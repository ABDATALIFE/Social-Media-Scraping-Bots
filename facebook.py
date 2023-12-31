import os
import time
import datetime
import warnings
import logging as log
from sys import exit as sys_exit

from urllib3.exceptions import MaxRetryError
from selenium import webdriver
from selenium.webdriver.remote.remote_connection import LOGGER
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    InvalidSelectorException
)

warnings.filterwarnings('ignore')


# NOTE there seems to be more elements that indicate the followers than
# the element 'followed by x people', test if the bot if capable of
# finding them all
#
# NOTE possible followers REs:
# - For friends: '[0-9]+,?[0-9]*(?= friends)'
# - For followed by: '[0-9]+,?[0-9]*(?= people</a>)'
# - For followers: '(?<=>)[0-9]+,?[0-9]*K?(?=<!-- --> followers)'
# These REs won't probably work with users than have 1 million
# followers or more
class fb:
    def __init__(
            self, users: list[dict[str, str]], browser: str,
            visible: bool = False, debug_selenium: bool = False):
        log.info('Facebook Scrapper')

        self.btn = {
            'log_usrnm': 'email',
            'log_userps': 'pass',
            'log_btn': '/html/body/div[1]/div[1]/div[1]/div/div/div/div[2]/div/div[1]/form/div[2]/button',
            'notificationIcon': 'a:not([aria-label=''])',
            'post': 'svg[title="Shared with Public"]',
            'post2': 'svg[title="Shared with Custom"]',
            'noPost': '/html/body/div[1]/div/div[1]/div/div[3]/div/div/div/div[1]/div[1]/div/div/div[4]/div[2]/div/div[2]/div[2]/div/span',
            'profilePic': '/html/body/div[1]/div/div[1]/div/div[3]/div/div/div/div[1]/div[1]/div/div/div[1]/div[2]/div/div/div/div[1]/div/div/div',
            'closeStory': '/html/body/div[1]/div/div[1]/div/div[2]/div[1]/div[1]/span/div',
            'next_story': 'div[aria-label="Next card button"]',
            'storyLen': '/html/body/div[1]/div/div[1]/div/div[4]/div/div/div[1]/div/div[3]/div[2]/div/div/div/div/div[3]/div/div/div/div[1]/div[1]/div[2]/div/div/div/div/div[2]',
            'postImg': '/html/body/div[1]/div/div[1]/div/div[3]/div/div/div/div[1]/div[1]/div[4]/div[1]',
            'tempBan': '/html/body/div[6]/div[1]/div/div[2]/div/div/div/div[1]/div/h2/span/span',
            'filterPost': 'div[aria-label="Filters"]',
            'postDate': 'div[class="__fb-dark-mode"] > div > span >div >div > span',
            'closePopup': '//div[@role="dialog"]//div[@aria-label="Done"]//span[contains(., "Done")]',
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
            if browser == 'chrome':
                self.options.binary_location = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
                self.options.add_argument(
                    f'--user-data-dir={os.environ["LOCALAPPDATA"]}\\Google\\Chrome\\User Data')
            else:
                self.options.binary_location = r'C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe'
                self.options.add_argument(
                    f'--user-data-dir={os.environ["LOCALAPPDATA"]}\\BraveSoftware\\Brave-Browser\\User Data')
        except:
            log.error('Data Directory in use!')

    def get(self, link: str, retries: int = 3) -> None:
        attempts = 0

        while attempts < retries:
            try:
                self.driver.get(link)

                break
            except WebDriverException as err:
                log.warning(
                    f'Error while connecting to {link}, retrying in 10 minutes'
                )
                log.debug(f'Connection error details: {err}')

                # NOTE put in a finally statement if more exceptions
                # get added
                attempts += 1

                time.sleep(600)
        else:
            # TODO send email on error
            log.error(
                'Connection attempts exceeded'
            )

            raise MaxRetryError('Manual call', link, 'Posible website down')

    def startBrowser(self):
        log.info('Opening browser...')

        self.userIdx = self.cuser%len(self.users)
        self.email = self.users[self.userIdx]['username']
        self.password = self.users[self.userIdx]['password']
        self.cuser = self.cuser+1

        if self.userIdx == 0:
            self.userIdx = len(self.users)

        self.userIdx = self.userIdx + 10
        self.options.add_argument('--profile-directory=Profile ' + str(self.userIdx))

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

        log.info('Going to facebook main page...')

        self.get('https://www.facebook.com/')

    def login(self):
        log.info(f'Login Facebook: {self.email}')
        try:
            username = self.elmwait.until(EC.visibility_of_element_located((By.ID, self.btn['log_usrnm'])))
            password = self.elmwait.until(EC.visibility_of_element_located((By.ID, self.btn['log_userps'])))
            login = self.elmwait.until(EC.visibility_of_element_located((By.XPATH, self.btn['log_btn'])))

            username.send_keys(self.email)
            password.send_keys(self.password)
            login.click()
            time.sleep(5)
            try:
                profileIcon = self.driver.find_elements(By.TAG_NAME, 'a')
                for a in profileIcon:
                    href = a.get_attribute('href')
                    if '/notifications/' in href:
                        return (True, (self.email, self.password))
                return ((False, (self.email, self.password)))
            except:
                return (False, (self.email, self.password))


        except:
            time.sleep(5)
            profileIcon = self.driver.find_elements(By.TAG_NAME, 'a')
            for a in profileIcon:
                href = a.get_attribute('href')
                if '/notifications/' in href:
                    return (True, (self.email, self.password))
            return ((False, (self.email, self.password)))


    def netwrok(self):
        try:
            ban = self.elmwait.until(EC.visibility_of_element_located((By.XPATH, self.btn['tempBan'])))
            return ((False, (self.email, self.password)))
        except:
            return ((True, (self.email, self.password)))

    def getUser(self, link):
        log.info(f'Going to user page: {link}')

        self.get(link)

        if not self.netwrok()[0]:
            return ((False, (self.email, self.password)))

        try:
            private = self.followers()

            # TODO change type comparison to isinstance
            if type(private) == type(False) and private == False:
                log.warning('This user has a private account, skipping...')

                return ([False])

            return ((True, (self.email, self.password)))
        except Exception:
            log.exception(
                f'An unknown error occurred while loading user page:'
            )

            return ([False])

    def followers(self):
        countTime = 1
        followers_ = None
        likes_ = None
        friends_ = None

        log.info('Getting user followers')

        while True:
            try:
                anchors = self.driver.find_elements(By.TAG_NAME, 'a')

                for anchor in anchors:
                    href = anchor.get_attribute('href')
                    text = anchor.get_attribute('innerText')

                    if href != None and text != None and 'followers' in href and 'people' in text:
                        followers = text
                        followers = int(''.join(filter(str.isdigit, followers)))
                        followers_ = int(followers)

                        return followers_
                    elif href != None and text != None and 'followers' in href and 'followers' in text:
                        if 'K' in text:
                            text = text.replace('followers', '').replace('K', '').strip()
                            followers = float(text) * 1000
                        elif 'M' in text:
                            text = text.replace('followers', '').replace('M', '').strip()
                            followers = float(text) * 1000000
                        else:
                            followers = int(''.join(filter(str.isdigit, text)))

                        followers = str(int(followers))
                        followers = int(''.join(filter(str.isdigit, followers)))
                        followers_ = int(followers)

                        return followers_
                    elif  href != None and text != None and 'friends_likes' in href and 'likes' in text:
                        if 'K' in text:
                            text = text.replace('likes','').replace('K','').strip()
                            followers = float(text) * 1000
                        elif 'M' in text:
                            text = text.replace('likes', '').replace('M', '').strip()
                            followers = float(text) * 1000000
                        else:
                            followers = int(''.join(filter(str.isdigit, text)))

                        followers = str(int(followers))
                        followers = int(''.join(filter(str.isdigit, followers)))
                        likes_ = int(followers)

                        return likes_

                    if followers_ != None:
                        return followers_

                spans = self.driver.find_elements(By.TAG_NAME, 'span')
                for span in spans:
                    text = span.get_attribute('innerText')

                    if text != None and ('people follow this' in text or 'person follows this' in text):
                        followers = text
                        followers = int(''.join(filter(str.isdigit, followers)))
                        followers_ = int(followers)

                        return followers_
            except Exception:
                _f = None

            if countTime == 3:
                break

            time.sleep(1)
            countTime = countTime + 1

        return False

    def stories(self):
        elmwait = WebDriverWait(self.driver, 5)
        stories_ = []
        countTime = 1
        while True:
            try:
                circles = self.driver.find_elements(By.CSS_SELECTOR, 'circle[stroke-width="4"]')
                if len(circles) > 1:
                    exits = circles[1]
                elif len(circles) == 1:
                    exits = circles[0]
                else:
                    return stories_

                viewed = exits.value_of_css_property('stroke')
                if 'rgb(206, 208, 212)' in viewed:
                    return stories_
                elif 'rgb(24, 118, 242)' in viewed:
                    pic = exits.find_element(By.XPATH, './..')
                    while True:
                        tag = pic.tag_name
                        label = pic.get_attribute('aria-label')

                        if tag == 'div' and label != None:
                            pic.click()
                            break
                        pic = pic.find_element(By.XPATH, './..')

                    countTime = 1
                    while True:
                        a = self.driver.find_elements(By.TAG_NAME, 'a')
                        for anchor in a:
                            if anchor.get_attribute('role') == 'menuitem' and '/stories/' in anchor.get_attribute('href'):
                                anchor.click()
                                time.sleep(1)
                                stories_ = self.driver.current_url
                                while True:
                                    try:
                                        next = elmwait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, self.btn['next_story']))).click()
                                        time.sleep(1)
                                    except Exception:
                                       break
                                self.driver.back()
                                return stories_
                                break
                        if countTime == 5:
                            break
                        time.sleep(1)
                        countTime = countTime + 1
            except Exception as err:
                _f = None
                log.debug(f'An unexpecter error ocurred: {err}')

            if countTime == 5:
                break
            countTime = countTime + 1
            time.sleep(1)
        return stories_

    # TODO make this method to only return tuples
    # NOTE there is a bug where the bot detects quoted posts as posts
    # from the user, fix that
    def posts(self, date: str) -> str | tuple[tuple[str], str, tuple[str]]:
        log.info('Getting user posts')

        self.driver.refresh()
        time.sleep(5)

        date_time = date.strip()
        posts_ = []
        error = 'unknown'
        countTime = 1
        countLen = 1
        fetch = True
        postSection = None

        try:
            log.debug('Looking for popups')
            popup = self.elmwait.until(EC.presence_of_all_elements_located(
                (By.XPATH, self.btn['closePopup'])
            ))

            log.debug('Popup window found, closing...')

            time.sleep(60)

            popup[-1].click()
        except TimeoutException:
            log.debug('Not popup windows found')

        time.sleep(20)
        html = self.driver.find_element(By.TAG_NAME, 'html')
        html.send_keys(Keys.END)

        time.sleep(2)
        html.send_keys(Keys.HOME)

        time.sleep(2)
        oldposts = []
        startLen = None

        while True:
            if fetch:
                try:
                    nopost = self.driver.find_element(By.XPATH, self.btn['noPost'])

                    log.warning('No posts found...')

                    return (posts_, error, (self.email, self.password))
                except:
                    _F = None

                if postSection == None:
                    publicIcon = self.driver.find_elements(By.CSS_SELECTOR, self.btn['post'])

                    if len(publicIcon) > 1:
                        publicIcon = publicIcon[1]
                        prnt = publicIcon.find_element(By.XPATH, './..')

                        countRow = 1
                        while True:
                            try:
                                tagName = prnt.tag_name
                                classes = prnt.get_attribute('class')
                                classes_ = classes.split(' ')

                                if tagName == 'div' and len(classes_) == 4:
                                    parent = prnt.find_element(By.XPATH, './..')
                                    parentclass = parent.get_attribute('class')

                                    if parentclass != '':
                                        divs = parent.find_elements(By.XPATH, './div')

                                        if len(divs) > 1:
                                            if divs[0].get_attribute('class') == divs[1].get_attribute('class') == classes:
                                                postSection = '.' + divs[0].find_element(By.XPATH, './..').get_attribute('class') + ' .' + classes.strip().replace(' ', '.')
                                                break
                                    else:
                                        if parent.get_attribute('role') == 'feed':
                                            postSection = 'div[role="feed"]:nth-child(2) .'+classes.strip().replace(' ','.')
                                            break
                                        else:
                                            parent = parent.find_element(By.XPATH, './..')
                                            divs = parent.find_elements(By.XPATH, './div')

                                            if len(divs) > 1:
                                                div1 = divs[0].find_element(By.XPATH, './div').get_attribute('class')
                                                div2 = divs[1].find_element(By.XPATH, './div').get_attribute('class')

                                                if div1 == div2 == classes:
                                                    # print('found2', classes,divs[0].find_element(By.XPATH, './..').get_attribute('class'))
                                                    postSection = '.'+classes.strip().replace(' ','.')
                                                    break
                                prnt = prnt.find_element(By.XPATH, './..')
                            except:
                                publicIcon = self.driver.find_element(By.CSS_SELECTOR, self.btn['post'])
                                prnt = publicIcon.find_element(By.XPATH, './..')

                                html = self.driver.find_element(By.TAG_NAME, 'html')
                                html.send_keys(Keys.END)
                                time.sleep(2)

                                html.send_keys(Keys.HOME)
                                time.sleep(2)

                                countRow = countRow + 1

                            if countRow == 3:
                                return 'reload'
                    elif len(publicIcon) == 1:
                        publicIcon = publicIcon[0]
                        child = publicIcon
                        prnt = publicIcon.find_element(By.XPATH, './..')
                        classes = prnt.get_attribute('class')

                        while True:
                            classes = prnt.get_attribute('class')

                            if classes == 'mfclru0v':
                                classes = child.get_attribute('class')
                                classes = '.' + classes.strip().replace(' ', '.')
                                postSection = classes
                                break

                            child = prnt

                            try:
                                prnt = prnt.find_element(By.XPATH, './..')
                            except InvalidSelectorException:
                                log.debug(
                                    'Reached html document, reloading page...'
                                )

                                self.driver.refresh()

                                time.sleep(60)

                                return self.posts(date)
                    else:
                        log.debug(
                            '"posts" element not found, retrying in 15 ' \
                                'minutes...'
                        )

                        self.driver.refresh()

                        time.sleep(900)

                        continue

                log.debug(f'Post section: {postSection}')

                posts = self.driver.find_elements(By.CSS_SELECTOR, postSection)
                postsU = posts

                if startLen == None:
                    startLen = len(postsU)

                if startLen == len(postsU) and countLen >=5:
                    break

                for old in oldposts:
                    oldhtml = old.get_attribute('outerHTML')

                    for new in posts:
                        newhtml = new.get_attribute('outerHTML')

                        if newhtml == oldhtml:
                            postsU.remove(new)

                log.debug(f'Length of postsU: {len(postsU)}')

                oldposts = oldposts + postsU
                for post in postsU:
                    postClass = post.get_attribute('class').split(' ')

                    if len(postClass) != 2:
                        pst = post.find_element(By.XPATH, './div')
                        classes = pst.get_attribute('class').split(' ')
                    else:
                        classes = postClass

                    if len(classes) == 2:
                        for x in range(3):
                            date = ''
                            postDate = ''
                            try:
                                for i in range(3):
                                    try:
                                        spans = post.find_element(
                                            By.CSS_SELECTOR,
                                            'span > span > span > a'

                                        )
                                        break
                                    except NoSuchElementException:
                                        log.error(
                                            'Date not found, retrying in ' \
                                                '10 minutes'
                                        )
                                        self.driver.refresh()

                                        time.sleep(600)
                                else:
                                    return 'reload'

                                try:
                                    ActionChains(self.driver).move_to_element(spans).perform()
                                except Exception:
                                    log.exception(f'Action:')

                                while True:
                                    try:
                                        postDate = self.elmwait.until(
                                            EC.visibility_of_element_located(
                                                (
                                                    By.CSS_SELECTOR,
                                                    self.btn['postDate']
                                                )
                                            )
                                        ).get_attribute('innerText')
                                        break
                                    except TimeoutException:
                                        try:
                                            ActionChains(self.driver).move_to_element(spans).perform()
                                            continue
                                        except:
                                            log.exception('ActionChains error: ')
                                            break

                                spans = spans.find_elements(By.TAG_NAME, 'span')
                                if len(spans) > 1:
                                    orders = []

                                    for span in spans:
                                        top = span.value_of_css_property('top')
                                        order = int(span.value_of_css_property('order'))
                                        spans_ = len(span.find_elements(By.XPATH, './*'))

                                        # TODO delete?
                                        log.debug(f'{top} {order} {spans_} {span.get_attribute("innerText")}')

                                        if (top == '0px' or top == 'auto') and spans_ == 0:
                                            orders.append({'order':order, 'text':span.get_attribute('innerText')})

                                    orders.sort(key=lambda a : a['order'])

                                    for text in orders:
                                        date = date + text['text']

                                    break
                                else:
                                    date = spans[0].get_attribute('innerText')
                                    break
                            except Exception:
                                log.exception('Date:')
                        try:
                            for i in range(3):
                                try:
                                    link = post.find_element(
                                        By.CSS_SELECTOR,
                                        'span span > a > span:not([class])'
                                    ).find_element(By.XPATH, './..')

                                    break
                                except (InvalidSelectorException,
                                        NoSuchElementException):
                                    log.error(
                                        'Link not found, retrying in 10 ' \
                                            'minutes'
                                    )
                                    self.driver.refresh()

                                    time.sleep(600)
                            else:
                                return 'reload'

                            try:
                                hover = ActionChains(self.driver).move_to_element(link)
                                hover.perform()
                            except Exception:
                                log.exception('Exception while hovering posts:')
                                _f = None

                            link = link.get_attribute('href')
                            if '/posts/' not in link and '/videos/' not in link and '/permalink.php'  not in link:
                               return 'reload'
                        except Exception:
                            log.exception('Link:')

                        if postDate != '':
                            postDate = postDate.strip()
                            postDateTime = (
                                datetime.datetime
                                .strptime(
                                    postDate,
                                    '%A, %B %d, %Y at %I:%M %p'
                                )
                                .strftime('%d/%m/%Y at %I:%M %p')
                            )
                        else:
                            continue

                        log.debug(
                            f'Post datetime: {postDateTime}, ' \
                            f'Last post: {date_time}, Date: {date}, ' \
                            f'Link: {link}'
                        )

                        postDateTimeD = datetime.datetime.strptime(
                            postDateTime,
                            '%d/%m/%Y at %I:%M %p'
                        )

                        if date_time == '':
                            log.debug('Last post date was empty')

                            today = datetime.datetime.today()
                            yesterday = today - datetime.timedelta(days=1)

                            if postDateTimeD > today or postDateTimeD > yesterday:
                                log.info(
                                    'Found new post, adding to list...'
                                )

                                posts_.append((link, postDateTime))
                            else:
                                log.info(
                                    'Found old post, changing to next user...'
                                )

                                break
                        else:
                            date_timeD = datetime.datetime.strptime(
                                date_time,
                                '%d/%m/%Y at %I:%M %p'
                            )

                            # NOTE this still can cause the bot to not
                            # register some posts as new if they where
                            # updated a second after the bot has
                            # finished getting posts from a user. For
                            # example: the bot registers the last post
                            # at 1:00:00 PM, but then the user uploads
                            # a new post at 1:00:30 PM. This might get
                            # fixed in the future by also checking the
                            # post ID
                            if postDateTimeD > date_timeD:
                                log.info('Found new post, adding to list...')
                                posts_.append((link, postDateTime))
                            else:
                                log.info(
                                    'Found old post, changing to next user...'
                                )
                                fetch = False

                                break

                if fetch:
                    countTime = 1
                else:
                    break

                if countTime == 2:
                    break

                time.sleep(1)
                countTime = countTime + 1
            else:
                break

            countLen = countLen + 1

        return (posts_, error, (self.email, self.password))

    def postTypes(self, posts):
        data = []
        for post in posts:
            time.sleep(10)
            self.get(post[0])
            # post[0].click()
            link = self.driver.current_url
            if '/reel/' in link or '/videos/' in link:
                data.append((link, post[1], 'video_reel'))
                continue

            elif '/watch/' in link or '/videos/' in link:
                data.append((link, post[1], 'video_reel'))
                continue
            else:
                data.append((link, post[1], 'picture'))
                continue
        return data

    def closeBrowser(self):
        log.info('Closing the browser...')

        self.driver.quit()
