from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
import time
from datetime import datetime
import json


class VetterTools:
    def __init__(self):
        self.creds = None

    def getCreds(self):
        with open('secrets/vetter_creds.json') as fp:
            self.creds = json.load(fp)

    def getAppointments(self, days):
        if self.creds is None:
            raise RuntimeError('creds not available')
        creds = self.creds

        options = Options()
        options.headless = True
        with webdriver.Chrome(options=options) as driver:
            wait = WebDriverWait(driver, 15)
            driver.get("https://www.vettersoftware.com/apps/index.php/october/login")
            name = driver.find_element(By.NAME, 'fm_login_email')
            password = driver.find_element(By.NAME, 'fm_login_password')

            name.send_keys(creds['user'])
            password.send_keys(creds['password'])

            login = driver.find_element(By.ID, 'btn-login')
            login.click()
            appointments = []

            for i in range(days):
                try:
                    wait.until(lambda d: d.find_elements(By.CLASS_NAME, 'fc-time-grid-event'))
                    time.sleep(1)
                except TimeoutException:
                    print("time out waiting for page to load, continuing")

                dateHeader = driver.find_element(By.CSS_SELECTOR, '.d-sm-inline span')
                date = dateHeader.text

                events = driver.find_elements(By.CLASS_NAME, 'fc-time-grid-event')

                for event in events:
                    event.click()
                    wait.until(lambda d: d.find_element(By.ID, 'previewModal___BV_modal_title_'))
                    time.sleep(1)
                    appointmentTime = driver.find_element(By.ID, 'previewModal___BV_modal_title_').text
                    (start, end) = appointmentTime.split(' - ')
                    startDt = datetime.strptime(date + ' ' + start, '%A, %B %d, %Y %I:%M %p')
                    endDt = datetime.strptime(date + ' ' + end, '%A, %B %d, %Y %I:%M %p')

                    appointment = {
                        'start': startDt.isoformat(),
                        'end': endDt.isoformat()
                    }

                    dataRows = driver.find_element(By.CLASS_NAME, 'modal-body').find_elements(By.CLASS_NAME, 'row')
                    for row in dataRows:
                        label = row.find_element(By.TAG_NAME, 'label').text
                        if label == 'Address:':
                            aHref = row.find_element(By.TAG_NAME, 'a')
                            appointment['address'] = aHref.text
                        elif label == 'Client:':
                            appointment['client'] = row.find_element(By.TAG_NAME, 'a').text
                        elif label == 'Patient:':
                            appointment['patient'] = row.find_element(By.TAG_NAME, 'a').text
                        elif label == 'Type:':
                            appointment['type'] = row.find_element(By.TAG_NAME, 'div').text
                        elif label == 'Complaint:':
                            appointment['complaint'] = row.find_element(By.TAG_NAME, 'div').text
                        elif label == 'Notes:':
                            appointment['notes'] = row.find_element(By.TAG_NAME, 'div').text

                    appointments.append(appointment)

                    closeButton = driver.find_element(By.CLASS_NAME, "close")
                    closeButton.click()
                    time.sleep(1)
                if i < days:
                    time.sleep(1)
                    nextButton = driver.find_element(By.CLASS_NAME, 'fc-icon-chevron-right')
                    nextButton.click()

        return appointments

