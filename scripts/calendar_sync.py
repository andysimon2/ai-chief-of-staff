#!/usr/bin/env python3
"""
Sync Google Calendar meetings to Google Sheets
"""

import os
import pickle
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.discovery import build as sheets_build

# Load environment
load_dotenv()

CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
SHEETS_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')

def authenticate_calendar():
    """Authenticate with Calendar API"""
    creds = None
    token_path = 'credentials/calendar_token.pickle'
    
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials/gmail_credentials.json', CALENDAR_SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    
    return build('calendar', 'v3', credentials=creds)

def get_sheets_service():
    """Authenticate and return Sheets service"""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SHEETS_SCOPES
    )
    return sheets_build('sheets', 'v4', credentials=credentials)

def extract_name_from_email(email):
    """Extract name from email address"""
    username = email.split('@')[0]
    return username.replace('.', ' ').title()

def get_todays_meetings(calendar_service):
    """Fetch today's meetings"""
    
    # Get today's date range
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    
    print(f"📅 Fetching meetings for {today.strftime('%A, %B %d, %Y')}...")
    
    events_result = calendar_service.events().list(
        calendarId='primary',
        timeMin=today.isoformat() + 'Z',
        timeMax=tomorrow.isoformat() + 'Z',
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    events = events_result.get('items', [])
    print(f"✅ Found {len(events)} meetings today")
    
    meetings = []
    for event in events:
        # Extract attendees with BOTH names and emails
        attendee_names = []
        attendee_emails = []
        
        if 'attendees' in event:
            for attendee in event['attendees']:
                email = attendee.get('email', '')
                # Try to get display name, otherwise extract from email
                name = attendee.get('displayName', extract_name_from_email(email))
                attendee_names.append(name)
                attendee_emails.append(email)
        
        # Extract time
        start = event['start'].get('dateTime', event['start'].get('date'))
        
        meetings.append({
            'id': event['id'],
            'title': event.get('summary', 'No title'),
            'datetime': start,
            'attendees': ', '.join(attendee_names),  # Names for display
            'attendee_emails': ', '.join(attendee_emails),  # Emails for cross-reference
            'source': 'calendar'
        })
    
    return meetings

def write_meetings_to_sheets(sheets_service, meetings):
    """Write meetings to Google Sheets"""
    
    if not meetings:
        print("\n✅ No meetings today")
        return
    
    print(f"\n📝 Writing {len(meetings)} meetings to Google Sheets...")
    
    timestamp = datetime.now().isoformat()
    
    meeting_rows = []
    for meeting in meetings:
        meeting_rows.append([
            meeting['id'],                  # A: id
            meeting['title'],                # B: title
            meeting['datetime'],             # C: datetime
            meeting['attendees'],            # D: attendees (NAMES)
            '',                              # E: summary
            '',                              # F: key_points
            '',                              # G: action_items
            meeting['attendees'],            # H: linked_people (names)
            meeting['source'],               # I: source
            '',                              # J: days_since_last_meeting
            meeting['attendee_emails']       # K: attendee_emails (EMAILS)
        ])
    
    sheets_service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range='Meetings!A:K',  # Extended to column K
        valueInputOption='RAW',
        body={'values': meeting_rows}
    ).execute()
    
    print(f"✅ Wrote {len(meeting_rows)} meetings with names AND emails")

def main():
    """Main execution"""
    
    print("=" * 60)
    print("📅 CALENDAR SYNC")
    print("=" * 60)
    
    # Authenticate
    calendar_service = authenticate_calendar()
    sheets_service = get_sheets_service()
    
    # Fetch meetings
    meetings = get_todays_meetings(calendar_service)
    
    # Write to sheets
    write_meetings_to_sheets(sheets_service, meetings)
    
    print("\n" + "=" * 60)
    print("✅ COMPLETE!")
    print("=" * 60)

if __name__ == "__main__":
    main()
