import datetime
from email.mime.text import MIMEText
import base64

def get_unreplied_sent_emails(service):
    """Fetch sent emails from the last 30 days that haven't received replies."""
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
        
        if not _has_replies(thread_msgs, msg['id'], sent_msg_internal_date):
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

def _has_replies(thread_msgs, original_msg_id, sent_msg_internal_date):
    """Check if a message has any replies."""
    for tmsg in thread_msgs:
        if tmsg['id'] != original_msg_id and int(tmsg.get('internalDate', '0')) // 1000 > sent_msg_internal_date:
            # If the sender is not me, it's a reply
            headers = tmsg.get('payload', {}).get('headers', [])
            from_header = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
            if 'me' not in from_header:
                return True
    return False

def send_followup_email(service, to, subject, thread_id):
    """Send a follow-up email for an unreplied message."""
    # Get user's name from Gmail profile
    profile = service.users().getProfile(userId='me').execute()
    email = profile['emailAddress']
    # Extract first name and last name from email
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
