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
                    self.writeToken(self.token)
                    return

    def readToken(self):
        try:
            with open(TOKEN_FILE, 'r') as fp:
                self.token = fp.readline()
        except:
            print("no token file found")

    def writeToken(self, token):
        with open(TOKEN_FILE, 'w') as fp:
            fp.write(token)

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
        end = (todayDt + timedelta(days=3)).isoformat().replace('+00:00', '.000Z')

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

