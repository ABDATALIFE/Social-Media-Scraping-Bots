"""Module with classes that extend the functionality of the base SM bots."""

import logging as log
from sys import stdout
from datetime import datetime
from argparse import ArgumentParser, Namespace
from smtplib import SMTPDataError, SMTPServerDisconnected

from urllib3.exceptions import MaxRetryError
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import WebDriverException, TimeoutException

from fb_bot import Main as FacebookBot
from ig_bot import Main as InstagramBot
from email_bot import sender as EmailBot

class ExtendedFacebookBot(FacebookBot):
    """A FacebookBot subclass that implements some debugging enhancements."""

    def __init__(self, options: Namespace):
        self.crashes: int = 0
        super().__init__(options)

    @property
    def browserDriver(self) -> WebDriver:
        """Return the Selenium WebDriver used by the currently used scrapping
        class.
        """
        return self.facebook.driver

    def handleCrash(self) -> None:
        """Execute parent handleCrash method, take a screenshot of the current
        Selenium browser window, then get the HTML code of the current page and
        store it in a file, and lastly close the current Selenium browser
        window.

        If there is no open Selenium window, skip the screenshot taking, the
        HTML code getting and Selenium browser window closing processes.
        """
        self.crashes += 1
        log.debug('Current number of crashes: %s', self.crashes)

        openWindow = True

        try:
            self.browserDriver.window_handles
        except (WebDriverException, MaxRetryError, AttributeError) as err:
            log.info('Window already closed')
            log.debug('Error details: %s', str(err))
            openWindow = False

        if openWindow:
            now = datetime.now().strftime('%H%M%S_%d%m%y')

            with open(f'debug/html/{now}.html', 'w', encoding='utf-8') as file:
                file.write(self.browserDriver.page_source)

            try:
                self.browserDriver.save_screenshot(
                    f'debug/screenshots/{now}.png'
                )
            except TimeoutException:
                log.error('Couldn\'t take screenshot, skipping...')

            try:
                self.browserDriver.closeBrowser()
            except AttributeError:
                log.info(
                    'The browser window couldn\'t be closed or it doesn\'t ' \
                        'exists'
                )

        if self.crashes == 3:
            self.crashes = 0

            try:
                super().handleCrash()
            except SMTPServerDisconnected:
                log.info('Email server is down, skipping...')
            except SMTPDataError:
                log.info(
                    'Daily email message sending limit exceeded, skipping...'
                )

    def sendOrders(
            self, userLink: str, followers: int, oldPosts: int,
            newPosts: list[list[str]], infos: list[tuple[list[int] | int]],
            typeP: str) -> bool:
        self.crashes = 0
        return super().sendOrders(
            userLink, followers, oldPosts, newPosts, infos, typeP
        )


class ExtendedInstagramBot(InstagramBot, ExtendedFacebookBot):
    """A InstagramBot subclass that implements some of the debugging
    enhancements of the ExtendedFacebookBot class.
    """

    def __init__(self, options: Namespace):
        self.crashes: int = 0
        super().__init__(options)

    @property
    def browserDriver(self) -> WebDriver:
        """Return the Selenium WebDriver used by the currently used scrapping
        class.
        """
        return self.instagram.driver

    def handleCrash(self):
        """Call ExtendedFacebookBot handleCrash method."""
        ExtendedInstagramBot.__bases__[1].handleCrash(self)

    def sendOrders(
            self, userLink: str, followers: int, oldPosts: int,
            newPosts: list[list[str]], infos: list[tuple[list[int] | int]],
            typeP: str) -> bool:
        self.crashes = 0
        return super().sendOrders(
            userLink, followers, oldPosts, newPosts, infos, typeP
        )


class ExtendedEmailBot(EmailBot):
    def __init__(self, *_):
        super().__init__()

    def start(self):
        self.openDatabase()
        while True:
            self.run()
            self.wait()

    def __del__(self):
        self.closeDatabase()


def parseArgs():
    """Define the arguments for the script and return the parsed arguments."""
    parser = ArgumentParser()
    parser.add_argument(
        'bot', choices=('ig', 'fb', 'email'),
        help='Select the SM bot to use'
    )
    parser.add_argument(
        '--use-chrome', action='store_true',
        help='Make the selected bot use Chrome as the Selenium browser ' \
            'instead of using Brave'
    )
    parser.add_argument(
        '--use-brave', action='store_true',
        help='Make the selected bot use Brave as the Selenium browser ' \
            'instead of using Chrome'
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

    match args.bot:
        case 'ig':
            NAME = 'IG'
            BotClass = ExtendedInstagramBot
        case 'fb':
            NAME = 'FB'
            BotClass = ExtendedFacebookBot
        case 'email':
            NAME = 'Email'
            BotClass = ExtendedEmailBot

    if args.show_debug:
        LEVEL = log.DEBUG
    else:
        LEVEL = log.INFO

    log.basicConfig(
        level=LEVEL, filename=f'{NAME}_log.log', filemode='w',
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%d/%m/Y %I:%M:%S %p'
    )

    # Allows to log both into a file and into stdout
    log.getLogger().addHandler(log.StreamHandler(stdout))

    bot = BotClass(args)

    try:
        bot.start()
    except KeyboardInterrupt:
        log.info('Program stopped manually')
    finally:
        del bot
