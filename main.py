import os
import base64
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

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
def read_sent_emails(service):
    results = service.users().messages().list(userId='me', labelIds=['SENT'], maxResults=10).execute()
    messages = results.get('messages', [])
    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
        snippet = msg_data.get('snippet', '')
        print(f"Snippet: {snippet}")

if __name__ == '__main__':
    service = get_gmail_service()
    read_sent_emails(service)
