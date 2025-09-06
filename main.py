import os
import base64
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from flask import Flask, render_template_string

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
app = Flask(__name__)

# Authenticate and build Gmail service
def get_gmail_service():
    creds = None
    cred_path = os.getenv('GMAIL_CREDENTIALS_PATH') or os.environ.get('gi') or 'credentials.json'
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(cred_path, SCOPES)
            creds = flow.run_local_server(port=8088)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    service = build('gmail', 'v1', credentials=creds)
    return service

# Read sent emails

import datetime

# Read sent emails with no replies in last 30 days
def get_unreplied_sent_emails(service):
    thirty_days_ago = int((datetime.datetime.utcnow() - datetime.timedelta(days=30)).timestamp())
    query = f'label:SENT after:{thirty_days_ago}'
    results = service.users().messages().list(userId='me', q=query, maxResults=20).execute()
    unreplied_emails = []
    
    messages = results.get('messages', [])
    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
        thread_id = msg_data.get('threadId')
        sent_msg_internal_date = int(msg_data.get('internalDate', '0')) // 1000
        thread = service.users().messages().list(userId='me', q=f'threadId:{thread_id}').execute()
        thread_msgs = thread.get('messages', [])
        
        # Get email details
        headers = msg_data.get('payload', {}).get('headers', [])
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
        to = next((h['value'] for h in headers if h['name'].lower() == 'to'), 'Unknown')
        date = datetime.datetime.fromtimestamp(sent_msg_internal_date).strftime('%Y-%m-%d %H:%M:%S')
        
        # Check for replies after sent message
        has_reply = False
        for tmsg in thread_msgs:
            if tmsg['id'] != msg['id'] and int(tmsg.get('internalDate', '0')) // 1000 > sent_msg_internal_date:
                # If the sender is not me, it's a reply
                headers = tmsg.get('payload', {}).get('headers', [])
                from_header = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
                if 'me' not in from_header:
                    has_reply = True
                    break
                    
        if not has_reply:
            snippet = msg_data.get('snippet', '')
            unreplied_emails.append({
                'subject': subject,
                'to': to,
                'date': date,
                'snippet': snippet
            })
            
    return unreplied_emails

@app.route('/')
def index():
    service = get_gmail_service()
    unreplied_emails = get_unreplied_sent_emails(service)
    
    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Unreplied Emails</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .email { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }
            .subject { font-weight: bold; color: #333; }
            .meta { color: #666; font-size: 0.9em; margin: 5px 0; }
            .snippet { color: #444; margin-top: 10px; }
        </style>
    </head>
    <body>
        <h1>Unreplied Sent Emails (Last 30 Days)</h1>
        {% for email in emails %}
        <div class="email">
            <div class="subject">{{ email.subject }}</div>
            <div class="meta">
                To: {{ email.to }}<br>
                Date: {{ email.date }}
            </div>
            <div class="snippet">{{ email.snippet }}</div>
        </div>
        {% endfor %}
    </body>
    </html>
    """
    
    return render_template_string(template, emails=unreplied_emails)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
