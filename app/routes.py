from flask import render_template_string, request, jsonify
from app import app
from app.gmail_service import get_gmail_service
from app.email_service import get_unreplied_sent_emails, send_followup_email

# HTML template for the main page
TEMPLATE = """
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

@app.route('/')
def index():
    """Render the main page with list of unreplied emails."""
    service = get_gmail_service()
    unreplied_emails = get_unreplied_sent_emails(service)
    return render_template_string(TEMPLATE, emails=unreplied_emails)

@app.route('/send-followup', methods=['POST'])
def send_followup():
    """Handle follow-up email requests."""
    data = request.json
    service = get_gmail_service()
    success = send_followup_email(
        service,
        data['to'],
        data['subject'],
        data['thread_id']
    )
    return jsonify({'success': success})
