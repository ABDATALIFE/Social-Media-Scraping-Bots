# TODO make a notification system with emails

__version__ = 'v1.0'
__author__ = 'IllustriousJelly'

import logging as log
from sys import exit
from re import search
from time import sleep
from datetime import date
from os.path import exists
from datetime import datetime
from json import load as json_load, dump as json_dump

from emailclient import email
from spreadsheet import Spread

DEBUG = False


# TODO change class name?
class sender(email):
    def __init__(self):
        if DEBUG:
            settings = 'EM_test_settings.json'
        else:
            settings = 'EM_settings.json'

        with open(settings) as f:
            self.data = json_load(f)

        super().__init__(self.data)

    def run(self):
        log.info('Program started')

        self.registry = self.loadRegistry()

        today = date.today().strftime('%d/%m/%Y')
        log.debug(f'Date from today: {today}')

        if today in self.registry and self.registry[today]['completed']:
            log.info('Already sent messages today, skipping...')

            return None
        elif today not in self.registry:
            self.registry[today] = {'completed': False}

            self.updateDatabase()

        # NOTE should use a walrus operator to avoid accessing
        # self.data twice?
        log.info(f'Opening googlesheet: {self.data["googlesheet"]}')
        self.googlesheet = Spread(self.data['googlesheet'])
        self.googlesheet.setSheet('Accounts')

        usersData = self.loadUsersData()

        log.info('Selecting column with account links')
        # TODO assert that the loop checks all row cells
        accounts = self.googlesheet.get_col(2)
        for r in range(1, len(accounts)):
            account = accounts[r]
            assert isinstance(account, str)

            if account not in usersData:
                log.warning(
                    f'User {account} not found in local data, skipping...'
                )

                continue
            elif account in self.registry[today] \
            and self.registry[today][account]['completed']:
                log.info(
                    f'All messages for account {account} where already ' \
                    'sent today, skipping...'
                )

                continue
            elif account not in self.registry[today]:
                self.registry[today][account] = {
                    'completed': False,
                    'likes': {'completed': False, 'numbers': []},
                    'comments': {'completed': False, 'numbers': []},
                    'save_posts': {'completed': False, 'numbers': []}
                }

                self.updateDatabase()

            log.debug(f'Got account: {account}')

            followers = usersData[account]
            log.debug(f'Number of followers: {followers}')
            self.googlesheet.set_cell(r+1, 4, followers)

            results = self.applyPercentages(int(followers))
            if results is None:
                continue

            results = self.updateArrangements(followers, r+1, results)
            log.debug(f'User {account} data: {results}')
            for c in results:
                if self.registry[today][account][c]['completed']:
                    log.info('Column already completed, skipping...')

                    break

                for n in results[c]['numbers']:
                    log.debug(f'Selected row {n} for {c}')

                    if n in self.registry[today][account][c]['numbers']:
                        log.info(
                            'Selected an already sent email, skipping...'
                        )

                    if DEBUG:
                        subject = 'Test'
                    else:
                        subject = 'Working'

                    email, message = self.getEmailMessage(c, int(n), today, r+1)

                    self.changeReceiver(email)

                    log.info(f'Got all data, sending message to: {email}')
                    self.sendMail(subject, '', message)

                    log.info('Message sent!')
                    self.registry[today][account][c]['numbers'].append(n)
                    self.updateDatabase()

                self.registry[today][account][c]['completed'] = True
                self.updateDatabase()

            self.registry[today][account]['completed'] = True
            self.updateDatabase()

            self.googlesheet.setSheet('Accounts')

        self.registry[today]['completed'] = True
        self.updateDatabase()

        log.info('Successfully sent all messages for today')

    def listNumbers(self, numbers: str) -> list[str]:
        """Gets a string of numbers separated by commas, and safely converts
        them into a list of strings
        """

        formattedNumbers = numbers.replace('.', ',')

        clearedNumbers = formattedNumbers.strip(',')

        numberList = clearedNumbers.split(',')

        return numberList

    def changeReceiver(self, newReceiver: str) -> None:
        # NOTE should validate the receiver address to avoid errors?
        self.receiver = newReceiver

    def openDatabase(self):
        if DEBUG:
            db = 'EM_test_database.json'
        else:
            db = 'EM_database.json'

        if exists(db):
            self.database = open(db, 'r+')
        else:
            self.database = open(db, 'x+')

            json_dump({}, self.database)
            self.database.seek(0)

        log.debug('Database opened successfully')

    def closeDatabase(self):
        self.database.close()

        log.debug('Database closed successfully')

    def updateDatabase(self) -> None:
        log.debug(f'Updating database with new data: {self.registry}')

        if self.database.tell() != 0:
            self.database.seek(0)

        self.database.truncate(0)

        json_dump(self.registry, self.database)
        self.database.seek(0)

    def loadRegistry(self):
        if self.database.tell() != 0:
            self.database.seek(0)

        registry = json_load(self.database)
        self.database.seek(0)

        return registry

    # NOTE this might cause some problems in the case where the other
    # bots are writing to their respective files at the same time this
    # bot is reading data from those file, though this is a rare case,
    # this should be fixed
    def loadUsersData(self) -> dict[str, str]:
        data: dict[str, str] = {}

        for f in ('FB_followers.json', 'IG_followers.json'):
            with open(f, 'r') as file:
                data.update(json_load(file))

        return data

    def applyPercentages(self, followers: int) -> dict[str, str | int] | None:
        log.info('Calculating percentages')

        results: dict[str, str] = {}
        percentages: list[str] | None = None

        self.googlesheet.setSheet('Ig Info')

        ranges = self.googlesheet.get_row(1)

        for i in range(len(ranges)):
            range_ = ranges[i].strip(' followers').split('-')

            if followers > int(range_[0]) and followers < int(range_[1]):
                percentages = self.googlesheet.get_col(i+1)

                log.debug(f'Got percentages: {percentages}')

                break

        if percentages is None:
            log.error(f'Number of followers is not supported, skipping...')

            return None

        for p in percentages[1:]:
            formattedP = p.strip(' IiGg').replace(' posts', '_posts')
            category, percentage = formattedP.split(' ')

            results[category] = {
                'percentage': percentage,
                'result': followers*int(percentage.strip('%')) // 100
            }

        log.debug('Percentage results: {results}')

        return results

    # TODO improve docstring
    def updateArrangements(
        self,
        followers,
        row,
        data: dict[str, str | int]
    ) -> dict[str, str | int]:
        """Updates the "Arrangements" sheet"""

        self.googlesheet.setSheet('Manual')

        # NOTE loading all sequences no matter how many will be needed
        # is not optimum, try to find a way to optimize this
        # NOTE should put it in a separated method so it can have unit
        # tests?
        numbersColumn = self.googlesheet.get_col(1)
        numbersString = ','.join(numbersColumn)
        # NOTE this could cause problems in case of trailing commas and
        # dots, fix it
        assert numbersString.endswith(',') == False \
            and '.' not in numbersString
        allNumbers = numbersString.split(',')

        self.googlesheet.setSheet('Arrangements')

        # NOTE should find a way to make this line shorter
        followersArrangement = f'{followers} ' \
            f'( {data["likes"]["percentage"]} ' \
            f'= {data["likes"]["result"]} ) ' \
            f'( {data["comments"]["percentage"]} ' \
            f'= {data["comments"]["result"]} ) ' \
            f'( {data["save_posts"]["percentage"]} ' \
            f'= {data["save_posts"]["result"]} )'

        self.googlesheet.set_cell(row, 2, followersArrangement)
        for i, c in enumerate(data):
            numbers = allNumbers[:data[c]['result']]

            self.googlesheet.set_cell(row, i+3, ','.join(numbers))

            data[c]['numbers'] = numbers

        return data

    # TODO finish
    def getEmailMessage(
        self,
        category: str,
        number: int,
        date: str,
        userRow: int
    ) -> tuple[str, str]:
        """Get's the corresponding email address and builds the corresponding
        message by gathering all the necessary data
        """

        # NOTE temporal fix to the google API quota exceeding, fix this
        # with fewer calls to the API instead
        sleep(number*2)

        self.googlesheet.setSheet('Msg')

        match category:
            case 'likes':
                messageRow = 2
            case 'comments':
                messageRow = 4
            case 'save_posts':
                messageRow = 6
            case _:
                raise ValueError(f'Unknown category: {category}')

        message = self.googlesheet.get_cell(messageRow, 1)

        self.googlesheet.setSheet('Send')

        email, accountInfo = self.googlesheet.get_row(number)

        # NOTE should compile outside and then search instead?
        app = search('(?<=\\( ).+(?= \\))', accountInfo)
        accountName = search('(?<=- ).+(?= \\()', accountInfo)

        message = message.replace(
            '( account and app )',
            f'{accountName.group()} {app.group()}'
        )

        self.googlesheet.setSheet('Arrangements')
        
        userData = self.googlesheet.get_cell(userRow, 1)
        userAccount = search('(?<=\\( ).+(?= \\))', userData)
        link = search('https://.+(?= \\()', userData)

        message = message.replace('( account name )', userAccount.group())
        message = message.replace('( link )', link.group())

        message = message.replace('(15/11/2022)', date)

        log.debug(f'Message built, result: {message}')

        return email, message

    def wait(self) -> None:
        today = datetime.today()

        tomorrow = today.day+1

        while True:
            sleep(10)

            today = datetime.today()

            if today.day == tomorrow:
                break

            if DEBUG:
                tomorrow -= 1

            log.debug('Not the next day yet, waiting...')


if __name__ == '__main__':
    try:
        if DEBUG:
            level = log.DEBUG
        else:
            level = log.INFO

        # NOTE should add a logs file? And if that's the case, should also
        # define a logs folder?
        log.basicConfig(level=level)

        bot = sender()

        bot.openDatabase()

        while True:
            # NOTE should run it in a different thread/process?
            bot.run()

            bot.wait()
    except KeyboardInterrupt:
        print('Program stopped manually')
    finally:
        bot.closeDatabase()
