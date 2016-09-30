# Prints Todoist list and Google Calendar events
from __future__ import print_function
 
import sys
import datetime
import todoist
import os
import time
from dateutil import parser
from dateutil.tz import *

from Adafruit_Thermal import *

import httplib2
from apiclient import discovery
import oauth2client
from oauth2client import client
from oauth2client import tools

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# Todoist Setup- Provide your username and password
usr = "Your User Name Here"
password = "Your Password Here"

# Parameters
# First parameters
# cal: print only calendar
# todoist: print only Todoist
param = ""
if len(sys.argv) > 1:
    param = sys.argv[1]

numDaysToShow = 7

printer = Adafruit_Thermal("/dev/ttyAMA0", 19200, timeout=5)

api = todoist.TodoistAPI()
user = api.user.login(usr, password)
response = api.sync()

date = datetime.datetime.now().replace(tzinfo=tzlocal())
date_str = date.strftime("%b %d %I:%M:%S %p")

printer.justify('C')
printer.println(date_str)
printer.justify('L')

today = []
future = []
overdue = []
calendar = []

# Calendar Setup- Gets credentials from Google. Get the JSON file by creating a Google API App.
SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Calendar Receipt Printer'

def getListFromId(id):
    for project in response['projects']:
        if (project['id'] == id):
            return project['name']

def printSection(list, header, isCalendar):
    if (len(list) > 0):
        printer.justify('C')
        printer.setSize('L')
        printer.underlineOn()
        printer.println(header)
        printer.setSize('S')
        printer.underlineOff()
        printer.justify('L')

        for item in list:
            if isCalendar:
                itemStr = "[C] " + item['content'] + "\n    " + item['date_string']
            else:
                itemStr = "[ ] " + item['content'] + " due " + item['date_string']
                itemSource = "    from " + getListFromId(item['project_id'])
            if(item['priority'] > 2):
                printer.underlineOn()
                printer.println(itemStr)
                printer.underlineOff()
                if not isCalendar:
                    printer.println(itemSource)
            else:
                printer.println(itemStr)
                if not isCalendar:
                    printer.println(itemSource)

        printer.feed(1)

def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'calendar-python-quickstart.json')

    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

# Todoist Part
for item in response['items']:
    if (item['due_date_utc'] is not None):
        dat = parser.parse(item['due_date_utc'], dayfirst=True, fuzzy=True)
        dat = dat.replace(tzinfo=tzutc())
        dat = dat.astimezone(tzlocal())

        delta = dat - datetime.datetime.now().replace(tzinfo=tzlocal())        

        if (delta.days in range(0,2)):
            today.append(item)

        if (delta.days in range(2, numDaysToShow) and item['priority'] > 1):
            future.append(item)

        if (delta.days < 0):
            overdue.append(item)

# Google Calendar Part
credentials = get_credentials()
http = credentials.authorize(httplib2.Http())
service = discovery.build('calendar', 'v3', http=http)

now = datetime.datetime.utcnow()
start = now.isoformat() + 'Z' # 'Z' indicates UTC time
if datetime.datetime.today().weekday() == 0:
    end = now + datetime.timedelta(days=numDaysToShow)
else:
    end = now + datetime.timedelta(days=2)
finish = end.isoformat() + 'Z'
eventsResult = service.events().list(
    calendarId='primary', timeMin=start, timeMax=finish, singleEvents=True,
    orderBy='startTime').execute()
events = eventsResult.get('items', [])

for event in events:
    begin = event['start'].get('dateTime', event['start'].get('date'))
    finish = event['end'].get('dateTime', event['end'].get('date'))

    start = parser.parse(begin, dayfirst=True, fuzzy=True)
    end = parser.parse(finish, dayfirst=True, fuzzy=True)

    event['priority'] = 0

    start_date = start.date().strftime('%m/%d/%Y').lstrip("0").replace(" 0", " ")
    end_date = end.date().strftime('%m/%d/%Y').lstrip("0").replace(" 0", " ")
    start_time = start.time().strftime('%I:%M %p').lstrip("0").replace(" 0", " ")
    end_time = end.time().strftime('%I:%M %p').lstrip("0").replace(" 0", " ")

    if start_date == datetime.datetime.now().date():
        event['priority'] = 3

    date_string = str(start_date)
    if "T" in begin:
        date_string += " " + str(start_time)
    date_string += " to "
    if not start_date == end_date:
        date_string += str(end_date) + " "
        
    if "T" in finish:
        date_string += str(end_time)
    event['date_string'] = date_string
    event['content'] = event['summary']
    print (event['summary'])
    calendar.append(event)

if param == "cal":
    printSection(calendar, "CALENDAR", True)
if param == "todoist":
    printSection(today, "DAILY SPECIAL", False)
    printSection(future, "UP NEXT", False)
    printSection(overdue, "OVERDUE", False)
else:
    printSection(today, "DAILY SPECIAL", False)
    printSection(future, "UP NEXT", False)
    printSection(overdue, "OVERDUE", False)
    printSection(calendar, "CALENDAR", True)

printer.feed(2)
