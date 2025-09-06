import datetime
from email.mime.text import MIMEText
import base64

from app.ai_service import AIService
import json

def get_unreplied_sent_emails(service):
    """Fetch sent emails from the last 30 days that haven't received replies."""
    thirty_days_ago = int((datetime.datetime.utcnow() - datetime.timedelta(days=30)).timestamp())
    query = f'label:SENT after:{thirty_days_ago}'
    results = service.users().messages().list(userId='me', q=query, maxResults=20).execute()
    unreplied_emails = []
    
    # Get user's email for identifying self-sent messages
    profile = service.users().getProfile(userId='me').execute()
    user_email = profile['emailAddress']
    
    # Initialize AI service
    ai_service = AIService()
    
    messages = results.get('messages', [])
    for msg in messages:
        # Get the full thread
        thread = service.users().threads().get(userId='me', id=msg['threadId']).execute()
        thread_messages = thread.get('messages', [])
        
        # Check if the first message in thread is from the user
        first_msg = thread_messages[0]
        first_msg_headers = first_msg['payload']['headers']
        from_header = next((h['value'] for h in first_msg_headers if h['name'].lower() == 'from'), '')
        if user_email not in from_header:
            continue  # Skip if user didn't initiate the thread
        
        # Find our sent message in the thread
        sent_msg = None
        for tmsg in thread_messages:
            if tmsg['id'] == msg['id']:
                sent_msg = tmsg
                break
                
        if not sent_msg:
            continue
            
        # Get sent message details
        sent_msg_date = int(sent_msg['internalDate']) // 1000
        headers = sent_msg['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
        to = next((h['value'] for h in headers if h['name'].lower() == 'to'), 'Unknown')
        date = datetime.datetime.fromtimestamp(sent_msg_date).strftime('%Y-%m-%d %H:%M:%S')
        
        # Check for replies after our sent message
        has_reply = False
        for tmsg in thread_messages:
            msg_date = int(tmsg['internalDate']) // 1000
            if msg_date > sent_msg_date:  # Message is after our sent message
                headers = tmsg['payload']['headers']
                from_header = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
                # Check if message is from someone else (not us)
                if user_email not in from_header:
                    has_reply = True
                    break
        
        if not has_reply:
            # Analyze thread with AI
            snippet = sent_msg.get('snippet', '')
            thread_content = '\n'.join([
                m.get('snippet', '') for m in thread_messages
            ])
            
            days_since_sent = (datetime.datetime.utcnow() - 
                             datetime.datetime.fromtimestamp(sent_msg_date)).days
            
            ai_analysis = ai_service.analyze_thread_urgency(thread_content, days_since_sent)
            try:
                analysis = json.loads(ai_analysis)
                if analysis.get('needs_followup', False):
                    # Generate AI follow-up content
                    recipient_name = to.split('<')[0].strip()
                    followup_content = ai_service.generate_followup_email(
                        thread_content,
                        recipient_name,
                        snippet,
                        days_since_sent
                    )
                    
                    unreplied_emails.append({
                        'id': msg['id'],
                        'thread_id': thread['id'],
                        'subject': subject,
                        'to': to,
                        'date': date,
                        'snippet': snippet,
                        'urgency': analysis.get('urgency', 'medium'),
                        'reason': analysis.get('reason', ''),
                        'ai_followup': followup_content
                    })
            except json.JSONDecodeError:
                # Fallback if AI analysis fails
                unreplied_emails.append({
                    'id': msg['id'],
                    'thread_id': thread['id'],
                    'subject': subject,
                    'to': to,
                    'date': date,
                    'snippet': snippet,
                    'urgency': 'unknown',
                    'reason': 'AI analysis failed',
                    'ai_followup': None
                })
    
    return unreplied_emails

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
        # service.users().messages().send(
        #     userId='me',
        #     body={'raw': raw_message, 'threadId': thread_id}
        # ).execute()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
