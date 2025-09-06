import datetime
import os
from email.mime.text import MIMEText
import base64
from app.ai_service import AIService
import json
from typing import List, Dict

# Constants
BATCH_SIZE = 20
MIN_DAYS = 2
MAX_DAYS = 30
USE_AI = os.getenv('USE_AI', 'false').lower() == 'true'
import json
from typing import List, Dict

# Constants
BATCH_SIZE = 20
MIN_DAYS = 2
MAX_DAYS = 30
USE_AI = os.getenv('USE_AI', 'false').lower() == 'true'

def get_unreplied_sent_emails(service) -> List[Dict]:
    """
    Fetch sent emails from the last 2-30 days that haven't received replies.
    Process in batches of 20 with optional AI analysis.
    """
    # Calculate time range
    now = datetime.datetime.utcnow()
    max_days_ago = int((now - datetime.timedelta(days=MAX_DAYS)).timestamp())
    min_days_ago = int((now - datetime.timedelta(days=MIN_DAYS)).timestamp())
    
    # Build query
    query = f'label:SENT after:{max_days_ago} before:{min_days_ago}'
    
    # Get user profile once
    profile = service.users().getProfile(userId='me').execute()
    user_email = profile['emailAddress']
    
    # Initialize AI service if needed
    ai_service = AIService() if USE_AI else None
    
    unreplied_emails = []
    page_token = None
    
    while True:
        # Fetch batch of messages
        results = service.users().messages().list(
            userId='me', 
            q=query, 
            maxResults=BATCH_SIZE,
            pageToken=page_token
        ).execute()
        
        messages = results.get('messages', [])
        if not messages:
            break
            
        # Collect thread IDs for batch processing
        thread_ids = [msg['threadId'] for msg in messages]
        threads_to_analyze = []
        
        # Process each thread in the batch
        for thread_id in thread_ids:
            thread = service.users().threads().get(userId='me', id=thread_id).execute()
            thread_messages = thread.get('messages', [])
            
            # Skip if user didn't initiate thread
            first_msg = thread_messages[0]
            first_msg_headers = first_msg['payload']['headers']
            from_header = next((h['value'] for h in first_msg_headers if h['name'].lower() == 'from'), '')
            if user_email not in from_header:
                continue
                
            # Find sent message and check for replies
            sent_msg = next((m for m in thread_messages if m['id'] in [msg['id'] for msg in messages]), None)
            if not sent_msg:
                continue
                
            sent_msg_date = int(sent_msg['internalDate']) // 1000
            has_reply = any(
                int(m['internalDate']) // 1000 > sent_msg_date and
                user_email not in next((h['value'] for h in m['payload']['headers'] if h['name'].lower() == 'from'), '')
                for m in thread_messages
            )
            
            if not has_reply:
                thread_data = process_thread(sent_msg, thread_messages, user_email)
                if USE_AI:
                    threads_to_analyze.append(thread_data)
                else:
                    unreplied_emails.append(thread_data)
        
        # Batch AI analysis if enabled
        if USE_AI and threads_to_analyze:
            analyzed_threads = batch_analyze_threads(ai_service, threads_to_analyze)
            unreplied_emails.extend(analyzed_threads)
        
        # Check for more pages
        page_token = results.get('nextPageToken')
        if not page_token:
            break
    
    return unreplied_emails

def process_thread(sent_msg, thread_messages, user_email) -> Dict:
    """Process a single thread and extract relevant information."""
    sent_msg_date = int(sent_msg['internalDate']) // 1000
    headers = sent_msg['payload']['headers']
    days_since_sent = (datetime.datetime.utcnow() - 
                      datetime.datetime.fromtimestamp(sent_msg_date)).days

    # If AI is disabled, determine follow-up based on time passed
    needs_followup = True if not USE_AI and MIN_DAYS <= days_since_sent <= MAX_DAYS else False
    
    return {
        'id': sent_msg['id'],
        'thread_id': sent_msg['threadId'],
        'subject': next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject'),
        'to': next((h['value'] for h in headers if h['name'].lower() == 'to'), 'Unknown'),
        'date': datetime.datetime.fromtimestamp(sent_msg_date).strftime('%Y-%m-%d %H:%M:%S'),
        'snippet': sent_msg.get('snippet', ''),
        'thread_content': '\n'.join([m.get('snippet', '') for m in thread_messages]),
        'days_since_sent': days_since_sent,
        'needs_followup': needs_followup,  # Will be True if AI is off and within time range
        'urgency': 'medium' if needs_followup else 'low',  # Default urgency when AI is off
        'reason': f'No response for {days_since_sent} days' if needs_followup else '',
        'ai_followup': None      # Will be updated by AI if enabled
    }

def batch_analyze_threads(ai_service, threads: List[Dict]) -> List[Dict]:
    """Analyze multiple threads in batch with AI."""
    analyzed_threads = []
    
    for thread in threads:
        try:
            # Analyze thread urgency
            ai_analysis = ai_service.analyze_thread_urgency(
                thread['thread_content'],
                thread['days_since_sent']
            )
            analysis = json.loads(ai_analysis)
            
            thread.update({
                'needs_followup': analysis.get('needs_followup', False),
                'urgency': analysis.get('urgency', 'low'),
                'reason': analysis.get('reason', '')
            })
            
            # Generate follow-up email if needed
            if analysis.get('needs_followup', False):
                recipient_name = thread['to'].split('<')[0].strip()
                followup_content = ai_service.generate_followup_email(
                    thread['thread_content'],
                    recipient_name,
                    thread['snippet'],
                    thread['days_since_sent']
                )
                thread['ai_followup'] = followup_content
            
            analyzed_threads.append(thread)
                
        except Exception as e:
            thread.update({
                'needs_followup': False,
                'urgency': 'unknown',
                'reason': f'AI analysis failed: {str(e)}',
                'ai_followup': None
            })
            analyzed_threads.append(thread)
    
    return analyzed_threads
        

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
