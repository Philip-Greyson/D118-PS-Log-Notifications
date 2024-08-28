"""Script to send notifications when a log entry has been entered in the last day for students with case managers.

https://github.com/Philip-Greyson/D118-PS-Log-Notifications

Needs the google-api-python-client, google-auth-httplib2 and the google-auth-oauthlib:
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
also needs oracledb: pip install oracledb --upgrade
"""

import base64
import os
from datetime import datetime, timedelta

import oracledb  # needed for connection to PowerSchool server (ordcle database)
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.message import EmailMessage

# setup db connection
DB_UN = os.environ.get('POWERSCHOOL_READ_USER')  # username for read-only database user
DB_PW = os.environ.get('POWERSCHOOL_DB_PASSWORD')  # the password for the database account
DB_CS = os.environ.get('POWERSCHOOL_PROD_DB')  # the IP address, port, and database name to connect to
print(f'DBUG: Database Username: {DB_UN} |Password: {DB_PW} |Server: {DB_CS}')  # debug so we can see where oracle is trying to connect to/with

# Google API Scopes that will be used. If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.compose']

LOG_TYPES = {-100000: 'Discipline', 12715: 'Teacher Intervention', 14866: 'Parent Contact'}  # define the mappings for the log types

if __name__ == '__main__':
    with open('log_notifications_log.txt', 'w') as log:
        startTime = datetime.now()
        startTime = startTime.strftime('%H:%M:%S')
        print(f'INFO: Execution started at {startTime}')
        print(f'INFO: Execution started at {startTime}', file=log)
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        
        service = build('gmail', 'v1', credentials=creds)  # create the Google API service with just gmail functionality

        # create the connecton to the PowerSchool database
        with oracledb.connect(user=DB_UN, password=DB_PW, dsn=DB_CS) as con:
            with con.cursor() as cur:  # start an entry cursor
                today = datetime.now()
                yesterday = today - timedelta(days = 1)
                cur.execute('SELECT stu.student_number, stu.id, stu.first_name, stu.last_name, ext.casemanager, ext.case_manager_email FROM STUDENTS stu LEFT JOIN u_def_ext_students0 ext ON stu.dcid = ext.studentsdcid WHERE ext.casemanager IS NOT NULL AND stu.enroll_status = 0')
                students = cur.fetchall()
                for student in students:  # go through each student one at a time
                    try:
                        # print(student)  # debug
                        stuNum = int(student[0])
                        stuID = int(student[1])
                        firstName = str(student[2])
                        lastName = str(student[3])
                        caseManager = str(student[4])
                        caseManagerEmail = str(student[5]) if student[5] else None

                        cur.execute('SELECT entry_author, entry, logtypeid, discipline_incidentdate, dcid FROM LOG WHERE studentid = :student AND entry_date > :timeframe', student=stuID, timeframe=yesterday)
                        entries = cur.fetchall()
                        for entry in entries:
                            try:
                                reporter = str(entry[0])
                                details = str(entry[1])
                                logType = LOG_TYPES.get(int(entry[2]), None)
                                incidentDate = entry[3].strftime("%m/%d/%Y") if (today - entry[3] < timedelta(days=365)) else 'Date Unspecified'  # check to see if the incident date is more than a year ago, likely 1/1/1990 and if it is just say unspecified
                                logDCID = int(entry[4])
                                print(f'DBUG: Student {stuNum} had entry {logDCID} entered in the last 24 hours by {reporter}, type "{logType}" that occured on {incidentDate}. Details: {details}')
                                print(f'DBUG: Student {stuNum} had entry {logDCID} entered in the last 24 hours by {reporter}, type "{logType}" that occured on {incidentDate}. Details: {details}', file=log)
                                if caseManagerEmail:
                                    print(f'INFO: Sending email to {caseManagerEmail} with details of entry {logDCID}')
                                    print(f'INFO: Sending email to {caseManagerEmail} with details of entry {logDCID}', file=log)
                                    try:
                                        mime_message = EmailMessage()  # create an email message object
                                        # define headers
                                        mime_message['To'] = caseManagerEmail # who the email gets sent to
                                        mime_message['Subject'] = f'Log Entry Added for {stuNum} - {firstName} {lastName} with the type of "{logType}"'  # subject line of the email
                                        mime_message.set_content(f'This email is to inform you that a log entry has been added for {firstName} {lastName} by {reporter} for an incident occuring on {incidentDate}.\nThe details of the entry are: {details}\n\nPlease check PowerSchool for more information and follow up with the teacher if needed.')  # body of the email
                                        # encoded message
                                        encoded_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()
                                        create_message = {'raw': encoded_message}
                                        send_message = (service.users().messages().send(userId="me", body=create_message).execute())
                                        print(f'DBUG: Email sent, message ID: {send_message["id"]}') # print out resulting message Id
                                        print(f'DBUG: Email sent, message ID: {send_message["id"]}', file=log)
                                    except HttpError as er:   # catch Google API http errors, get the specific message and reason from them for better logging
                                        status = er.status_code
                                        details = er.error_details[0]  # error_details returns a list with a dict inside of it, just strip it to the first dict
                                        print(f'ERROR {status} from Google API while sending email to {caseManagerEmail}: {details["message"]}. Reason: {details["reason"]}')
                                        print(f'ERROR {status} from Google API while sending email to {caseManagerEmail}: {details["message"]}. Reason: {details["reason"]}', file=log)
                                    except Exception as er:
                                        print(f'ERROR while trying to send email to {caseManagerEmail} for log entry DCID {logDCID}: {er}')
                                        print(f'ERROR while trying to send email to {caseManagerEmail} for log entry DCID {logDCID}: {er}', file=log)
                                else:
                                    print(f'ERROR: Student {stuNum} does not have a case manager email specified, cannot sent email for entry {logDCID}')
                                    print(f'ERROR: Student {stuNum} does not have a case manager email specified, cannot sent email for entry {logDCID}', file=log)
                            except Exception as er:
                                print(f'ERROR while processing log entry DCID {entry[4]}: {er}')
                                print(f'ERROR while processing log entry DCID {entry[4]}: {er}', file=log)
                    except Exception as er:
                        print(f'ERROR while doing initial processing of student {student[0]}: {er}')
                        print(f'ERROR while doing initial processing of student {student[0]}: {er}', file=log)
        endTime = datetime.now()
        endTime = endTime.strftime('%H:%M:%S')
        print(f'INFO: Execution ended at {endTime}')
        print(f'INFO: Execution ended at {endTime}', file=log)
