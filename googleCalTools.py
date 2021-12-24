import datetime
import zoneinfo
import os.path
import urllib.parse

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# If modifying these scopes, delete the file token.json.
LOCAL_TZ_STRING = 'America/Los_Angeles'
LOCAL_TZ = zoneinfo.ZoneInfo(LOCAL_TZ_STRING)
SCOPES = ['https://www.googleapis.com/auth/calendar']
BASE_ADDRESS = 'https://www.google.com/maps/dir/?api=1'

class GoogleCalTools:
    def __init__(self):
        self.creds = None

    def getCreds(self):
        creds = self.creds
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('secrets/token.json'):
            creds = Credentials.from_authorized_user_file('secrets/token.json', SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except:
                    creds # do nothing

            if not creds or not creds.valid:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'secrets/credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('secrets/token.json', 'w') as token:
                token.write(creds.to_json())
        self.creds = creds

    def postAppointments(self, appointments):
        creds = self.creds
        service = build('calendar', 'v3', credentials=creds)

        # Call the Calendar API
        today = datetime.datetime.today()
        todayDt = datetime.datetime(today.year, today.month, today.day, tzinfo=LOCAL_TZ)
        now = todayDt.isoformat()
        later = (todayDt + datetime.timedelta(days=3)).isoformat()
        print('Getting the upcoming events')
        events_result = service.events().list(calendarId='primary', timeMin=now, timeMax=later,
                                              singleEvents=True, orderBy='startTime').execute()
        events = events_result.get('items', [])

        print('Deleting {} events found'.format(len(events)))
        for event in events:
            service.events().delete(calendarId='primary', eventId=event['id']).execute()

        print("Posting {} appointments found".format(len(appointments)))
        for appointment in appointments:
            missing_address = "MISSING ADDRESS: "
            if 'patient' not in appointment:
                appointment['patient'] = 'unknown'
            if 'address' in appointment and len(appointment['address']) > 10:
                appointment['addressLink'] = BASE_ADDRESS + '&destination=' + \
                                             urllib.parse.quote_plus(appointment['address'])
                missing_address = ''
            else:
                appointment['addressLink'] = 'None'

            event = {
                'summary': missing_address + appointment['client'],
                'location': appointment['address'],
                'description': 'addressLink: ' + appointment['addressLink'] + '\n' +
                               'patient: ' + appointment['patient'] + '\n' +
                               'complaint: ' + appointment['complaint'] + '\n' +
                               'notes: ' + appointment['notes'] + '\n',
                'start': {
                    'dateTime': appointment['start'],
                    'timeZone': LOCAL_TZ_STRING,
                },
                'end': {
                    'dateTime': appointment['end'],
                    'timeZone': LOCAL_TZ_STRING,
                },
            }
            service.events().insert(calendarId='primary', body=event).execute()
            print("Created event for {} at {}".format(appointment['client'], appointment['start']))
