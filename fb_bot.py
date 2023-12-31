"""Module that contains the main class for scrapping facebook."""

# TODO add the old programmer as an author too
__author__ = 'IllustriousJelly'

import os
import time
import json
import logging as log
from sys import stdout
from socket import gaierror
from datetime import datetime, date
from argparse import ArgumentParser

import pandas as pd
from halo import Halo
from selenium.common.exceptions import WebDriverException

from facebook import fb
from emailclient import email
from spreadsheet import Spread
from webapi import testApi, websiteApi

# NOTE should use __debug__ instead and freeze the bots into EXEs?
DEBUG = False


class Main:
    """Class that scraps through facebook, retrieves user data, and sends it
    to the database.
    """

    def __init__(self, options):
        log.info('FACEBOOK BOT')

        self.options = options

        self.loadData()

        self.setData()

    def loadData(self) -> None:
        """Load the settings from the JSON settings file, if the bot is in
        DEBUG mode, or the test_api argument is passed in the command-line,
        the bot will use a tests JSON settings file instead of the normal
        settings file.
        """
        if DEBUG or self.options.test_api:
            settings = 'FB_test_settings.json'
        else:
            settings = 'FB_settings.json'

        with open(settings, 'r', encoding='utf-8') as file:
            self.data = json.load(file)

    def setData(self) -> None:
        """Initialize all the objects for scrapping, database handling and API
        handling using the previously loaded configurations.
        """
        self.outlook = email(self.data)

        self.spreadSheet = Spread(self.data['spreadsheet']['sheet'])

        if self.options.use_chrome:
            browser = 'chrome'
        else:
            browser = 'brave'

        self.facebook = fb(
            self.data['facebook'], browser, self.options.visible,
            self.options.debug_selenium
        )

        if self.options.test_api or DEBUG:
            self.webApi = testApi(self.data, self.outlook, 'FB_BOT')
        else:
            self.webApi = websiteApi(self.data, self.outlook, 'FB_BOT')

    def fbAccounts(self) -> list[str]:
        """Get all the registered users from the database and load them into
        a list of tuples including their user link, the sheet of the database
        where they come from and the date of their last post.
        """
        log.info('Getting user accounts...')

        users = []

        for sheet in ('fb personal lists', 'fb page lists'):
            self.spreadSheet.setSheet(sheet)
            matrix = self.spreadSheet.get_all()

            for user in range(1, len(matrix)):
                userlink = matrix[user][0]
                postDate = matrix[user][2]
                if 'www.facebook.com' in userlink:
                    users.append((userlink, sheet, postDate))

        return users

    def usersDetails(self):
        users = self.fbAccounts()
        saveUsers = []
        login = self.facebook.login()

        if login[0]:
            network = self.facebook.netwrok()
            if network[0]:
                log.info('Scraping users data...')

                spinner = Halo(text='', spinner='dots')
                spinner.start()

                for idx, user in enumerate(users):
                    usr = self.facebook.getUser(user[0])
                    if usr[0]:
                        followers = self.facebook.followers()
                        stories =  self.facebook.stories()
                        posts = self.facebook.posts(user[2])

                        for _ in range(3):
                            if posts == 'reload':
                                posts = self.facebook.posts(user[2])

                        if posts == 'reload':
                            log.error('Error fecthing posts!')
                            log.info('skipping user..')

                            time.sleep(1800)

                            continue

                        if posts[1] == 'network':
                            spinner.stop()
                            log.error('Network Error!')

                            dataFrame = pd.DataFrame(
                                [posts[2]], columns=['Username', 'Password']
                            )
                            self.outlook.sendMail(
                                'FB_BOT (NETWORK ERROR!)',
                                'NETWORK ERROR!',
                                dataFrame.to_html()
                            )

                            time.sleep(self.data['networkDelay'] * 60)

                            return False
                        else:
                            posts = posts[0]
                        if len(posts) > 0:
                            posts = self.facebook.postTypes(posts)
                            posts = self.savePosts(user[0], posts)

                        users[idx] = (user[0], followers, posts, True, user[1])
                        saveUsers.append(
                            (user[0], followers, posts, True, stories)
                        )
                        log.debug((user[0], followers, posts, True, stories))
                    else:
                        if len(usr) > 1:
                            log.error('Network Error!')

                            dataFrame = pd.DataFrame(
                                [usr[1]], columns=['Username', 'Password']
                            )
                            self.outlook.sendMail(
                                'FB_BOT (NETWORK ERROR!)',
                                'NETWORK ERROR!',
                                dataFrame.to_html()
                            )

                            time.sleep(self.data['networkDelay'] * 60)

                            return False
                        else:
                            users[idx] = (user[0], None, None, False, user[1])
                            saveUsers.append(
                                (user[0], None, None, False, False)
                            )
                            log.debug((user[0], None, None, False, False))

                spinner.stop()
            else:
                log.error('Network Error!')

                dataFrame = pd.DataFrame(
                    [network[1]], columns=['Username', 'Password']
                )
                self.outlook.sendMail(
                    'FB_BOT (NETWORK ERROR!)',
                    'NETWORK ERROR!',
                    dataFrame.to_html()
                )

                time.sleep(self.data['networkDelay'] * 60)

                return False

            self.saveUsers(saveUsers)

            return users

        log.error('Error Login FB: %s', login[1][0])

        dataFrame = pd.DataFrame([login[1]], columns=['Username', 'Password'])
        self.outlook.sendMail(
            'FB_BOT (LOGIN ERROR!)',
            'LOGIN ERROR!',
            dataFrame.to_html()
        )

        return False

    def savePosts(
            self, userLink: str, posts: list[tuple[str]],
            path: str = '.') -> list[tuple[str]]:
        filePath = path + '/FB_posts.json'

        # TODO make a method to load/save data into a file?
        log.debug('Looking for file in: %s', filePath)
        if os.path.isfile(filePath):
            with open(filePath, 'r', encoding='utf-8') as openfile:
                data = json.load(openfile)
        else:
            with open(filePath, 'x', encoding='utf-8') as outfile:
                data = {}
                json.dump(data, outfile)

        log.debug('Loaded posts: %s', data)

        # NOTE this loop updates the post parameter instead of the old
        # data list because this way it can keep all posts objects as
        # lists of tuples. It is very likely that in the future the
        # posts objects will change to be lists of lists instead to
        # simplify this kind of checks
        if userLink in data:
            oldData = data[userLink]

            for post in oldData:
                postTuple = tuple(post)

                if postTuple not in posts:
                    posts.append(postTuple)

        data[userLink] = posts

        with open(filePath, 'w', encoding='utf-8') as outfile:
            json.dump(data, outfile)

        return data[userLink]

    def saveUsers(self, userdata: list[tuple[str]]) -> None:
        log.info('Saving Users...')

        cusers = []

        if os.path.isfile('FB_users.json'):
            with open('FB_users.json', 'r', encoding='utf-8') as openfile:
                data = json.load(openfile)
        else:
            with open('FB_users.json', 'w', encoding='utf-8') as outfile:
                json.dump([], outfile)
                data = []

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

            newStories = user[4]
            if newStories not in data:
                data.append(newStories)

            if newStories is False:
                newStories = ''

            cusers.append((user[0], newPosts, newPostLink, newStories))

        if len(cusers) > 0 :
            dataFrame = pd.DataFrame(
                cusers,
                columns=['User Link', 'New Posts', 'Post Link', 'Stories']
            )
            self.outlook.sendMail(
                'FB_BOT (New Posts!)',
                'New Posts!',
                dataFrame.to_html()
            )

        with open('FB_users.json', 'w', encoding='utf-8') as outfile:
            json.dump(data, outfile)

    def fbInfo(self):
        log.info('Getting FB Info...')
        infos = []
        self.spreadSheet.setSheet('fb info')
        columns = self.spreadSheet.get_prop()[1]
        for col in range(1, columns + 1):
            info = self.spreadSheet.get_col(col)
            followersRange = info[0].strip().split('-')
            followersRange[0] = int(
                ''.join(filter(str.isdigit, followersRange[0]))
            )
            followersRange[1] = int(
                ''.join(filter(str.isdigit, followersRange[1]))
            )
            picLikes = ''.join(filter(str.isdigit, info[1]))
            videoViews = ''.join(filter(str.isdigit, info[3]))
            videoLikes = ''.join(filter(str.isdigit, info[4]))
            followers = ''.join(filter(str.isdigit, info[2]))
            infos.append((
                followersRange, int(picLikes.strip()),
                int(videoViews.strip()), int(videoLikes.strip()),
                int(followers)
            ))
        return infos

    def fbOrders(self):
        log.info('Getting FB Orders...')
        data = {}
        rows = []
        self.spreadSheet.setSheet('order fb')
        rowsCols = self.spreadSheet.get_all()
        head = rowsCols[0]
        for row in rowsCols:
            if row[0] !='':
                rows.append(row)
        for col in range(1, len(head)):
            tmp = []
            for row in rows:
                if row[0].strip() != '' and row[col].strip() != '' \
                        and row[col].strip() != '-':
                    tmp.append((row[0], row[col]))
            if len(tmp) > 0:
                data[head[col]] = tmp
        return data

    def addDay(self) -> dict[str, int]:
        cols: dict[str, int] = {}
        today = date.today().strftime('%d/%m/%Y')

        sheets = ('fb personal lists', 'fb page lists')
        for sheet in sheets:
            self.spreadSheet.setSheet(sheet)
            row = self.spreadSheet.get_row(1)
            rowLength = len(row)

            if today not in row:
                cols[sheet] = rowLength+1
                result = self.spreadSheet.set_cell(1, rowLength+1, today)

                if result is None:
                    columns = self.spreadSheet.get_col(1)

                    self.spreadSheet.clear_grid('D1', f'Z{len(columns)}')

                    self.spreadSheet.set_cell(1, 4, today)
            else:
                cols[sheet] = rowLength

        return cols

    def removePost(self, userLink, post):
        fileExists = os.path.isfile('FB_posts.json')
        if fileExists:
            with open('FB_posts.json', 'r', encoding='utf-8') as openfile:
                data = json.load(openfile)
                if userLink in data:
                    data[userLink].remove(list(post))
                with open('FB_posts.json', 'w', encoding='utf-8') as outfile:
                    json.dump(data, outfile)
                    return True

    # NOTE the bot seems to be not updating the followers numbers
    # correctly, check that
    def updateFollower(self, newFollower, userLink, infos, type):
        self.spreadSheet.setSheet(type)
        userLinks = self.spreadSheet.get_col(1)

        today = date.today().strftime('%d/%m/%Y')

        if os.path.isfile('FB_followers.json'):
            with open('FB_followers.json', 'r', encoding='utf-8') as file:
                followersData = json.load(file)
        else:
            with open('FB_followers.json', 'x', encoding='utf-8') as file:
                followersData = {}
                json.dump(followersData, file)

        for idx, user in enumerate(userLinks):
            if user == userLink:
                for info in infos:
                    followerClose = int(info[0][1])

                    if int(newFollower) <= followerClose:
                        userFollowers = info[4]

                        newOrder = self.webApi.newOrder(
                            userLink, userFollowers, 'followers', today, type
                        )
                        if not newOrder:
                            log.warning(
                                'Could not order followers for user, ' \
                                'skipping...'
                            )

                        follower = self.spreadSheet.get_cell(idx + 1, 2)
                        ffollower = ''

                        try:
                            start = follower.index('(')
                            ffollower = ''

                            for num in range(0, start):
                                ffollower = ffollower + follower[num]
                        except:
                            ffollower = newFollower

                        updatedFollowers = f'{str(ffollower)}' \
                            f'({str(newFollower)})'
                        followersData[user] = str(newFollower)

                        with open('FB_followers.json', 'w', encoding='utf-8') \
                                as file:
                            json.dump(followersData, file)

                        self.spreadSheet.set_cell(idx + 1, 2, updatedFollowers)

                        return True

        return False

    # NOTE check if the post this method uses for updating the last
    # post date is actually the last post
    def updatePost(
            self, newPosts: list[tuple[str]], userLink: str,
            dateCol: dict[str, int], type: str) -> int:
        log.info('Updating user posts in googlesheets')

        self.spreadSheet.setSheet(type)

        dateCol = dateCol[type]
        userLinks = self.spreadSheet.search_cell(userLink)
        posts = self.spreadSheet.get_cell(userLinks[0], dateCol)

        if posts is None or posts.strip() == '':
            oldposts = 0

            self.spreadSheet.set_cell(userLinks[0], dateCol, len(newPosts))
        else:
            oldposts = int(posts)

            self.spreadSheet.set_cell(
                userLinks[0], dateCol, len(newPosts)+oldposts
            )

        if len(newPosts) > 0:
            self.spreadSheet.set_cell(userLinks[0], 3, newPosts[0][1])

        return oldposts

    # TODO add unit tests for this method
    # TODO improve annotations of infos parameter
    # NOTE it seems like the parameter oldPosts is not being used,
    # delete it?
    # NOTE should change parameter newPosts to a list of tuples, or
    # a tuple of tuples
    # NOTE should check if the type of newPosts parameter is
    # list[list[str]] or list[tuple[str]]
    def sendOrders(
            self, userLink: str, followers: int, oldPosts: int,
            newPosts: list[list[str]], infos: list[tuple[list[int] | int]],
            typeP: str) -> bool:
        log.debug('New posts: %s', newPosts)

        if len(newPosts) == 0:
            log.info('This user has no new posts, skipping orders...')

            return True

        for post in newPosts:
            isBalance = self.webApi.balance()

            if isBalance['enough']:
                for info in infos:
                    followerClose = int(info[0][1])

                    assert isinstance(followers, int)
                    if followers <= followerClose:
                        # NOTE it seems like followers_ variable is
                        # redundant with followers parameter, delete
                        # one of them?
                        userFollowers: int = info[4]
                        postLink: str = post[0]
                        postDate: str = post[1]
                        postType: str = post[2]

                        if postType == 'picture':
                            picLikes = (info[1] * followers) // 100

                            order = self.webApi.newOrder(
                                postLink, picLikes, 'picture', postDate, typeP
                            )

                            if order:
                                self.removePost(
                                    userLink, (postLink, postDate, postType)
                                )
                            else:
                                log.error('Order error')
                        elif postType == 'video_reel':
                            for metricType in ('videoViews', 'videoLikes'):
                                if metricType == 'videoViews':
                                    percentage = (info[2] * followers) // 100
                                elif metricType == 'videoLikes':
                                    percentage = (info[3] * followers) // 100

                                order = self.webApi.newOrder(
                                    postLink, percentage, metricType,
                                    postDate, typeP
                                )

                                if order and metricType == 'videoViews':
                                    self.removePost(
                                        userLink,
                                        (postLink, postDate, postType)
                                    )
                                elif order and metricType == 'videoLikes':
                                    break
                                else:
                                    log.error('Order error')

                        break
                    else:
                        continue
            else:
                return False

        return True

    def start(self):
        count = 1
        while True:
            try:
                now = datetime.now()
                log.info(
                    '[%s] %s %s Running script!', count, now.strftime("%A"),
                    now.strftime("%I:%M:%S")
                )
                isBalance = self.webApi.balance()
                if isBalance['enough']:
                    dateCol = self.addDay()
                    self.facebook.startBrowser()
                    usersData = self.usersDetails()
                    if not usersData:
                        self.facebook.closeBrowser()
                        count = count + 1
                        continue
                    self.webApi.setOrder(self.fbOrders())
                    self.facebook.closeBrowser()
                    infos = self.fbInfo()
                    for user in usersData:
                        userLink = user[0]
                        username = userLink.split('/')
                        username = username[3]
                        if 'profile.php?id=' in username:
                            username = username.replace('profile.php?id=', '')
                        postType = user[4]
                        cuserFollower = user[1]
                        cuserPosts = user[2]
                        isUser = user[3]
                        if isUser:
                            log.info('USER: %s', username)

                            if self.data['neworder']:
                                log.info('➥ Ordering Followers...')

                                result = self.updateFollower(
                                    cuserFollower, userLink, infos, postType
                                )
                                if result:
                                    posts = self.updatePost(
                                        cuserPosts, userLink, dateCol, postType
                                    )
                                    time.sleep(60)

                                    log.info('➥ Ordering Posts...')

                                    newOrder = self.sendOrders(
                                        userLink, cuserFollower, posts,
                                        cuserPosts, infos, postType
                                    )

                                    if not newOrder:
                                        break
                        else:
                            log.warning(
                                'USER: %s (Private/Not Found)', username
                            )
                else:
                    dataFrame = pd.DataFrame(
                        isBalance['data'],
                        columns=['API', 'Balance', 'Currency']
                    )

                    log.error('Insufficient balance!\n%s', dataFrame)

                    self.outlook.sendMail(
                        'FB_BOT (Insufficient balance!)',
                        'Insufficient balance!',
                        dataFrame.to_html()
                    )

                    # TODO make the bot wait for user input instead
                    log.info('Waiting 10 minutes...')
                    time.sleep(10*60)

                log.info(
                    'Restarting script in %s minutes!', self.data["delay"]
                )
                time.sleep(self.data['delay']*60)

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

        time.sleep(300)

    def handleCrash(self):
        log.exception('Program crashed because of unknown error:')
        log.info('Restarting in 5 minutes...')

        for _ in range(3):
            try:
                self.outlook.sendMail(
                    'FB_BOT (Program crashed!)',
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
    parser = ArgumentParser()
    parser.add_argument(
        '--use-chrome', action='store_true',
        help='Make the bot use Chrome as the Selenium browser instead of ' \
            'using Brave'
    )
    parser.add_argument(
        '--visible', action='store_true',
        help='Make the Selenium browser visible instead of headless'
    )
    parser.add_argument(
        '--show-debug', action='store_true',
        help='Show the debug logs during execution'
    )
    parser.add_argument(
        '--show-selenium-debug', action='store_true', dest='debug_selenium',
        help='Show selenium debug logs'
    )
    parser.add_argument(
        '-A', '--use-test-api', action='store_true', dest='test_api',
        help='Use a test API instead of the production API'
    )

    return parser.parse_args()

if __name__ == '__main__':
    args = parseArgs()

    if DEBUG or args.show_debug:
        level = log.DEBUG
    else:
        level = log.INFO

    # TODO add timestamps to logs?
    log.basicConfig(level=level, filename='FB_log.log', filemode='w')

    # Allows to log both into a file and into stdout
    log.getLogger().addHandler(log.StreamHandler(stdout))

    bot = Main(args)

    while True:
        bot.start()
