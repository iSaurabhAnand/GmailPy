import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]

def get_gmail_service():
    """Initialize and return Gmail service with proper authentication."""
    creds = None
    cred_path = os.getenv('GMAIL_CREDENTIALS_PATH') or os.environ.get('GMAIL_CREDENTIALS_PATH') or 'credentials.json'
    
    try:
        if os.path.exists('token.json'):
            try:
                creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            except Exception as e:
                print(f"Error loading token.json: {e}")
                # If there's any error with the token file, remove it
                os.remove('token.json')
                creds = None
    except Exception as e:
        print(f"Error accessing token.json: {e}")
        creds = None
    
    try:
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing token: {e}")
                    creds = None
            
            if not creds:
                flow = InstalledAppFlow.from_client_secrets_file(
                    cred_path, 
                    SCOPES,
                    redirect_uri='http://localhost:8088'
                )
                creds = flow.run_local_server(
                    port=8088,
                    access_type='offline',  # This ensures we get a refresh token
                    prompt='consent',       # Force consent screen to ensure refresh token
                    include_granted_scopes='true'
                )
            
            # Save the credentials only if we successfully got them
            if creds and creds.valid:
                try:
                    with open('token.json', 'w') as token:
                        token.write(creds.to_json())
                except Exception as e:
                    print(f"Error saving token.json: {e}")
    except Exception as e:
        print(f"Error in authentication flow: {e}")
        raise
    
    return build('gmail', 'v1', credentials=creds)
