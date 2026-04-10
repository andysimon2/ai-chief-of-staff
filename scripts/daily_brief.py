#!/usr/bin/env python3
"""
Generate and email enhanced daily brief
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load environment
load_dotenv()

SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
GMAIL_USER = os.getenv('GMAIL_USER')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

def get_sheets_service():
    """Authenticate and return Sheets service"""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )
    return build('sheets', 'v4', credentials=credentials)

def get_todays_meetings(service):
    """Get today's meetings from Meetings tab"""
    
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range='Meetings!A:K'
    ).execute()
    
    rows = result.get('values', [])
    
    if len(rows) <= 1:
        return []
    
    # Parse meetings
    meetings = []
    headers = rows[0]
    
    for row in rows[1:]:
        if len(row) >= 4:
            try:
                # Parse datetime
                meeting_datetime = datetime.fromisoformat(row[2].replace('Z', '+00:00'))
                
                # Check if today
                today = datetime.now().date()
                if meeting_datetime.date() == today:
                    meetings.append({
                        'time': meeting_datetime.strftime('%I:%M %p').lstrip('0'),
                        'title': row[1],
                        'attendees': row[3] if len(row) > 3 else '',
                        'summary': row[4] if len(row) > 4 else ''
                    })
            except:
                continue
    
    # Sort by time
    meetings.sort(key=lambda x: x['time'])
    
    return meetings

def get_high_priority_tasks(service):
    """Get high priority tasks"""
    
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range='Tasks!A:Q'
    ).execute()
    
    rows = result.get('values', [])
    
    if len(rows) <= 1:
        return []
    
    tasks = []
    for row in rows[1:]:
        if len(row) >= 8:
            status = row[6] if len(row) > 6 else ''
            priority = row[7] if len(row) > 7 else 'medium'
            
            # Only include open, high priority tasks
            if status == 'open' and priority == 'high':
                tasks.append({
                    'title': row[1],
                    'description': row[2] if len(row) > 2 else ''
                })
    
    return tasks[:3]  # Max 3 tasks

def get_critical_waiting_on(service):
    """Get waiting_on items >7 days"""
    
    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range='WaitingOn!A:M'
    ).execute()
    
    rows = result.get('values', [])
    
    if len(rows) <= 1:
        return []
    
    critical_items = []
    now = datetime.now()
    
    for row in rows[1:]:
        if len(row) >= 7:
            status = row[7] if len(row) > 7 else 'waiting'
            
            if status == 'waiting':
                try:
                    # Calculate days waiting
                    last_activity = datetime.fromisoformat(row[6].replace('Z', '+00:00'))
                    days_waiting = (now - last_activity).days
                    
                    if days_waiting >= 7:
                        critical_items.append({
                            'person': row[2],
                            'description': row[1],
                            'days': days_waiting
                        })
                except:
                    continue
    
    # Sort by days (most overdue first)
    critical_items.sort(key=lambda x: x['days'], reverse=True)
    
    return critical_items

def generate_brief(meetings, tasks, waiting_on):
    """Generate the brief text"""
    
    today = datetime.now()
    date_str = today.strftime('%A, %B %d, %Y')
    
    brief = f"""TODAY - {date_str}

📅 Meetings
"""
    
    if meetings:
        for m in meetings:
            attendees_short = m['attendees'].split(',')[0] if m['attendees'] else 'No attendees'
            brief += f"- {m['time']}: {m['title']} ({attendees_short.strip()})\n"
    else:
        brief += "- No meetings scheduled\n"
    
    brief += "\n🎯 Top Tasks (High Priority Only)\n"
    
    if tasks:
        for i, task in enumerate(tasks, 1):
            brief += f"{i}. {task['title']}\n"
    else:
        brief += "- No high priority tasks\n"
    
    brief += "\n⏳ Waiting On (Critical - >7 days)\n"
    
    if waiting_on:
        for item in waiting_on:
            brief += f"- {item['person']}: {item['description']} ({item['days']} days)\n"
    else:
        brief += "- Nothing overdue\n"
    
    brief += "\n---\n\n✅ Have a productive day!\n"
    
    return brief

def send_email(brief_text):
    """Send brief via email"""
    
    msg = MIMEMultipart()
    msg['From'] = GMAIL_USER
    msg['To'] = GMAIL_USER
    msg['Subject'] = f"Daily Brief - {datetime.now().strftime('%A, %B %d')}"
    
    msg.attach(MIMEText(brief_text, 'plain'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("✅ Email sent successfully!")
    except Exception as e:
        print(f"❌ Error sending email: {e}")

def main():
    """Main execution"""
    
    print("=" * 60)
    print("📧 GENERATING DAILY BRIEF")
    print("=" * 60)
    
    # Get Sheets service
    service = get_sheets_service()
    
    # Gather data
    print("\n📅 Fetching today's meetings...")
    meetings = get_todays_meetings(service)
    print(f"   Found {len(meetings)} meetings")
    
    print("\n🎯 Fetching high priority tasks...")
    tasks = get_high_priority_tasks(service)
    print(f"   Found {len(tasks)} high priority tasks")
    
    print("\n⏳ Fetching critical waiting_on items...")
    waiting_on = get_critical_waiting_on(service)
    print(f"   Found {len(waiting_on)} items >7 days")
    
    # Generate brief
    print("\n✍️  Generating brief...")
    brief = generate_brief(meetings, tasks, waiting_on)
    
    print("\n" + "=" * 60)
    print("PREVIEW:")
    print("=" * 60)
    print(brief)
    print("=" * 60)
    
    # Send email
    print("\n📧 Sending email...")
    send_email(brief)
    
    print("\n" + "=" * 60)
    print("✅ COMPLETE!")
    print("=" * 60)

if __name__ == "__main__":
    main()
