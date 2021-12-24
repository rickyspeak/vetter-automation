import sqlite3
from vetterTools import VetterTools

class Line2Tools:
    readDbFile = 'db/readMessages.db'

    def __init__(self):
        self.readDb = sqlite3.connect(self.readDbFile)

    def getNewConversations(self, file):
        line2Db = sqlite3.connect(file)
        data = line2Db.execute('''SELECT * FROM smsMessages''')
        numbers = dict()
        for row in data:
            for number in row[2:4]:
                if number not in numbers:
                    numbers[number] = list()
                numbers[number].append((row[4], row[1], row[9]))
        i = 0

def main():
    line2 = Line2Tools()
    line2.getNewConversations('db/line2Db.db')

if __name__ == '__main__':
    main()