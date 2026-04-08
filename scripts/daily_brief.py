#!/usr/bin/env python3
"""
Daily Brief Generator with Email Delivery
Reads tasks from Google Sheets and emails daily brief
"""

import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Load environment variables
load_dotenv()

# Configuration
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
GMAIL_ADDRESS = os.getenv('GMAIL_ADDRESS')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

def get_sheets_service():
    """Authenticate and return Sheets service"""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )
    return build('sheets', 'v4', credentials=credentials)

def read_tasks(sheets_service):
    """Read all tasks from the Tasks sheet"""
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='Tasks!A2:Q'
        ).execute()
        
        rows = result.get('values', [])
        
        tasks = []
        for row in rows:
            row = row + [''] * (17 - len(row))
            
            task = {
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'primary_owner': row[3],
                'collaborators': row[4],
                'collaboration_type': row[5],
                'status': row[6],
                'priority': row[7],
                'due_date': row[8],
                'source': row[9],
                'source_confidence': row[10],
                'linked_person': row[11],
                'linked_meeting': row[12],
                'created_at': row[13],
                'updated_at': row[14],
                'duplicate_flag': row[15],
                'potential_duplicates': row[16]
            }
            tasks.append(task)
        
        return tasks
    
    except Exception as e:
        print(f"❌ Error reading tasks: {e}")
        return []

def generate_brief(tasks):
    """Generate the daily brief from tasks"""
    
    now = datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")
    
    open_tasks = [t for t in tasks if t['status'] == 'open']
    high_priority = [t for t in open_tasks if t['priority'] == 'high']
    medium_priority = [t for t in open_tasks if t['priority'] == 'medium']
    
    brief = []
    brief.append("=" * 60)
    brief.append(f"📅 DAILY BRIEF - {date_str}")
    brief.append("=" * 60)
    brief.append("")
    
    brief.append("🎯 TOP TASKS")
    brief.append("")
    
    if high_priority:
        brief.append("High Priority:")
        for i, task in enumerate(high_priority, 1):
            person = f" (from {task['linked_person']})" if task['linked_person'] else ""
            brief.append(f"  {i}. {task['title']}{person}")
        brief.append("")
    
    if medium_priority:
        brief.append("Medium Priority:")
        for i, task in enumerate(medium_priority[:3], 1):
            person = f" (from {task['linked_person']})" if task['linked_person'] else ""
            brief.append(f"  {i}. {task['title']}{person}")
        brief.append("")
    
    if not high_priority and not medium_priority:
        brief.append("  ✅ No open tasks! You're all caught up.")
        brief.append("")
    
    brief.append("📊 SUMMARY")
    brief.append("")
    brief.append(f"  • Total open tasks: {len(open_tasks)}")
    brief.append(f"  • High priority: {len(high_priority)}")
    brief.append(f"  • Medium priority: {len(medium_priority)}")
    brief.append("")
    
    people = {}
    for task in open_tasks:
        person = task['linked_person'] or 'Unknown'
        if person not in people:
            people[person] = []
        people[person].append(task['title'])
    
    if len(people) > 1:
        brief.append("👥 TASKS BY PERSON")
        brief.append("")
        for person, task_list in sorted(people.items()):
            if person != 'Unknown':
                brief.append(f"  • {person}: {len(task_list)} task(s)")
        brief.append("")
    
    brief.append("=" * 60)
    brief.append("💡 View full sheet:")
    brief.append(f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")
    brief.append("=" * 60)
    
    return "\n".join(brief)

def send_email(brief_text):
    """Send the daily brief via email"""
    
    if not GMAIL_APP_PASSWORD:
        print("⚠️  No Gmail app password configured - skipping email")
        return False
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Daily Brief - {datetime.now().strftime('%A, %B %d, %Y')}"
        msg['From'] = GMAIL_ADDRESS
        msg['To'] = GMAIL_ADDRESS
        
        # Plain text version
        text_part = MIMEText(brief_text, 'plain')
        msg.attach(text_part)
        
        # Send via Gmail SMTP
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        
        print(f"✅ Email sent to {GMAIL_ADDRESS}")
        return True
    
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False

def main():
    """Main execution"""
    
    if not all([SPREADSHEET_ID, SERVICE_ACCOUNT_FILE]):
        print("❌ Missing required environment variables")
        sys.exit(1)
    
    try:
        sheets = get_sheets_service()
        
        print("📖 Reading tasks from Google Sheets...")
        tasks = read_tasks(sheets)
        
        if not tasks:
            print("⚠️  No tasks found in sheet")
            brief_text = f"\n📧 DAILY BRIEF - {datetime.now().strftime('%A, %B %d, %Y')}\n\n✅ No tasks to show\n"
            print(brief_text)
            if GMAIL_APP_PASSWORD:
                send_email(brief_text)
            return
        
        print(f"✅ Found {len(tasks)} total tasks\n")
        
        brief_text = generate_brief(tasks)
        print(brief_text)
        
        # Send email if configured
        if GMAIL_APP_PASSWORD:
            print("\n📧 Sending email...")
            send_email(brief_text)
        else:
            print("\n⚠️  Email not configured (missing GMAIL_APP_PASSWORD)")
    
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
