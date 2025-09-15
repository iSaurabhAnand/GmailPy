
from flask import render_template_string, request, jsonify
from app import app
from app.gmail_service import get_gmail_service
from app.email_service import get_threads_to_follow_up, send_followup_email
from app.config import DISABLE_SEND_FOLLOWUP

# HTML template for the main page
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Unreplied Emails</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 20px; 
            background-color: #f5f5f5;
        }
        .email { 
            background-color: white;
            border: 1px solid #ddd; 
            margin: 15px 0; 
            padding: 20px; 
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .subject { 
            font-weight: bold; 
            color: #1a73e8; 
            font-size: 1.1em;
            margin-bottom: 8px;
        }
        .meta { 
            color: #666; 
            font-size: 0.9em; 
            margin: 8px 0;
            line-height: 1.4;
        }
        .snippet { 
            color: #444; 
            margin: 15px 0;
            line-height: 1.5;
            padding: 10px;
            background-color: #fafafa;
            border-radius: 4px;
        }
        .analysis {
            background-color: #f8f9fa;
            padding: 15px;
            margin: 15px 0;
            border-radius: 6px;
            border: 1px solid #e8eaed;
        }
        .analysis-item {
            margin: 10px 0;
            line-height: 1.5;
        }
        .needs-followup {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 15px;
            font-size: 0.9em;
            font-weight: 500;
            letter-spacing: 0.3px;
        }
        .needs-followup.true { 
            background-color: #e8f5e9; 
            color: #1b5e20;
            border: 1px solid #81c784;
        }
        .needs-followup.false { 
            background-color: #f5f5f5; 
            color: #666;
            border: 1px solid #ddd;
        }
        .reason {
            font-style: italic;
            color: #555;
            padding: 10px;
            background-color: white;
            border-radius: 4px;
            margin: 10px 0;
        }
        .followup-email {
            background-color: white;
            border: 1px solid #e0e0e0;
            padding: 15px;
            margin: 10px 0;
            border-radius: 6px;
            white-space: pre-wrap;
            line-height: 1.5;
            color: #333;
            font-family: 'Roboto Mono', monospace;
            font-size: 0.95em;
        }
        .actions { 
            margin-top: 15px;
            display: flex;
            align-items: center;
        }
        .follow-up-btn {
            background-color: #1a73e8;
            color: white;
            padding: 8px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            display: inline-block;
            font-weight: 500;
            transition: background-color 0.2s;
        }
        .follow-up-btn:hover {
            background-color: #1557b0;
        }
        .follow-up-btn:disabled {
            background-color: #e0e0e0;
            color: #999;
            cursor: not-allowed;
        }
        .success { 
            color: #2e7d32; 
            display: none; 
            margin-left: 15px;
            font-weight: 500;
        }
        .error { 
            color: #d32f2f; 
            display: none; 
            margin-left: 15px;
            font-weight: 500;
        }
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
        
        <div class="analysis">
            <div class="analysis-item">
                <span class="needs-followup {{ 'true' if email.needs_followup else 'false' }}">
                    {{ "Needs Follow-up" if email.needs_followup else "No Follow-up Needed" }}
                </span>
            </div>
            {% if email.reason %}
            <div class="analysis-item reason">
                {{ email.reason }}
            </div>
            {% endif %}
            {% if email.needs_followup and email.followup_email %}
            <div class="analysis-item">
                <strong>Suggested Follow-up:</strong>
                <div class="followup-email">{{ email.followup_email }}</div>
            </div>
            {% endif %}
        </div>

        <div class="actions">
            <button class="follow-up-btn" onclick="sendFollowUp(this, '{{ email.id }}', '{{ email.thread_id }}', '{{ email.to }}', '{{ email.subject }}')">
                Send Follow-up
            </button>
            <span class="success">✓ Sent!</span>
            <span class="error">Failed to send</span>
        </div>
    </div>
    {% endfor %}
</body>
</html>
"""

@app.route('/')
def index():
    """Render the main page with list of unreplied emails."""
    service = get_gmail_service()
    unreplied_emails = get_threads_to_follow_up(service)
    return render_template_string(TEMPLATE, emails=unreplied_emails)

@app.route('/send-followup', methods=['POST'])
def send_followup():
    """Handle follow-up email requests."""
    data = request.json
    # Use a flag from config to disable sending follow-up emails
    if DISABLE_SEND_FOLLOWUP:
        return jsonify({'success': False, 'error': 'Sending follow-up emails is disabled by flag.'})
    service = get_gmail_service()
    success = send_followup_email(
        service,
        data['to'],
        data['subject'],
        data['thread_id']
    )
    return jsonify({'success': success})
