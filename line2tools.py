import json
import sqlite3
import os
from datetime import datetime
import zoneinfo

from vetterTools import VetterTools

LOCAL_TZ_STRING = 'America/Los_Angeles'
LOCAL_TZ = zoneinfo.ZoneInfo(LOCAL_TZ_STRING)


class Line2Tools:
    readDbFile = 'db/readMessages.db'

    def __init__(self):
        self.readDb = sqlite3.connect(self.readDbFile)
        # series of migrations for db. should us a migration tool eventually
        self.initDbV1()
        self.excludeNumbers = list()
        with open('secrets/line2_exclude_numbers.json', 'r') as fp:
            self.excludeNumbers = json.load(fp)

    def initDbV1(self):
        r = self.readDb.execute('''SELECT count(*) FROM sqlite_master WHERE type='table' AND name='read_messages';''')
        if r.fetchone()[0] == 0:
            self.readDb.execute('''create table read_messages (phone_number TEXT, time INTEGER);''')

    def getNewConversations(self, file):
        data = self.readDb.execute('''SELECT * from read_messages;''')
        read_messages = dict()
        for row in data:
            read_messages[row[0]] = row[1]

        line2Db = sqlite3.connect(file)
        data = line2Db.execute('''SELECT * FROM smsMessages''')
        new_conversations = dict()
        for row in data:
            for phone_numbers in row[2:4]:
                for phone_number in phone_numbers.split(','):
                    # check if number is in the exclude list
                    if phone_number in self.excludeNumbers:
                        continue
                    # check if message has already been read
                    if phone_number in read_messages and read_messages[phone_number] >= int(row[4]):
                        continue
                    if phone_number not in new_conversations:
                        new_conversations[phone_number] = dict()
                    timestamp = datetime.fromtimestamp(int(row[4]), LOCAL_TZ)
                    date = timestamp.date()
                    if date not in new_conversations[phone_number]:
                        new_conversations[phone_number][date] = list()
                    new_conversations[phone_number][date].append((row[4], timestamp, row[2], row[3], row[1], row[0], row[9]))
        print("loaded conversations")
        return new_conversations

    def commitCommunication(self, phone_number, timestamp):
        self.readDb.execute('insert into read_messages(phone_number,time) values (?,?)', (phone_number, int(timestamp)))
        self.readDb.commit()


def main():
    line2 = Line2Tools()
    conversations = line2.getNewConversations(os.path.expanduser('~/Library/Application Support/Line2/line2Db.db'))

    vetterTools = VetterTools()
    vetterTools.login()
    vetterTools.loadClients()
    vetterTools.postConversations(conversations, line2)


if __name__ == '__main__':
    main()
