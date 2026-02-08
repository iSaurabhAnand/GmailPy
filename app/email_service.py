from app.report_service import generate_followup_report
from app.config import FOLLOWUP_TEMPLATES

import datetime
import os
import base64
from email.mime.text import MIMEText
from typing import List, Dict
from app.config import MIN_DAYS, MAX_DAYS, BATCH_SIZE, MAX_FOLLOW_UPS



def get_threads_to_follow_up(service) -> List[Dict]:
    """
    Get threads from last MIN_DAYS to MAX_DAYS, batch-wise, that need follow-up.
    """
    profile = service.users().getProfile(userId='me').execute()
    user_email = profile['emailAddress']
    now = datetime.datetime.utcnow()
    after_ts = int((now - datetime.timedelta(days=MAX_DAYS)).timestamp())
    before_ts = int((now - datetime.timedelta(days=MIN_DAYS)).timestamp())
    query = f"label:SENT after:{after_ts} before:{before_ts} subject:'Interest in'"

    threads_to_follow_up = []
    page_token = None
    while True:
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=BATCH_SIZE,
            pageToken=page_token
        ).execute()
        messages = results.get('messages', [])
        if not messages:
            break

        thread_ids = set(msg['threadId'] for msg in messages)
        for thread_id in thread_ids:
            thread = service.users().threads().get(userId='me', id=thread_id).execute()
            thread_messages = thread.get('messages', [])
            # Only process if all messages are from user
            if all(is_from_user(m, user_email) for m in thread_messages):
                # Filter: first email subject must start with 'Interest in'
                if thread_messages:
                    first_subject = get_header(thread_messages[0], 'subject').strip().lower()
                    if not first_subject.startswith('interest in'):
                        continue
                # Check last message date
                last_msg = thread_messages[-1]
                last_msg_date = int(last_msg['internalDate']) // 1000
                days_since_last = (now - datetime.datetime.fromtimestamp(last_msg_date)).days
                if days_since_last >= MIN_DAYS:
                    # Check follow-up count
                    followup_count = count_followups(thread_messages)
                    if followup_count < MAX_FOLLOW_UPS:
                        threads_to_follow_up.append({
                            'id': last_msg['id'],
                            'thread_id': thread_id,
                            'subject': get_header(last_msg, 'subject'),
                            'to': get_header(last_msg, 'to'),
                            'date': datetime.datetime.fromtimestamp(last_msg_date).strftime('%Y-%m-%d %H:%M:%S'),
                            'snippet': last_msg.get('snippet', ''),
                            'followup_count': followup_count,
                            'days_since_last': days_since_last
                        })
        page_token = results.get('nextPageToken')
        if not page_token:
            break
    # Generate CSV report after batch processing
    from app.report_service import generate_followup_report
    generate_followup_report(threads_to_follow_up)
    return threads_to_follow_up

def is_from_user(message, user_email: str) -> bool:
    try:
        headers = message.get('payload', {}).get('headers', [])
        from_header = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
        return user_email in from_header
    except (KeyError, AttributeError):
        return False

def get_header(message, name: str) -> str:
    try:
        headers = message.get('payload', {}).get('headers', [])
        return next((h['value'] for h in headers if h['name'].lower() == name.lower()), '')
    except (KeyError, AttributeError):
        return ''

def count_followups(messages: List[Dict]) -> int:
    """Count how many follow-ups have been sent in this thread."""
    # Simple heuristic: count messages with subject starting with 'Re:' or containing 'follow up'
    count = 0
    for m in messages:
        subject = get_header(m, 'subject').lower()
        if subject.startswith('re:') or 'follow up' in subject:
            count += 1
    return count

def send_followup_email(service, to: str, subject: str, thread_id: str) -> bool:
    """Send a general follow-up email."""
    try:
        from datetime import datetime
        import re
        
        # Get authenticated user's profile for actual email
        profile = service.users().getProfile(userId='me').execute()
        profile_email = profile['emailAddress']
        sender_name = os.getenv('SENDER_NAME', 'Nishant Soni')
        
        # Get thread and extract message IDs for threading
        thread = service.users().threads().get(userId='me', id=thread_id).execute()
        last_email_date = None
        thread_messages = thread.get('messages', [])
        receiver_name = None
        original_message_id = None
        
        if thread and 'messages' in thread and thread['messages']:
            # Get first message (original) for In-Reply-To header
            first_msg = thread['messages'][0]
            first_msg_headers = first_msg.get('payload', {}).get('headers', [])
            original_message_id = next((h['value'] for h in first_msg_headers if h['name'].lower() == 'message-id'), None)
            
            # Get last message date
            last_msg = thread['messages'][-1]
            last_email_ts = int(last_msg.get('internalDate', '0')) // 1000
            last_email_date = datetime.utcfromtimestamp(last_email_ts).strftime('%Y-%m-%d %H:%M UTC')
            
            # Extract receiver name from first message salutation
            payload = first_msg.get('payload', {})
            parts = payload.get('parts', [])
            body_data = None
            if parts:
                for part in parts:
                    if part.get('mimeType') == 'text/plain' and 'data' in part.get('body', {}):
                        body_data = part['body']['data']
                        break
            else:
                body_data = payload.get('body', {}).get('data')
            
            if body_data:
                # Ensure proper padding for base64 then decode
                padded = body_data + '=' * (-len(body_data) % 4)
                decoded_body = base64.urlsafe_b64decode(padded).decode('utf-8', errors='ignore')
                # Match salutations like "Hi James," or "Hello James Smith" (case-insensitive, multiline).
                m = re.search(
                    r'^\s*(?:hi|hello)[\s,]+([A-Za-z][A-Za-z\'\-\s]*?)(?=[,\.\n\r]|$)',
                    decoded_body,
                    re.IGNORECASE | re.MULTILINE
                )
                if m:
                    receiver_name = m.group(1).strip()
        
        if not receiver_name:
            receiver_name = ''
        
        # Select template based on follow-up count
        followup_count = count_followups(thread_messages)
        print(f"Follow-up count for thread {thread_id}: {followup_count}")
        template_idx = followup_count % len(FOLLOWUP_TEMPLATES)
        template_body = FOLLOWUP_TEMPLATES[template_idx]
        salutation = f"Hi {receiver_name}," if receiver_name else "Hi,"
        
        #signature = f"{sender_name}\n{sender_email}{spacing}{separator}{spacing}{sender_phone}"
        signature = f"{sender_name}"
        message_text = f"{salutation}\n\n{template_body}\n\nThanks,\n{signature}"
        
        message = MIMEText(message_text)
        message['to'] = to
        message['from'] = f"{sender_name} <{profile_email}>"
        message['subject'] = f"Re: {subject}"
        
        # Add threading headers to keep emails in same thread
        if original_message_id:
            message['In-Reply-To'] = original_message_id
            message['References'] = original_message_id
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        service.users().messages().send(
            userId='me',
            body={'raw': raw, 'threadId': thread_id}
        ).execute()
        return True
    except Exception as e:
        print(f"Error sending follow-up: {e}")
        return False
