import os
from app.gmail_service import get_gmail_service
from app.email_service import get_threads_to_follow_up, send_followup_email
from app.report_service import generate_followup_report

def run_followup_and_report():
    disable_send = os.getenv('DISABLE_SEND_FOLLOWUP', '0') in ['1', 'true', 'True']
    service = get_gmail_service()
    threads = get_threads_to_follow_up(service)
    print(f"Found {len(threads)} threads to follow up.")
    results = []
    for thread in threads:
        result = {
            'to': thread.get('to'),
            'subject': thread.get('subject'),
            'thread_id': thread.get('thread_id'),
            'date': thread.get('date'),
            'followup_count': thread.get('followup_count', 0),
            'status': None
        }
        if disable_send:
            print(f"Dry run: Would send follow-up to {result['to']} | Subject: {result['subject']}")
            result['status'] = 'dry_run'
        else:
            success = send_followup_email(
                service,
                result['to'],
                result['subject'],
                result['thread_id']
            )
            print(f"Sent follow-up to {result['to']} | Subject: {result['subject']} | Success: {success}")
            result['status'] = 'sent' if success else 'failed'
        results.append(result)
    # Generate report after processing
    generate_followup_report(results)
