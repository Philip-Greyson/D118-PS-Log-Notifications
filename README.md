# # D118-PS-Log-Notifications

This is an pretty specific script D118 uses to send an email to case managers after a log entry is added for a student.

## Overview

The purpose of this script is to send an email to a student's case manager when that student has a log entry added for them via the eDiscipline plugin. This is done by finding students who have a case manager defined in a custom field, then retrieving the case manager email from another custom field, and searching for logs matching the current student in the last day. An email is constructed and sent for each log entry (if the case manager email exists) which contains the details and date of the incident.

## Requirements

The following Environment Variables must be set on the machine running the script:

- POWERSCHOOL_READ_USER
- POWERSCHOOL_DB_PASSWORD
- POWERSCHOOL_PROD_DB
- POWERSCHOOL_API_ID
- POWERSCHOOL_API_SECRET

These are fairly self explanatory, and just relate to the usernames, passwords, and host IP/URLs for PowerSchool, as well as the API ID and secret you can get from creating a plugin in PowerSchool. If you wish to directly edit the script and include these credentials or to use other environment variable names, you can.

Additionally, the following Python libraries must be installed on the host machine (links to the installation guide):

- [Python-oracledb](https://python-oracledb.readthedocs.io/en/latest/user_guide/installation.html)
- [Python-Google-API](https://github.com/googleapis/google-api-python-client#installation)

In addition, an OAuth credentials.json file must be in the same directory as the overall script. This is the credentials file you can download from the Google Cloud Developer Console under APIs & Services > Credentials > OAuth 2.0 Client IDs. Download the file and rename it to credentials.json. When the program runs for the first time, it will open a web browser and prompt you to sign into a Google account that has the permissions to send emails (this will be the account that the emails come from). Based on this login it will generate a token.json file that is used for authorization. When the token expires it should auto-renew unless you end the authorization on the account or delete the credentials from the Google Cloud Developer Console. One credentials.json file can be shared across multiple similar scripts if desired.
There are full tutorials on getting these credentials from scratch available online. But as a quickstart, you will need to create a new project in the Google Cloud Developer Console, and follow [these](https://developers.google.com/workspace/guides/create-credentials#desktop-app) instructions to get the OAuth credentials, and then enable APIs in the project (the Gmail API is used in this project).

## Customization

This script is pretty specific to our district's use case, so it is going to be a bit of work to customize for your needs.

- To begin with, you will need to change the student SQL query to match the custom tables/fields that contains the case manager and email.
- You will want to change the `LOG_TYPES` dict to contain your mappings of log type ID to the string type. For us, these values were set up by the eDiscipline plugin and I just used the values available for teachers when they submit a log entry.
- If you are running the script at any point besides in the morning, you will want to change the `today` and `timeframe` definitions. I strip off the time code of the current timedate object and then subtract a day, which results in midnight and 0 seconds of the morning before the script runs. The log entries have a entry_date that also just has a date but no time, so this retrieves all log entries from the previous day and current day. We run it at the morning so case managers get a summary of the previous day, if you are instead running it in the evening you would probably want to remove the day subtraction so you only get the logs of the current day.
