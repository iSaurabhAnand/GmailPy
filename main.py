import os
import base64
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from flask import Flask, render_template_string, request, jsonify
import base64
from email.mime.text import MIMEText

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]
app = Flask(__name__)

def send_followup_email(service, to, subject, thread_id):
    # Get user's name from Gmail profile
    profile = service.users().getProfile(userId='me').execute()
    email = profile['emailAddress']
    # Extract first name and last name from email (you might want to customize this)
    name_parts = email.split('@')[0].split('.')
    first_name = name_parts[0].title()
    last_name = name_parts[1].title() if len(name_parts) > 1 else ""

    # Create follow-up message
    reply_subject = f"Re: {subject}" if not subject.startswith('Re:') else subject
    message_text = f"""Hi,

Just following up on this.

Thanks,
{first_name} {last_name}"""

    message = MIMEText(message_text)
    message['to'] = to
    message['subject'] = reply_subject
    message['In-Reply-To'] = thread_id
    message['References'] = thread_id

    # Encode the message
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    
    try:
        service.users().messages().send(
            userId='me',
            body={'raw': raw_message, 'threadId': thread_id}
        ).execute()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

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
                'id': msg['id'],
                'thread_id': thread_id,
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
            .actions { margin-top: 10px; }
            .follow-up-btn {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }
            .follow-up-btn:hover {
                background-color: #45a049;
            }
            .success { color: green; display: none; margin-left: 10px; }
            .error { color: red; display: none; margin-left: 10px; }
        </style>
        <script>
        function sendFollowUp(button, emailId, threadId, to, subject) {
            button.disabled = true;
            const successSpan = button.nextElementSibling;
            const errorSpan = successSpan.nextElementSibling;
            
            fetch('/send-followup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email_id: emailId,
                    thread_id: threadId,
                    to: to,
                    subject: subject
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    successSpan.style.display = 'inline';
                    button.style.display = 'none';
                } else {
                    errorSpan.style.display = 'inline';
                    button.disabled = false;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                errorSpan.style.display = 'inline';
                button.disabled = false;
            });
        }
        </script>
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
            <div class="actions">
                <button class="follow-up-btn" onclick="sendFollowUp(this, '{{ email.id }}', '{{ email.thread_id }}', '{{ email.to }}', '{{ email.subject }}')">Follow Up</button>
                <span class="success">✓ Sent!</span>
                <span class="error">Failed to send</span>
            </div>
        </div>
        {% endfor %}
    </body>
    </html>
    """
    
    return render_template_string(template, emails=unreplied_emails)

@app.route('/send-followup', methods=['POST'])
def send_followup():
    data = request.json
    service = get_gmail_service()
    success = send_followup_email(
        service,
        data['to'],
        data['subject'],
        data['thread_id']
    )
    return jsonify({'success': success})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
