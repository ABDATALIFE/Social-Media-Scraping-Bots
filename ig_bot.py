"""Module that contains the main class for scrapping instagram."""

__author__ = 'IllustriousJelly'

import os
import time
import json
import math
# TODO see if redundant
import datetime
import logging as log
from sys import stdout
from datetime import date
from socket import gaierror
from argparse import ArgumentParser

import pandas as pd
from halo import Halo
from selenium.common.exceptions import WebDriverException

from insta import insta
from emailclient import email
from spreadsheet import Spread
from webapi import testApi, websiteApi

# NOTE should use __debug__ instead and freeze the bots into EXEs?
DEBUG = False


class Main:
    """Class that performs a scrapping process on instagram users, retrieving
    data about their lastest posts, stories and number of followers and storing
    this data on a database, then it promotes these users by a proportional
    amount based on their metrics using SMM APIs.
    """

    def __init__(self, options):
        log.info('INSTAGRAM BOT')

        self.options = options

        self.loadData()

        self.setData()

    def loadData(self) -> None:
        """Load the settings from a JSON settings file, if the bot is in
        DEBUG mode, or the test_api argument is passed through the
        command-line, the bot will use a tests JSON settings file instead of
        the normal settings file.
        """
        if DEBUG or self.options.test_api:
            settings = 'IG_test_settings.json'
        else:
            settings = 'IG_settings.json'

        with open(settings) as f:
            self.data = json.load(f)

    def setData(self) -> None:
        """Initialize all the objects for scrapping, database handling and API
        handling using the previously loaded configurations.
        """
        self.outlook = email(self.data)

        self.ss = Spread(self.data['spreadsheet']['sheet'])

        if self.options.use_brave:
            browser = 'brave'
        else:
            browser = 'chrome'

        self.instagram = insta(
            self.data['instagram'], browser,
            self.options.visible, self.options.debug_selenium
        )

        if self.options.test_api or DEBUG:
            self.webApi = testApi(self.data, self.outlook, 'IG_BOT')
        else:
            self.webApi = websiteApi(self.data, self.outlook, 'IG_BOT')

    def instaAccounts(self):
        """Retrieve all the user links and their last post date from the
        database and return a list of tuples containing this data.
        """
        log.info('Getting user accounts...')
        self.ss.setSheet('Sheet11')
        matrix = self.ss.get_all()
        users = []
        for user in range(1, len(matrix)):
            userlink = matrix[user][0]
            postDate = matrix[user][2]
            if 'www.instagram.com' in userlink:
                users.append((userlink, postDate))
        return users

    def usersDetails(self):
        """Check if the configured instagram scrapping account is logged, in
        case it is logged in, start scrapping the list of user links from the
        database and retrieve their followers and lastest posts and stories
        (if any), then return a list with the scrapped data from the users.

        If any error occurs during the scrapping process, return False,

        If the scrapping user is not logged in, login and then begin the
        scrapping process.
        """
        today = date.today()
        d1 = today.strftime('%d/%m/%Y')
        users = self.instaAccounts()
        saveUsers = []
        login = self.instagram.login()
        if login[0]:
            network = self.instagram.netwrok()
            if network[0]:
                log.info('Scraping users data...')
                spinner = Halo(text='', spinner='dots')
                spinner.start()
                for idx, user in enumerate(users):
                    if self.instagram.getUser(user[0]):
                        followers = self.instagram.followers()
                        stories = self.instagram.stories()
                        # TODO make the bot to scrap the posts without
                        # having to get the user page again
                        self.instagram.driver.get(user[0])
                        posts = self.instagram.posts(user[1])
                        if posts[1] == 'network':
                            spinner.stop()
                            log.error('Network Error!')
                            df = pd.DataFrame([posts[2]], columns=['Username', 'Password'])
                            self.outlook.sendMail(
                                'IG_BOT (NETWORK ERROR!)',
                                'NETWORK ERROR!',
                                df.to_html()
                            )
                            time.sleep(self.data['networkDelay'] * 60)
                            return False
                        else:
                            posts = posts[0]
                            posts = self.savePosts(user[0], posts)

                        users[idx] = (user[0], followers, posts, True, 'instagram user')
                        saveUsers.append((user[0], followers, posts, True, stories))

                    else:
                        users[idx] = (user[0], None, None, False, 'instagram user')
                        saveUsers.append((user[0], None, None, False, []))
                spinner.stop()
            else:

                log.error('Network Error!')
                df = pd.DataFrame([network[1]], columns=['Username', 'Password'])
                self.outlook.sendMail(
                    'IG_BOT (NETWORK ERROR!)',
                    'NETWORK ERROR!',
                    df.to_html()
                )
                time.sleep(self.data['networkDelay'] * 60)
                return False

            self.saveUsers(saveUsers)
            return users

        else:
            log.error(f'Error Login IG: {login[1][0]}')
            df = pd.DataFrame([login[1]], columns=['Username', 'Password'])
            self.outlook.sendMail(
                'IG_BOT (LOGIN ERROR!)',
                'LOGIN ERROR!',
                df.to_html()
            )
            return False

    def savePosts(self, user, posts):
        """Save all the new retrieved user posts into a JSON file and return
        the updated list of user posts.
        """
        file_exists = os.path.isfile('IG_posts.json')
        if not file_exists:
            with open('IG_posts.json', 'w') as outfile:
                json.dump([], outfile)
                data = {}
        else:
            with open('IG_posts.json', 'r') as openfile:
                data = json.load(openfile)

        userLink = user
        if userLink in data:
            oldData = data[userLink]
            for post in oldData:
                if tuple(post) not in posts:
                    posts.append(tuple(post))
            data[userLink] = posts
        else:
            data[userLink] = posts

        with open('IG_posts.json', 'w') as outfile:
            json.dump(data, outfile)
            return data[userLink]

    # NOTE this method might have the same issues that the same method
    # in the Fb bot, check that
    def saveUsers(self, userdata):
        """Save the currently retrieved user data into a JSON file. If the user
        has uploaded new posts, send a email notification to the configured
        notification email address.
        """
        log.info('Saving Users...')
        cusers = []
        file_exists = os.path.isfile('IG_users.json')
        if not file_exists:
            with open('IG_users.json', 'w') as outfile:
                json.dump([], outfile)
                data = []
        else:
            with open('IG_users.json', 'r') as openfile:
                data = json.load(openfile)

        for user in userdata:
            newPosts = 0
            newPostLink = []

            if user[2]:
                posts = user[2]

                for post in posts:
                    link = post[0]

                    if link not in data:
                        newPosts = newPosts + 1
                        newPostLink.append(link)
                        data.append(link)
            else:
                continue

            newStories = []

            if user[4]:
                story = user[4]

                for stry in story:
                    link = stry

                    if link not in data:
                        newStories.append(link)
                        data.append(link)
            else:
                pass

            cusers.append((user[0], newPosts, newPostLink, newStories))

        if len(cusers) > 0:
            df = pd.DataFrame(cusers, columns=['User Link', 'New Posts', 'Post Link', 'Stories'])
            self.outlook.sendMail(
                'IG_BOT (New Posts!)',
                'New Posts!',
                df.to_html()
            )

        with open('IG_users.json', 'w') as outfile:
            json.dump(data, outfile)

    def igInfo(self):
        """Retrieve the data necessary to perform the calculations on how
        much resources will have to be spent on an user based on their metrics
        and then return the retrieved data as a list of tuples.
        """
        log.info('Getting IG Info...')
        infos = []
        self.ss.setSheet('ig info')
        columns = self.ss.get_prop()[1]
        for col in range(1, columns + 1):
            info = self.ss.get_col(col)
            followersRange = info[0].strip().split('-')
            followersRange[0] = int(''.join(filter(str.isdigit, followersRange[0])))
            followersRange[1] = int(''.join(filter(str.isdigit, followersRange[1])))
            picLikes = ''.join(filter(str.isdigit, info[1]))
            videoViews = ''.join(filter(str.isdigit, info[2]))
            videoLikes = ''.join(filter(str.isdigit, info[3]))
            igSavePosts = info[4].strip().split('-')
            igSavePosts[0] = int(''.join(filter(str.isdigit, igSavePosts[0])))
            igSavePosts[1] = int(''.join(filter(str.isdigit, igSavePosts[1])))
            impressionAndReache = ''.join(filter(str.isdigit, info[5]))
            reelViwes = ''.join(filter(str.isdigit, info[6]))
            reelLikes = ''.join(filter(str.isdigit, info[7]))
            followers = ''.join(filter(str.isdigit, info[9]))
            infos.append((followersRange, int(picLikes.strip()), int(videoViews.strip()), int(videoLikes.strip()),
                          igSavePosts, int(impressionAndReache.strip()), int(reelViwes.strip()), int(reelLikes.strip()),
                          followers))
        return infos

    def igOrders(self):
        """Retrieve the data necessary to perform a new order request to the
        configured SMM APIs and return the retrieved data in a dictionary.
        """
        log.info('Getting IG Orders...')
        data = {}
        rows = []
        self.ss.setSheet('order ig')
        rows_cols = self.ss.get_all()
        head = rows_cols[0]
        for row in rows_cols:
            if row[0] != '':
                rows.append(row)
        for col in range(1, len(head)):
            tmp = []
            for row in rows:
                if row[0].strip() != '' and row[col].strip() != '' and row[col].strip() != '-':
                    tmp.append((row[0], row[col]))
            if len(tmp) > 0:
                data[head[col]] = tmp
        return data

    def addDay(self):
        """Check if there is a date column with the current date and if there
        is no such column, create one and then return the new length of the
        date columns row. If there is already a current date column, return
        the current length of the date columns row.
        """
        addDate = True
        today = date.today().strftime('%d/%m/%Y')
        self.ss.setSheet('Sheet11')
        row = self.ss.get_row(1)

        for col in row:
            if col == today:
                addDate = False

        if addDate:
            result = self.ss.set_cell(1, len(row) + 1, str(today))

            if result:
                return len(row)+1
            else:
                columns = self.ss.get_col(1)

                self.ss.clear_grid('D1', f'Z{len(columns)}')

                return self.addDay()
        else:
            return len(row)

    def removePost(self, userLink, post):
        """Remove a post object from a user object inside a post JSON file."""
        file_exists = os.path.isfile('IG_posts.json')
        if file_exists:
            with open('IG_posts.json', 'r') as openfile:
                data = json.load(openfile)
                if userLink in data:
                    data[userLink].remove(list(post))
                with open('IG_posts.json', 'w') as outfile:
                    json.dump(data, outfile)
                    return True

    def updateFollower(self, newFollower, userLink, infos, type_):
        """Order new followers for the given user and then update the amount
        of instagram followers this user currently has. If the order is made
        successfully return True, return False otherwise.
        """
        self.ss.setSheet('Sheet11')
        userLinks = self.ss.get_col(1)

        today = date.today().strftime('%d/%m/%Y')

        # TODO add fix for crash when file is empty
        if os.path.isfile('IG_followers.json'):
            with open('IG_followers.json', 'r') as file:
                followersData = json.load(file)
        else:
            with open('IG_followers.json', 'x') as file:
                followersData = {}
                json.dump(followersData, file)

        for idx, user in enumerate(userLinks):
            if user == userLink:
                for info in infos:
                    followerClose = int(info[0][1])

                    if int(newFollower) <= followerClose:
                        followers_ = info[8]

                        newOrder = self.webApi.newOrder(
                            userLink, followers_, 'followers', today, type_
                        )
                        if not newOrder:
                            log.warning(
                                'Could not order followers for user, ' \
                                'skipping...'
                            )

                        follower = self.ss.get_cell(idx + 1, 2)
                        ffollower = ''

                        try:
                            start = follower.index('(')
                            ffollower = ''

                            for x in range(0, start):
                                ffollower = ffollower + follower[x]
                        except:
                            ffollower = newFollower

                        updatedFollowers = f'{str(ffollower)}({str(newFollower)})'
                        followersData[user] = str(newFollower)

                        with open('IG_followers.json', 'w') as file:
                            json.dump(followersData, file)

                        self.ss.set_cell(idx + 1, 2, updatedFollowers)

                        return True
        return False

    def updatePost(self, newPosts, userLink, dateCol):
        """Update the number of a user new posts for today's date column inside
        the database.
        """
        log.info('Updating user posts in googlesheets')

        log.debug(f'New posts from {userLink}: {newPosts}')

        self.ss.setSheet('Sheet11')

        userLinks = self.ss.search_cell(userLink)
        posts = self.ss.get_cell(userLinks[0], dateCol)

        if posts == None or posts.strip() == '':
            oldposts = 0

            self.ss.set_cell(userLinks[0], dateCol, len(newPosts))
        else:
            oldposts = int(posts)

            self.ss.set_cell(userLinks[0], dateCol, len(newPosts)+oldposts)

        if len(newPosts) > 0:
            self.ss.set_cell(userLinks[0], 3, newPosts[0][1])

        return oldposts

    def sendOrders(self, userLink, followers, oldPosts, newPosts, infos, type_):
        """Make orders for getting instagram post likes, saves and
        impressions for video and picture posts to the configured SMM APIs and
        return True if the orders are made successfully. If there is not enough
        balance for performing the orders, return False.
        """
        log.debug(f'New posts: {newPosts}')

        if len(newPosts) == 0:
            log.info('This user has no new posts, skipping orders...')

            return True

        for post in newPosts:
            isBalance = self.webApi.balance()
            if isBalance['enough']:
                for info in infos:
                    followerClose = int(info[0][1])
                    if int(followers) <= followerClose:
                        picLikes = math.floor((info[1] * followers) / 100)
                        videoViews = math.floor((info[2] * followers) / 100)
                        videoLikes = math.floor((info[3] * followers) / 100)
                        igSavePosts = info[4]
                        impressionAndReache = math.floor((info[5] * followers) / 100)
                        reelViwws = math.floor((info[6] * followers) / 100)
                        reelLikes = math.floor((info[7] * followers) / 100)
                        followers_ = info[8]
                        postLink = post[0]
                        postDate = post[1]
                        postType = post[2]
                        if postType == 'picture':
                            order = self.webApi.newOrder(postLink, picLikes, 'picture', postDate, type_)
                            if not order:
                                log.error('Order error')
                            elif order:
                                self.removePost(userLink, (postLink, postDate, postType))
                            if not self.webApi.newOrder(postLink, igSavePosts, 'igSavePosts', postDate, type_):
                                log.error('Order error')
                            if not self.webApi.newOrder(postLink, impressionAndReache, 'impressionAndReache', postDate, type_):
                                log.error('Order error')
                        elif postType == 'video_reel':
                            order = self.webApi.newOrder(postLink, videoViews, 'videoViews', postDate, type_)
                            if not order:
                                log.error('Order error')
                            elif order:
                                self.removePost(userLink, (postLink, postDate, postType))
                            if not self.webApi.newOrder(postLink, videoLikes, 'videoLikes', postDate, type_):
                                log.error('Order error')
                            if not self.webApi.newOrder(postLink, igSavePosts, 'igSavePosts', postDate, type_):
                                log.error('Order error')
                            if not self.webApi.newOrder(postLink, impressionAndReache, 'impressionAndReache', postDate, type_):
                                log.error('Order error')

                        break
                # return True

            else:
                return False

        return True

    def start(self):
        """Run the scrapping process of the bot.

        This process includes logging the status of the bot into a file,
        sending notification mails in case of crash, retrieving data from
        the users inside the database, updating the database and making
        followers and engage orders to the given SMM APIs.
        """
        count = 1

        while True:
            try:
                x = datetime.datetime.now()
                log.info(f'[{count}] {x.strftime("%A")} {x.strftime("%I:%M:%S")}, Running script!')

                isBalance = self.webApi.balance()
                if isBalance['enough']:
                    dateCol = self.addDay()
                    self.instagram.startBrowser()
                    usersData = self.usersDetails()

                    if not usersData:
                        self.instagram.closeBrowser()
                        count = count + 1

                        continue

                    self.webApi.setOrder(self.igOrders())
                    self.instagram.closeBrowser()
                    infos = self.igInfo()

                    for user in usersData:
                        log.debug(f'Selected user data: {user}')

                        userLink = user[0]
                        username = userLink.split('/')
                        username = username[len(username) - 2]
                        cuserFollower = user[1]
                        cuserPosts = user[2]
                        isUser = user[3]
                        type_ = user[4]

                        if isUser:
                            log.info(f'USER: {username}')

                            if int(cuserFollower) > 15000:
                                log.info(f'{userLink} {cuserFollower} Followers Exceed!')

                                df = pd.DataFrame([(userLink, cuserFollower)], columns=['User', 'Followers'])
                                self.outlook.sendMail(
                                    'IG_BOT (Follower Range Exceed!)',
                                    'Follower Range Exceed!',
                                    df.to_html()
                                )

                                continue

                            if self.data['neworder']:
                                log.info('➥ Ordering Followers...')

                                if self.updateFollower(cuserFollower, userLink, infos, type_):
                                    posts = self.updatePost(cuserPosts, userLink, dateCol)
                                    time.sleep(60)

                                    log.info('➥ Ordering Posts...')
                                    newOrder = self.sendOrders(userLink, cuserFollower, posts, cuserPosts, infos, type_)

                                    if not newOrder:
                                        break
                        else:
                            log.warning(f'USER: {username} (Private/Not Found)')
                else:
                    df = pd.DataFrame(
                        isBalance['data'],
                        columns=['API', 'Balance', 'Currency']
                    )

                    log.error(f'Insufficient balance!\n{df}')

                    self.outlook.sendMail(
                        'IG_BOT (Insufficient balance!)',
                        'Insufficient balance!',
                        df.to_html()
                    )

                    log.info('Waiting 10 minutes...')
                    time.sleep(10*60)

                log.info(f'Restarting script in {self.data["delay"]} minute!')
                time.sleep(self.data['delay'] * 60)

                count = count + 1
            except WebDriverException as err:
                errString = str(err)
                if 'ERR_CONNECTION_CLOSED' in errString:
                    log.error('Browser closed due to a connection error')
                    log.info('Restarting browser in 20 minutes')

                    time.sleep(1200)
                else:
                    self.handleCrash()
            except Exception:
                self.handleCrash()

        time.sleep(300)

    def handleCrash(self):
        """Log any unexpected exception that occurs during the execution of
        the scrapping process and send a notification mail to the email
        address specified in the configuration.
        """
        log.exception('Program crashed because of unknown error:')
        log.info('Restarting in 5 minutes...')

        for _ in range(3):
            try:
                self.outlook.sendMail(
                    'IG_BOT (Program crashed!)',
                    'Program crashed, an unknown error occurred!',
                    'Restarting in 5 minutes!'
                )
                break
            # TODO implement on emailclient.py
            except gaierror:
                log.warning(
                    'Couldn\' send mail, retrying in 5 minutes...'
                )

                time.sleep(300)
            except:
                log.exception(
                    'Unable to send crash report because of error:'
                )

                break


def parseArgs():
    """Parse the argument passed to the script through the command line."""
    parser = ArgumentParser()
    parser.add_argument(
        '--use-brave', action='store_true',
        help='Use the Brave browser as the Selenium browser instead of Chrome'
    )
    parser.add_argument(
        '--visible', action='store_true', help='Make the Selenium browser visible'
    )
    parser.add_argument(
        '--show-debug', action='store_true',
        help='Show debug messages of the ig bot'
    )
    parser.add_argument(
        '--show-selenium-debug', action='store_true', dest='debug_selenium',
        help='Show debug messages of the selenium package'
    )
    parser.add_argument(
        '-A', '--use-test-api', action='store_true', dest='test_api',
        help='Make the bot use the test API instead of the production API'
    )

    return parser.parse_args()


if __name__ == '__main__':
    args = parseArgs()

    if DEBUG or args.show_debug:
        level = log.DEBUG
    else:
        level = log.INFO

    # TODO add timestamps to logs?
    log.basicConfig(level=level, filename='IG_log.log', filemode='w')

    # Allows to log both into a file and into stdout
    log.getLogger().addHandler(log.StreamHandler(stdout))

    bot = Main(args)

    while True:
        bot.start()
