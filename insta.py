"""Module that includes a class used for traversing through instagram and
retrieving user data.
"""

import os
import time
import datetime
import warnings
import logging as log
from sys import exit as sys_exit

from urllib3.exceptions import MaxRetryError
from selenium import webdriver
from selenium.webdriver.remote.remote_connection import LOGGER
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    NoSuchElementException,
)

warnings.filterwarnings('ignore')


class insta:
    """Class that serves as a browser for the instagram scrapper, it loads
    instagram user pages on a automated browser and retrieves all the
    necessary user data such as followers, posts and stories.
    """

    def __init__(
            self, users: list[dict[str, str]], browser: str,
            visible: bool = False, debug_selenium: bool = False):
        self.btn = {
            'log_usrnm': '//*[@id="loginForm"]/div/div[1]/div/label/input',
            'log_userps': '//*[@id="loginForm"]/div/div[2]/div/label/input',
            'log_btn': '//*[@id="loginForm"]/div/div[3]',
            'save_info': '//*[@id="react-root"]/section/main/div/div/div/section/div/button',
            'is_private': '//article//h2',
            'not_found': '//h2[contains(., "Sorry, this page isn\'t available")] | //h2[contains(., "很抱歉，无法访问此页面")]',
            'followers': '//span/span',
            'profileIcon': '//img[@crossorigin="anonymous"]',
            'postList': '//div[@style="position: relative; display: flex; flex-direction: column; padding-bottom: 0px; padding-top: 0px;"]',
            'reelIndicator': '//span[contains(.,"reel")]',
            'postMenu': '//*[local-name() = "svg"][@aria-label="More options"] | //*[local-name() = "svg"][@aria-label="More Options"] | //*[local-name() = "svg"][@aria-label="更多选项"]',
            'postLink': '//button[contains(.,"Copy link")] | //button[contains(.,"复制链接")]',
            'nextPost': '//*[local-name() = "svg"][@aria-label="Next"] | //*[local-name() = "svg"][@aria-label="下一步"]',
            'stories': '//header/div/div',
            'next_story': 'button[aria-label="Next"]',
            'view_story': '/html/body/div[1]/div/div/div/div[1]/div/div/div/div[1]/div[1]/section/div[1]/div/section/div/div[1]/div/div/div/div[3]/button',
            'loadingUser': '/html/body/div[1]/div/div/div/div[1]/div/div/div/div[1]/div[1]/section/main/div[1]/section/div[3]/div[1]/div/div/div[2]/div/div/div/a',
            'heartBtn': '/html/body/div[1]/div/div/div/div[1]/div/div/div/div[1]/section/nav/div[2]/div/div/div[3]/div/div[5]',
            'likeFollows': '/html/body/div[1]/div/div/div/div[1]/div/div/div/div[1]/section/nav/div[2]/div/div/div[3]/div/div[5]/div[2]/div/div[2]/div',
            'allowCookies': '/html/body/div[4]/div/div/button[2]',
            'userMenu': '//a[@href="#"]',
            'logout': '//div[contains(., "Log out")][@role="button"] | //div[contains(., "退出")][@role="button"]',
            # TODO make a chinese version of this xpath
            'notNow2': '//button[contains(., "Not Now")]',
            # TODO make an english version of this xpath
            'notNow': '//button[contains(., "打开")]',
        }

        if debug_selenium:
            LOGGER.setLevel(log.DEBUG)
        else:
            LOGGER.setLevel(log.WARNING)

        self.users = users
        self.cuser = 1
        self.options = webdriver.ChromeOptions()
        self.options.add_argument('--no-sandbox')
        if visible:
            self.options.add_argument('--start-maximized')
        else:
            self.options.add_argument('--headless')
        self.options.add_argument('--disable-extensions')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_experimental_option('excludeSwitches', ['enable-logging'])
        try:
            if browser == 'brave':
                self.options.binary_location = r'C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe'
                self.options.add_argument(
                    f'--user-data-dir={os.environ["LOCALAPPDATA"]}\\BraveSoftware\\Brave-Browser\\User Data'
                )
            else:
                self.options.binary_location = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
                self.options.add_argument(
                    f'--user-data-dir={os.environ["LOCALAPPDATA"]}\\Google\\Chrome\\User Data'
                )
        except:
            print('Data Directory in use!')

    def get(self, link: str, retries: int = 3) -> None:
        """Go to the given link using the Selenium browser, if the connection
        to the link page fails, retry the connection, if the max amount of
        retries is reached, close the program.
        """
        attempts = 0

        while attempts < retries:
            try:
                self.driver.get(link)

                break
            except (WebDriverException, MaxRetryError) as err:
                log.warning(
                    f'Error while connecting to {link}, retrying in 15 minutes'
                )
                log.debug(f'Connection error details: {err}')

                # NOTE put in a finally statement if more exceptions
                # get added
                attempts += 1

                time.sleep(900)
        else:
            # TODO send email on error
            log.error(
                'Connection attempts exceeded, maybe the website is down?'
            )

            raise MaxRetryError('Manual call', link, 'Posible website down')

    def startBrowser(self):
        """Select the username credentials from the configurations and specify
        the profile directory for such user, then start the Selenium browser
        and go instagram's main page.
        """
        log.info('Opening browser...')

        self.userIdx = self.cuser%len(self.users)
        self.email = self.users[self.userIdx]['username']
        self.password = self.users[self.userIdx]['password']
        self.cuser = self.cuser+1

        if self.userIdx == 0:
            self.userIdx = len(self.users)

        self.options.add_argument('--profile-directory=Profile '+str(self.userIdx))

        for _ in range(3):
            try:
                self.driver = webdriver.Chrome('driver//chromedriver', options=self.options)
                break
            except WebDriverException as error:
                log.warning(
                    'Could not open the Browser, retrying in 10 minutes'
                )
                log.debug('Error details: %s', str(error))
                time.sleep(600)

        self.elmwait = WebDriverWait(self.driver, 5)

        log.info('Going to instagram main page...')

        self.get('https://www.instagram.com/')

    def login(self):
        """Check if the user is logged in by looking for a user icon, if no
        user icon is found assume that the user is not logged and start the
        login process using the selected user credentials from the
        configuration. If the user is correctly logged in, return a tuple with
        True and the used login credentials.

        If a "remember login", "not now" or "allow cookies" popup is detected,
        close it.
        """
        print('Login Instagram: ', self.email)
        elmwait = WebDriverWait(self.driver, 25)
        try:
            remember = elmwait.until(EC.element_to_be_clickable((By.XPATH, self.btn['save_info'])))
            remember.click()
        except:
            _f = None
        try:
            notNow = elmwait.until(EC.element_to_be_clickable((By.XPATH, self.btn['notNow2'])))
            notNow.click()
        except:
            _f = None
        try:
            profile = self.elmwait.until(EC.visibility_of_element_located((By.XPATH, self.btn['profileIcon'])))
            return True, (self.email, self.password)
        except:
            try:
                allowCookies = self.elmwait.until(EC.visibility_of_element_located((By.XPATH, self.btn['allowCookies'])))
                allowCookies.click()
                time.sleep(3)
            except:
                _f = None
            username = self.elmwait.until(EC.visibility_of_element_located((By.XPATH, self.btn['log_usrnm'])))
            password = self.elmwait.until(EC.visibility_of_element_located((By.XPATH, self.btn['log_userps'])))
            login = self.elmwait.until(EC.element_to_be_clickable((By.XPATH, self.btn['log_btn'])))

            username.send_keys(self.email)
            password.send_keys(self.password)
            login.click()

            try:
                remember = elmwait.until(EC.element_to_be_clickable((By.XPATH, self.btn['save_info'])))
                remember.click()
                notNow = elmwait.until(EC.element_to_be_clickable((By.XPATH, self.btn['notNow2'])))
                notNow.click()
            except:
                pass

            return True, (self.email, self.password)

    def netwrok(self):
        """Go to the instagram main page and check if the scrapping user is
        logged in, if the user is correctly logged in return a tuple containing
        True and the used login credentials, otherwise return a tuple
        containing False and the used login credentials.

        If a "Not now" popup is detected, close it.
        """
        self.get('https://www.instagram.com/')

        elmwait = WebDriverWait(self.driver, 10)

        try:
            notNow = elmwait.until(EC.element_to_be_clickable((By.XPATH, self.btn['notNow'])))
            notNow.click()
        except TimeoutException:
            log.debug('Not now window not found')
        except Exception as err:
            log.debug(f'An unknown exception ocurred: {err}')

        try:
            profile = self.elmwait.until(EC.visibility_of_element_located((By.XPATH, self.btn['profileIcon'])))
            result = True
        except TimeoutException:
            log.debug('Profile icon not found')
            result = False
        except Exception as err:
            log.error(f'An unexpected exception ocurred: {err}')
            result = False

        return result, (self.email, self.password)

    def getUser(self, link: str, *, retry: bool = True) -> bool:
        """Go to the given instagram user page link and if the account is
        either banned or public, return False, return True otherwise.

        If the retry parameter is True, if the visited user page link is
        detected as not found, logout and then login again using different
        instagram credentials, then check again for the user availability.
        """
        log.info(f'Going to user page: {link}')

        self.get(link)
        time.sleep(5)

        try:
            self.elmwait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, self.btn['not_found'])
                )
            )

            if retry:
                log.warning('This account seems to be banned, changing...')

                self.logout()

                userIdx = self.cuser%len(self.users)
                self.email = self.users[userIdx]['username']
                self.password = self.users[userIdx]['password']
                self.cuser += 1

                self.login()

                return self.getUser(link, retry=False)
            else:
                log.warning('User not found or banned, skipping...')

                return False
        except TimeoutException:
            log.debug(f'Access to {link} is normal')
        except Exception:
            log.exception(f'An unexpected exception ocurred:')

        html = self.driver.page_source

        try:
            private = self.elmwait.until(EC.visibility_of_element_located((By.XPATH, self.btn['is_private'])))

            log.warning('This user has a private account, skipping...')

            return False
        except:
            return True

    def followers(self):
        """Retrieve the followers amount from the currently visited instagram
        user page and return the obtained amount. If no user followers are
        found, retry up to three times, if the max amount of retries is
        reached and no followers amount is found, raise a ValueError.
        """
        log.info('Getting user followers...')

        followers = None

        time.sleep(5)
        html = self.driver.page_source

        for _ in range(3):
            try:
                followers = self.driver.find_elements(By.XPATH, self.btn['followers'])

                if len(followers) > 1:
                    followers = followers[1]
                elif len(followers) == 1:
                    followers = followers[0]
                else:
                    followers = None
                    raise IndexError

                followers = followers.get_attribute('innerText').replace(',', '')

                break
            except IndexError:
                log.info('Couldn\'t find user followers, retrying in 5 minutes')

                self.driver.refresh()

                time.sleep(300)

                continue

        if followers is None:
            raise ValueError('Could not find followers')
        elif 'K' in followers:
            followers = float(followers.replace('K', '').strip()) * 1000
        elif 'M' in followers:
            # NOTE this seems like a possible bug, fix?
            followers = float(followers.replace('K', '').strip()) * 1000000

        # TODO make an info log?
        log.debug(f'Found followers: {followers}')

        return int(followers)

    def stories(self):
        """Retrieve any stories from the currently visited instagram user page
        and return a list with the links of the found stories. If no stories
        are found return an empty list.
        """
        log.info('Searching for user Stories')
        stories_ = []

        try:
            story = self.elmwait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, self.btn['stories'])
                )
            )
            story.click()

            time.sleep(5)

            self.driver.refresh()

            time.sleep(10)

            storyLink = self.driver.current_url
            if 'stories' in storyLink:
                log.info('Found stories, collecting')
                if storyLink not in stories_:
                    stories_.append(storyLink)
            else:
                log.info('Not stories found')
                log.debug(f'Not valid link: {storyLink}')
                pass
        except NoSuchElementException:
            log.info('Not stories found')
            log.debug('Element not found')
            stories_ = []

        return stories_

    # NOTE this method has some of the same issues that the Fb bot
    # has with post dates, and it also doesn't seems to have a limit
    # of post to search, fix that
    def posts(self, date):
        """Retrieve all those posts from the currently visited instagram user
        page where the post date time is greater than the given date time, then
        return a tuple containing the list of the retrieved posts, a string
        specifying any errors encountered during the post scrapping process,
        and a tuple with the currectly logged in instagram credentials.
        """
        log.info('Getting user posts')

        posts_ = []
        currentPost = 0
        error = 'unknown'
        date_time = date.strip()

        try:
            for _ in range(3):
                try:
                    article = self.driver.find_element(By.TAG_NAME, 'article')

                    firstPost = article.find_elements(By.TAG_NAME, 'a')[0]
                    firstPost.click()

                    break
                except NoSuchElementException:
                    time.sleep(5)

            while currentPost < 6:
                self.driver.refresh()

                time.sleep(10)

                postUrl = self.driver.current_url

                try:
                    reel = self.elmwait.until(
                        EC.presence_of_element_located(
                            (By.XPATH, self.btn['reelIndicator'])
                        )
                    )

                    postType = 'video_reel'
                except TimeoutException:
                    postType = 'picture'

                for _ in range(3):
                    try:
                        postDate = self.elmwait.until(
                            EC.presence_of_element_located(
                                (By.TAG_NAME, 'time')
                            )
                        )

                        break
                    except TimeoutException:
                        log.warning(
                            'Couldn\'t find current post date, retrying ' \
                                'in 5 minutes'
                        )

                        self.driver.refresh()

                        time.sleep(300)

                        continue
                else:
                    log.error(
                        'Couldn\'t get current post date, skipping ' \
                            'to next user...'
                    )

                    break

                postDateTime = postDate.get_attribute('datetime')
                postDateTime = postDateTime.split('.')[0]
                postDateTime = (
                    datetime.datetime
                    .strptime(postDateTime, '%Y-%m-%dT%H:%M:%S')
                    .strftime('%d/%m/%Y at %I:%M %p'))

                log.debug(f'Post date: {postDateTime}, Date time: {date_time}')

                postDateTimeD = (
                    datetime.datetime
                    .strptime(postDateTime, '%d/%m/%Y at %I:%M %p'))

                if date_time == '':
                    log.debug('Last post date was empty')

                    today = datetime.datetime.today()
                    yesterday = today - datetime.timedelta(days=1)

                    if postDateTimeD > today or postDateTimeD > yesterday:
                        log.info(
                            'Found new post, adding to list...'
                        )

                        posts_.append((postUrl, postDateTime, postType))
                    else:
                        log.info(
                            'Found old post, changing to next user...'
                        )

                        break
                else:
                    date_timeD = (
                        datetime.datetime
                        .strptime(date_time, '%d/%m/%Y at %I:%M %p'))

                    if postDateTimeD > date_timeD:
                        log.info('Found new post, adding to list...')
                        posts_.append((postUrl, postDateTime, postType))
                    else:
                        log.info('Found old post, changing to next user...')
                        break

                try:
                    postList = self.driver.find_element(By.XPATH, self.btn['postList'])

                    lastPosts = postList.find_elements(By.TAG_NAME, 'a')

                    # TODO test if this sleep is necessary
                    time.sleep(10)

                    lastPosts[currentPost].click()

                    currentPost += 1
                except TimeoutException:
                    log.warning('Could not find next post button')

                    break
        except Exception:
            log.exception('Exception while getting posts')

            posts_ = []

        log.debug(f'Found posts {posts_} with error: {error}')

        return posts_, error, (self.email, self.password)

    def logout(self) -> None:
        """Logout from the currently logged in scrapping user account."""
        time.sleep(5)
        userMenu = self.driver.find_elements(By.XPATH, self.btn['userMenu'])
        time.sleep(10)
        userMenu[-1].click()

        logout = self.elmwait.until(
            EC.visibility_of_element_located((By.XPATH, self.btn['logout']))
        )
        logout.click()

        time.sleep(10)

    def closeBrowser(self):
        """Close the currently open Selenium browser window."""
        log.info('Closing the browser...')

        self.driver.quit()
