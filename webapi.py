import os
import time
import json
import logging as log
from datetime import date

import requests
import pandas as pd
from requests.exceptions import ConnectionError
from urllib3.exceptions import NewConnectionError


class smmfollowers:
    def __init__(self, key):
        self.key = key
        self.url = 'https://smmfollows.com/api/v2'

    def req(self, params, wait=True):
        try:
            req = requests.post(self.url, data=params)
        except (ConnectionError, NewConnectionError):
            log.error(f'Couldn\'t connect to {self.url}, retrying in 5 minutes')

            time.sleep(300)

            req = requests.post(self.url, data=params)

        if req.status_code == 200:
            try:
                if 'error' not in req.json():
                    return req.json()
                else:
                    if wait:
                        log.debug(f'{self.url} {req.json()}')
                        log.info('Requesting again in 5 minutes...')
                        time.sleep(5 * 60)
                        return self.req(params, wait)
                    else:
                        if 'multiple of 100' in req.json()['error']:
                            quantity = params['quantity']
                            mod = 100 - (int(quantity) % 100)
                            params['quantity'] = quantity + mod
                            return self.req(params, wait)
                        else:
                            return req.json()
            except:
                log.error(f'Error: {req}')
                return {'Error': req}
        else:
            return {'Error': req.status_code}

    def services(self):
        params = {'key': self.key, 'action': 'services'}
        return self.req(params)

    def minQuantity(self, id):
        while True:
            services = self.services()

            if 'Error' in services:
                log.warning(
                    'Problem while getting smmfollowers services, retrying ' \
                        'in 5 minutes...'
                )

                time.sleep(300)

                continue
            else:
                break

        for service in services:
            serviceId = int(service['service'])
            if serviceId == id:
                return int(service['min'])


    def newOrder(self, id, link, quantity):
        id = int(id)
        minQuant = self.minQuantity(id)
        if int(quantity) < int(minQuant):
            quantity = int(minQuant)
        params = {'key': self.key, 'action': 'add', 'service': id, 'link': link, 'quantity': quantity}
        return self.req(params, False)
        # return {'order': 17374921}

    def orderStatus(self, orderId):
        params = {'key': self.key, 'action': 'status', 'order': orderId}
        return self.req(params)

    def balance(self):
        params = {'key': self.key, 'action': 'balance'}
        return self.req(params)

class paytosmm:
    def __init__(self, key):
        self.key = key
        self.url = 'https://paytosmm.com/api/v2'

    def req(self, params, wait=True):
        try:
            req = requests.post(self.url, data=params)
        except (ConnectionError, NewConnectionError):
            log.error(f'Couldn\'t connect to {self.url}, retrying in 5 minutes')

            time.sleep(300)

            req = requests.post(self.url, data=params)

        if req.status_code == 200:
            try:
                if 'error' not in req.json():
                    return req.json()
                else:
                    if wait:
                        log.debug(f'{self.url} {req.json()}')
                        log.info('Requesting again in 5 minutes...')
                        time.sleep(5 * 60)
                        return self.req(params, wait)
                    else:
                        if 'multiple of 100' in req.json()['error']:
                            quantity = params['quantity']
                            mod = 100 - (int(quantity) % 100)
                            params['quantity'] = quantity + mod
                            return self.req(params, wait)
                        else:
                            return req.json()
            except:
                log.error(f'Error: {req}')
                return {'Error': req}
        else:
            return {'Error': req.status_code}

    def services(self):
        params = {'key': self.key, 'action': 'services'}
        return self.req(params)

    def minQuantity(self, id):
        while True:
            services = self.services()

            if 'Error' in services:
                log.warning(
                    'Problem while getting smmfollowers services, retrying ' \
                        'in 5 minutes...'
                )

                time.sleep(300)

                continue
            else:
                break

        for service in services:
            serviceId = int(service['service'])
            if serviceId == id:
                return int(service['min'])

    def newOrder(self, id , link , quantity):
        id = int(id)
        minQuant = self.minQuantity(id)
        if int(quantity) < int(minQuant):
            quantity = int(minQuant)
        params = {'key': self.key, 'action': 'add', 'service': id, 'link': link, 'quantity': quantity}
        return self.req(params, False)
        # return {'order': 9842080}

    def orderStatus(self, orderId):
        params = {'key': self.key, 'action': 'status', 'order': orderId }
        return self.req(params)

    def balance(self):
        params = {'key': self.key, 'action': 'balance'}
        return self.req(params)


class websiteApi:
    def __init__(self, data, mail, bot):
        self.mail = mail
        self.data = data
        self.bot = bot
        self.file = f'{bot[:2]}_data.json'
        self.smmfollowers = smmfollowers(self.data['webapi']['smmfollowers']['key'])
        self.smmBalance = self.smmfollowers.balance()
        self.paytosmm = paytosmm(self.data['webapi']['paytosmm']['key'])
        self.pytsmBalance = self.paytosmm.balance()
        self.followerStart = 1
        self.followerPrStart = 1
        self.followerPgStart = 1
        self.likesStart = 1
        self.videoviewStart = 1
        self.videolikesStart = 1
        self.igsavepostStart = 1
        self.impressionandreacheStart = 1
        self.reelviewStart = 1
        self.reallikesStart = 1

    def setOrder(self, orders):
        self.order = orders
        self.validateId()

    def isId(self, id, services):
        exist = False
        for service in services:
            serviceId = int(service['service'])
            if serviceId == id:
                exist = True
                break
        return exist

    def validateId(self) -> None:
        log.info('Validating Order ID\'s...')

        newOrder = {}

        while True:
            pytservices = self.paytosmm.services()
            smmservices = self.smmfollowers.services()

            if 'Error' in smmservices or 'Error' in pytservices:
                log.error(
                    'Could not get SMM services, retrying in 10 minutes...'
                )

                time.sleep(600)

                continue
            else:
                break

        for types in self.order:
            valid = []
            ids = self.order[types]
            for id in ids:
                if 'smmfollows.com' in id[0]:
                    if self.isId(int(id[1]), smmservices):
                        log.info(f'Found valid ID {id}')
                        valid.append(id)
                    else:
                        log.warning(f'INVALID ID! {id}')
                        df = pd.DataFrame([id], columns=['Website', 'ID'])
                        self.mail.sendMail(f'{self.bot} (Invalid ID!)', 'Invalid ID!', df.to_html())
                elif 'paytosmm.com' in id[0]:
                    if self.isId(int(id[1]), pytservices):
                        log.info(f'Found valid ID {id}')
                        valid.append(id)
                    else:
                        log.warning(f'INVALID ID! {id}')
                        df = pd.DataFrame([id], columns=['Website', 'ID'])
                        self.mail.sendMail(f'{self.bot} (Invalid ID!)', 'Invalid ID!', df.to_html())
            if len(valid) == 0:
                log.warning(f'NO VALID ID FOUND ({types})!\n Update Order IDs!')
                self.mail.sendMail(f'{self.bot} (NO VALID ID FOUND!)', 'NO VALID ID!', f'NO VALID ID FOUND ({types})!\nUpdate Order IDs!')
                continue
            newOrder[types] = valid
        self.order = newOrder

    def writeOrder(self, link, orderid, status, type, date):
        file_exists = os.path.isfile(self.file)
        if not file_exists:
            with open(self.file, 'w') as outfile:
                json.dump([], outfile)
                data = []
        else:
            with open(self.file, 'r') as openfile:
                data = json.load(openfile)
        data.append({'link': link, 'orderId': orderid, 'status': status, 'type': type, 'date': date})
        with open(self.file, 'w') as outfile:
            json.dump(data, outfile)
            return True

    def isOrdered(self, link, d1, type):
        log.info(f'Checking {type} order status for {link} on {d1}')
        file_exists = os.path.isfile(self.file)
        if file_exists:
            with open(self.file, 'r') as openfile:
                data = json.load(openfile)
                for idx, order in enumerate(data):
                    if order['link'] == link and order['type'] == type:
                        if type == 'followers':
                            if order['date'] == d1:
                                log.debug('Marking followers as ordered')
                                return True
                        else:
                            log.debug(f'Marking order of {type} as ordered')
                            return True
                log.debug(f'Marking {type} as not ordered')
                return False

    # TODO make it show the balance?
    def balance(self) -> dict[str, list[tuple] | bool]:
        while True:
            self.smmBalance = self.smmfollowers.balance()
            self.pytsmBalance = self.paytosmm.balance()

            if 'balance' in self.smmBalance.keys() and 'balance' in self.pytsmBalance.keys():
                result = {'data': [
                    (
                        'https://smmfollows.com/',
                        self.smmBalance['balance'],
                        self.smmBalance['currency']
                    ),
                    (
                        'https://paytosmm.com/',
                        self.pytsmBalance['balance'],
                        self.pytsmBalance['currency']
                    )
                ]}

                break
            else:
                log.error(f'Unable to fetch Balance! {self.smmBalance} {self.pytsmBalance}')
                log.info('Retrying in 5 minutes...')
                time.sleep(300)

        if (float(self.smmBalance['balance']) <= self.data['minAmount']
                or float(self.pytsmBalance['balance']) <= self.data['minAmount']):
            result['enough'] = False
        else:
            result['enough'] = True

        return result

    def newOrder(self, postLink, value, type, d1, userType):
        ordered = self.isOrdered(postLink, d1, type)
        orderId = 'NotOrdered'
        if not ordered:
            if type == 'followers' and self.data['features']['followers']:
                if userType == 'fb personal lists' and 'followersProfile' in self.order:
                    api = self.order['followersProfile'][self.followerPrStart % len(self.order['followersProfile'])]
                elif userType == 'fb page lists' and 'followersPage' in self.order:
                    api = self.order['followersPage'][self.followerPgStart % len(self.order['followersPage'])]
                elif userType == 'instagram user' and 'followers' in self.order:
                    api = self.order['followers'][self.followerStart % len(self.order['followers'])]
                else:
                    return False

                if 'smmfollows' in api[0]:
                    log.info(f'{api[0]} {api[1]} {postLink} {value} {type}')
                    orderId = self.smmfollowers.newOrder(api[1], postLink, value)
                    if 'error' in orderId:
                        log.info(f'ERROR: {postLink} {orderId["error"]}')
                        return True
                    else:
                        status = self.smmfollowers.orderStatus(orderId['order'])

                elif 'paytosmm' in api[0]:
                    log.info(f'{api[0]} {api[1]} {postLink} {value} {type}')
                    orderId = self.paytosmm.newOrder(api[1], postLink, value)
                    if 'error' in orderId:
                        log.error(f'ERROR: {postLink} {orderId["error"]}')
                        return True
                    else:
                        status = self.paytosmm.orderStatus(orderId['order'])
                if userType == 'fb personal lists':
                    self.followerPrStart = self.followerPrStart + 1
                elif userType == 'fb page lists':
                    self.followerPgStart = self.followerPgStart + 1


            elif type == 'picture' and self.data['features']['likes']:
                api = self.order['likes'][self.likesStart % len(self.order['likes'])]

                if 'smmfollows' in api[0]:
                    log.info(f'{api[0]} {api[1]} {postLink} {value} {type}')
                    orderId = self.smmfollowers.newOrder(api[1], postLink, value)
                    if 'error' in orderId:
                        log.error(f'ERROR: {postLink} {orderId["error"]}')
                        return True
                    else:
                        status = self.smmfollowers.orderStatus(orderId['order'])

                elif 'paytosmm' in api[0]:
                    log.info(f'{api[0]} {api[1]} {postLink} {value} {type}')
                    orderId = self.paytosmm.newOrder(api[1], postLink, value)
                    if 'error' in orderId:
                        log.error(f'ERROR: {postLink} {orderId["error"]}')
                        return True
                    else:
                        status = self.paytosmm.orderStatus(orderId['order'])

                self.likesStart = self.likesStart + 1

            elif type == 'videoViews' and self.data['features']['view videos']:
                api = self.order['view videos post'][self.videoviewStart % len(self.order['view videos post']) ]

                if 'smmfollows' in api[0]:
                    log.info(f'{api[0]} {api[1]} {postLink} {value} {type}')
                    orderId = self.smmfollowers.newOrder(api[1], postLink, value)
                    if 'error' in orderId:
                        log.error(f'ERROR: {postLink} {orderId["error"]}')
                        return True
                    else:
                        status = self.smmfollowers.orderStatus(orderId['order'])

                elif 'paytosmm' in api[0]:
                    log.info(f'{api[0]} {api[1]} {postLink} {value} {type}')
                    orderId = self.paytosmm.newOrder(api[1], postLink, value)
                    if 'error' in orderId:
                        log.error(f'ERROR: {postLink} {orderId["error"]}')
                        return True
                    else:
                        status = self.paytosmm.orderStatus(orderId['order'])
                self.videoviewStart = self.videoviewStart + 1

            elif type == 'videoLikes' and self.data['features']['video post likes']:
                api = self.order['video post likes'][self.videolikesStart % len(self.order['video post likes'])]

                if 'smmfollows' in api[0]:
                    log.info(f'{api[0]} {api[1]} {postLink} {value} {type}')
                    orderId = self.smmfollowers.newOrder(api[1], postLink, value)
                    if 'error' in orderId:
                        log.error(f'ERROR: {postLink} {orderId["error"]}')
                        return True
                    else:
                        status = self.smmfollowers.orderStatus(orderId['order'])

                elif 'paytosmm' in api[0]:
                    log.info(f'{api[0]} {api[1]} {postLink} {value} {type}')
                    orderId = self.paytosmm.newOrder(api[1], postLink, value)
                    if 'error' in orderId:
                        log.error(f'ERROR: {postLink} {orderId["error"]}')
                        return True
                    else:
                        status = self.paytosmm.orderStatus(orderId['order'])
                self.videolikesStart = self.videolikesStart + 1



            if orderId and orderId != 'NotOrdered':
                return self.writeOrder(postLink, orderId, status, type, d1)
            else:
                return orderId

        else:
            log.info(f'Already ordered {value} {type} for user {postLink} today, skipping...')
            return True

class testApi:
    # TODO do something with data and email?
    def __init__(self, *_):
        log.info('Test started')
        self.enoughBalance = True

    # TODO return orderId and self.writeOrder result
    def newOrder(self, *_):
        log.info('New order started')
        return True

    def setOrder(self, orders):
        log.info(f'Orders: {orders}')

    def balance(self) -> dict[str, list[tuple] | bool]:
        log.info('Getting balance')

        result = {
            'enough': self.enoughBalance,
            'data': [
                ('https://smmfollows.com/', 0.0, 'USD'),
                ('https://paytosmm.com/', 0.0, 'USD')
            ]
        }

        return result
