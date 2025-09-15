import csv
from typing import List, Dict
from app.config import *

def generate_followup_report(threads_to_follow_up: List[Dict], report_path: str = None):
    """
    Generate a day-wise CSV report of processed emails.
    Columns: Sent To, Subject, Prev Message sent on, Follow up text, Number of follow up
    """
    # Group by date
    day_groups = {}
    for thread in threads_to_follow_up:
        day = thread['date'].split(' ')[0]  # YYYY-MM-DD
        if day not in day_groups:
            day_groups[day] = []
        day_groups[day].append(thread)
    import datetime
    curr_date = datetime.datetime.now().strftime('%Y-%m-%d')
    if report_path is None:
        report_path = f"followup_report_{curr_date}.csv"

    with open(report_path, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Day", "Sent To", "Subject", "Prev Message sent on", "Follow up text", "Number of follow up"])
        for day, threads in sorted(day_groups.items()):
            for thread in threads:
                # Determine follow-up text and count
                followup_count = thread.get('followup_count', 0)
                template_idx = min(followup_count, len(FOLLOWUP_TEMPLATES)-1)
                followup_text = FOLLOWUP_TEMPLATES[template_idx]
                writer.writerow([
                    day,
                    thread.get('to', ''),
                    thread.get('subject', ''),
                    thread.get('date', ''),
                    followup_text,
                    followup_count
                ])
