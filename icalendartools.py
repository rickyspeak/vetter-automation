import datetime
import json
import os.path
import urllib.parse

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']
BASE_ADDRESS = 'https://www.google.com/maps/dir/?api=1'

class IcalendarTools:
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
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('secrets/token.json', 'w') as token:
                token.write(creds.to_json())
        self.creds = creds

    def postAppointments(self, appointments):
        creds = self.creds
        service = build('calendar', 'v3', credentials=creds)

        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
        later = (datetime.datetime.utcnow() + datetime.timedelta(days=3)).isoformat() + 'Z'
        print('Getting the upcoming 10 events')
        events_result = service.events().list(calendarId='primary', timeMin=now, timeMax=later,
                                              singleEvents=True, orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            print('No upcoming events found.')
        for event in events:
            service.events().delete(calendarId='primary', eventId=event['id']).execute()

        for appointment in appointments:
            if 'patient' not in appointment:
                appointment['patient'] = 'unknown'
            if 'address' in appointment:
                appointment['addressLink'] = BASE_ADDRESS + '&destination=' + \
                                             urllib.parse.quote_plus(appointment['address'])
            else:
                appointment['addressLink'] = 'None'

            event = {
                'summary': appointment['client'],
                'location': appointment['address'],
                'description': 'addressLink: ' + appointment['addressLink'] + '\n' +
                               'patient: ' + appointment['patient'] + '\n' +
                               'type: ' + appointment['type'] + '\n' +
                               'complaint: ' + appointment['complaint'] + '\n' +
                               'notes: ' + appointment['notes'] + '\n',
                'start': {
                    'dateTime': appointment['start'],
                    'timeZone': 'America/Los_Angeles',
                },
                'end': {
                    'dateTime': appointment['end'],
                    'timeZone': 'America/Los_Angeles',
                },
            }
            service.events().insert(calendarId='primary', body=event).execute()
