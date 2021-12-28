from selenium import webdriver
import zoneinfo
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import requests
from datetime import datetime, timedelta
import json
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

LOCAL_TZ_STRING = 'America/Los_Angeles'
LOCAL_TZ = zoneinfo.ZoneInfo(LOCAL_TZ_STRING)
UTC_TZ_STRING = 'UTC'
UTC_TZ = zoneinfo.ZoneInfo(UTC_TZ_STRING)
TOKEN_FILE = 'secrets/vetter-token'

class VetterTools:
    def __init__(self):
        self.creds = None
        self.token = None
        self.business_id = None
        self.clientsByPhoneNumber = dict()

    def login(self):
        self.getCreds()
        self.readToken()
        if not self.validateToken():
            self.getToken()

    def getCreds(self):
        with open('secrets/vetter_creds.json') as fp:
            self.creds = json.load(fp)

    def getToken(self):
        if self.creds is None:
            raise RuntimeError('creds not available')
        creds = self.creds

        options = Options()
        options.headless = True
        capabilities = DesiredCapabilities.CHROME
        capabilities["goog:loggingPrefs"] = {"performance": "ALL"}

        with webdriver.Chrome(options=options, desired_capabilities=capabilities) as driver:
            driver.get("https://www.vettersoftware.com/apps/index.php/october/login")
            name = driver.find_element(By.NAME, 'fm_login_email')
            password = driver.find_element(By.NAME, 'fm_login_password')

            name.send_keys(creds['user'])
            password.send_keys(creds['password'])

            login = driver.find_element(By.ID, 'btn-login')
            login.click()

            time.sleep(5)
            logs = driver.get_log("performance")

            for log in logs:
                network_log = json.loads(log["message"])["message"]
                if "Network.request" in network_log["method"] and 'headers' in network_log['params'] \
                        and 'vetter-token' in network_log['params']['headers']:
                    self.token = network_log['params']['headers']['vetter-token']
                    for cookie in network_log['params']['associatedCookies']:
                        if cookie['cookie']['name'] == 'active_business_id':
                            self.business_id = cookie['cookie']['value']
                    self.writeToken(self.token, self.business_id)
                    return

    def readToken(self):
        try:
            with open(TOKEN_FILE, 'r') as fp:
                self.token = fp.readline().replace('\n', '')
                self.business_id = fp.readline()
        except:
            print("no token file found")

    def writeToken(self, token, id):
        with open(TOKEN_FILE, 'w') as fp:
            fp.write(token + '\n' + id)

    def setToken(self, token):
        self.token = token

    def validateToken(self):
        headers = {
            'vetter-token': self.token
        }
        r = requests.get('https://www.vettersoftware.com/barramundi/actor/staff', headers=headers)
        return r.status_code == 200

    def getAppointments(self, days):
        if self.token is None:
            raise RuntimeError('token not available')

        appointments = list()

        today = datetime.today()
        todayDt = datetime(today.year, today.month, today.day, tzinfo=UTC_TZ)
        start = todayDt.isoformat().replace('+00:00', '.000Z')
        end = (todayDt + timedelta(days=days)).isoformat().replace('+00:00', '.000Z')

        params = {
            'start': start,
            'end': end,
        }
        headers = {
            'vetter-token': self.token
        }
        response = requests.get('https://www.vettersoftware.com/barramundi/schedule/appointment',
                     params=params, headers=headers)
        events = json.loads(response.content)['response']['resources']
        for event in events:
            r = requests.get('https://www.vettersoftware.com/barramundi/schedule/appointment/' + event['id'],
                                    headers=headers)
            appointment = json.loads(r.content)['response']['resources']
            # fill some defaults
            if 'patient' not in appointment or appointment['patient'] is None:
                appointment['patient'] = {'name': 'unknown'}
            appointments.append({
                'start': appointment['start'],
                'end': appointment['end'],
                'address': appointment['appointment_location']['address_label'],
                'client': appointment['client']['firstname'] + ' ' + appointment['client']['lastname'],
                'patient': appointment['patient']['name'],
                'complaint': appointment['reason'],
                'notes': appointment['note'],
            })
        return appointments

    def loadClients(self):
        headers = {
            'vetter-token': self.token
        }
        params = {
            'perPage': 200,
            'page': 1
        }
        body = {
            'meta': {
                'nextPageUrl': 'https://www.vettersoftware.com/barramundi/actor/client?page1'
            }
        }
        while body['meta']['nextPageUrl']:
            response = requests.get('https://www.vettersoftware.com/barramundi/actor/client',
                                    params=params, headers=headers)
            if response.status_code != 200:
                print('failed to get client list')
                raise RuntimeError('failed to get client list')

            params['page'] += 1
            body = json.loads(response.content)['response']
            for client in body['resource']['data']:
                phone_numbers = self.getClientNumbers(client)
                for phone_number in phone_numbers:
                    self.clientsByPhoneNumber[phone_number] = client

    def getClientNumbers(self, client):
        phone_numbers = list()
        if client['home'] is not None and client['home'] != '':
            phone_numbers.append(self.normalizeNumber(client['home_country_code'], client['home']))
        if client['mobile'] is not None and client['mobile'] != '':
            phone_numbers.append(self.normalizeNumber(client['mobile_country_code'], client['mobile']))
        if client['work'] is not None and client['work'] != '':
            phone_numbers.append(self.normalizeNumber(client['work_country_code'], client['work']))
        return phone_numbers

    def normalizeNumber(self, country_code, number):
        country_code = str(country_code)
        number = number.replace('-', '').replace('(', '').replace(')', '').replace(' ', '').replace('.', '')
        if number[0] == '1':
            number = number[1:]
        return country_code + number

    def postConversations(self, conversations, line2):
        headers = {
            'vetter-token': self.token
        }
        for phone_number in conversations:
            if phone_number not in self.clientsByPhoneNumber:
                continue
            client = self.clientsByPhoneNumber[phone_number]
            client_name = client['firstname'] + ' ' + client['lastname']
            dates = list(conversations[phone_number].items())
            dates.sort()
            for date, text_chain in dates:
                text_chain.sort()
                content = ""
                last_sender = None
                for text in text_chain:
                    if last_sender != text[2]:
                        if last_sender is not None:
                            content += '\n'
                        last_sender = text[2]
                        content += '---'
                        if last_sender == phone_number:
                            content += client_name
                        else:
                            content += last_sender
                        content += '---' + str(text[1]) + '\n'
                    content += text[4] + '\n'

                body = {
                    'business_id': self.business_id,
                    'client_id': client['id'],
                    'content': content,
                    'date': text_chain[0][1].isoformat(),
                    'patient_id': "",
                    'type': 6
                }
                r = requests.post('https://www.vettersoftware.com/barramundi/communication', data=body, headers=headers)
                if r.status_code != 200:
                    raise RuntimeError('failed to post conversation, quitting')
                print("Created text communication for {} on {}".format(client_name, str(date)))
                line2.commitCommunication(phone_number, text_chain[-1][0])


