from flask import render_template_string, request, jsonify
from app import app
from app.gmail_service import get_gmail_service
from app.email_service import get_threads_to_follow_up, send_followup_email
from app.config import DISABLE_SEND_FOLLOWUP
from itertools import groupby

# HTML template for the main page with grouped subjects
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Follow-ups by Subject</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; 
            padding: 20px; 
            background-color: #f5f5f5;
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            margin-bottom: 24px;
            color: #202124;
            font-size: 28px;
        }
        .group-section {
            background-color: white;
            border: 1px solid #dadce0;
            border-radius: 8px;
            margin-bottom: 20px;
            overflow: hidden;
            box-shadow: 0 1px 2px rgba(60,64,67,.1);
        }
        .group-header {
            background-color: #f8f9fa;
            padding: 16px;
            border-bottom: 1px solid #dadce0;
            display: flex;
            align-items: center;
            gap: 12px;
            cursor: pointer;
            user-select: none;
        }
        .group-header input[type="checkbox"] {
            width: 20px;
            height: 20px;
            cursor: pointer;
        }
        .group-header:hover {
            background-color: #f0f0f0;
        }
        .subject-title {
            flex: 1;
            font-weight: 500;
            color: #202124;
            font-size: 16px;
        }
        .email-count {
            color: #5f6368;
            font-size: 14px;
            background-color: white;
            padding: 4px 8px;
            border-radius: 12px;
        }
        .emails-list {
            max-height: 500px;
            overflow-y: auto;
        }
        .email-item {
            padding: 12px 16px;
            border-bottom: 1px solid #f0f0f0;
            display: flex;
            gap: 12px;
            align-items: flex-start;
        }
        .email-item:last-child {
            border-bottom: none;
        }
        .email-item input[type="checkbox"] {
            width: 18px;
            height: 18px;
            margin-top: 4px;
            cursor: pointer;
            flex-shrink: 0;
        }
        .email-details {
            flex: 1;
            min-width: 0;
        }
        .email-to {
            color: #1a73e8;
            font-size: 13px;
            margin-bottom: 4px;
        }
        .email-date {
            color: #5f6368;
            font-size: 12px;
        }
        .snippet-text {
            color: #3c4043;
            font-size: 12px;
            margin-top: 4px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        .group-actions {
            padding: 12px 16px;
            background-color: #f8f9fa;
            border-top: 1px solid #dadce0;
            display: flex;
            gap: 8px;
            justify-content: flex-end;
        }
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 500;
            font-size: 14px;
            transition: all 0.2s;
        }
        .btn-primary {
            background-color: #1a73e8;
            color: white;
        }
        .btn-primary:hover {
            background-color: #1557b0;
            box-shadow: 0 1px 3px rgba(26, 115, 232, 0.3);
        }
        .btn-primary:disabled {
            background-color: #e0e0e0;
            color: #999;
            cursor: not-allowed;
        }
        .btn-secondary {
            background-color: #f1f3f4;
            color: #3c4043;
        }
        .btn-secondary:hover {
            background-color: #e8eaed;
        }
        .status-message {
            display: inline-block;
            margin-left: 8px;
            font-weight: 500;
            font-size: 13px;
        }
        .status-success {
            color: #188038;
        }
        .status-error {
            color: #d33b27;
        }
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: #5f6368;
        }
    </style>
    <script>
    function toggleGroupCheckboxes(groupIndex, mainCheckbox) {
        const emailCheckboxes = document.querySelectorAll(`.group-${groupIndex} .email-checkbox`);
        emailCheckboxes.forEach(cb => {
            cb.checked = mainCheckbox.checked;
        });
    }

    // Toggle group checkbox reliably and propagate to child checkboxes.
    function toggleGroupByClick(headerEl, groupIndex) {
        const cb = headerEl.querySelector('input[type="checkbox"]');
        if (!cb) return;
        // Flip checkbox state
        cb.checked = !cb.checked;
        // Propagate change to children
        toggleGroupCheckboxes(groupIndex, cb);
    }

    function sendSelectedFollowUps(groupIndex) {
        const selectedEmails = Array.from(document.querySelectorAll(`.group-${groupIndex} .email-checkbox:checked`))
            .map(cb => ({
                email_id: cb.dataset.emailId,
                thread_id: cb.dataset.threadId,
                to: cb.dataset.to,
                subject: cb.dataset.subject
            }));

        if (selectedEmails.length === 0) {
            alert('Please select at least one email');
            return;
        }

        const button = event.target;
        button.disabled = true;
        const originalText = button.textContent;
        let completed = 0;
        let failed = 0;

        selectedEmails.forEach((email, index) => {
            fetch('/send-followup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(email)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    completed++;
                    const checkbox = document.querySelector(`.email-checkbox[data-email-id="${email.email_id}"]`);
                    checkbox.parentElement.parentElement.style.opacity = '0.6';
                    checkbox.disabled = true;
                } else {
                    failed++;
                }
                if (completed + failed === selectedEmails.length) {
                    const message = document.createElement('span');
                    message.className = 'status-message ' + (failed === 0 ? 'status-success' : 'status-error');
                    message.textContent = `✓ ${completed} sent${failed > 0 ? `, ${failed} failed` : ''}`;
                    button.parentElement.appendChild(message);
                    button.style.display = 'none';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                failed++;
                if (completed + failed === selectedEmails.length) {
                    const message = document.createElement('span');
                    message.className = 'status-message status-error';
                    message.textContent = `✗ Error: ${failed} failed`;
                    button.parentElement.appendChild(message);
                    button.disabled = false;
                }
            });
        });
    }
    </script>
</head>
<body>
    <h1>Follow-up Required Emails</h1>
    {% if groups %}
        {% set groupIndex = namespace(value=0) %}
        {% for subject, group_emails in groups %}
            <div class="group-section">
                <div class="group-header" onclick="toggleGroupByClick(this, {{ groupIndex.value }})">
                    <!-- stopPropagation so clicking the checkbox doesn't also trigger the header click -->
                    <input type="checkbox" class="group-checkbox" onclick="event.stopPropagation();" onchange="toggleGroupCheckboxes({{ groupIndex.value }}, this)" checked>
                    <span class="subject-title">{{ subject }}</span>
                    <span class="email-count">{{ group_emails|length }} email{{ 's' if group_emails|length != 1 else '' }}</span>
                </div>
                <div class="emails-list">
                    {% for email in group_emails %}
                    <div class="email-item group-{{ groupIndex.value }}">
                        <input type="checkbox" class="email-checkbox" 
                               data-email-id="{{ email.id }}"
                               data-thread-id="{{ email.thread_id }}"
                               data-to="{{ email.to }}"
                               data-subject="{{ email.subject }}"
                               checked>
                        <div class="email-details">
                            <div class="email-to">{{ email.to }}</div>
                            <div class="email-date">{{ email.date }}</div>
                            {% if email.days_since_last %}
                            <div class="email-date">{{ email.days_since_last }} days since follow-up</div>
                            {% endif %}
                            {% if email.snippet %}
                            <div class="snippet-text">{{ email.snippet }}</div>
                            {% endif %}
                        </div>
                    </div>
                    {% endfor %}
                </div>
                <div class="group-actions">
                    <button class="btn btn-primary" onclick="sendSelectedFollowUps({{ groupIndex.value }})">
                        Send Follow-ups
                    </button>
                </div>
            </div>
            {% set groupIndex.value = groupIndex.value + 1 %}
        {% endfor %}
    {% else %}
        <div class="empty-state">
            <p>No emails require follow-up at this time.</p>
        </div>
    {% endif %}
</body>
</html>
"""


@app.route('/')
def index():
    """Render the main page with emails grouped by subject."""
    service = get_gmail_service()
    emails = get_threads_to_follow_up(service)
    
    # Group emails by subject
    emails_sorted = sorted(emails, key=lambda x: x['subject'])
    groups = []
    for subject, group in groupby(emails_sorted, key=lambda x: x['subject']):
        groups.append((subject, list(group)))
    
    return render_template_string(TEMPLATE, groups=groups)

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