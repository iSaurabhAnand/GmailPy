from flask import render_template_string, request, jsonify, Response
from app import app
from app.gmail_service import get_gmail_service
from app.email_service import get_threads_to_follow_up, get_threads_to_follow_up_generator, send_followup_email
from app.config import DISABLE_SEND_FOLLOWUP
from itertools import groupby
import json

# HTML template for the main page with progressive loading
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
        .loading-indicator {
            display: none;
            text-align: center;
            padding: 20px;
            color: #5f6368;
            font-size: 14px;
        }
        .loading-indicator.active {
            display: block;
        }
        .spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #1a73e8;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 10px;
            vertical-align: middle;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .group-section {
            background-color: white;
            border: 1px solid #dadce0;
            border-radius: 8px;
            margin-bottom: 20px;
            overflow: hidden;
            box-shadow: 0 1px 2px rgba(60,64,67,.1);
            animation: slideIn 0.3s ease-out;
        }
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
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
            animation: fadeIn 0.2s ease-out;
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
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
    const groupsMap = new Map(); // Track groups by subject
    
    // Decode HTML entities
    function decodeHTMLEntities(text) {
        const textarea = document.createElement('textarea');
        textarea.innerHTML = text;
        return textarea.value;
    }
    
    function toggleGroupCheckboxes(groupIndex, mainCheckbox) {
        const emailCheckboxes = document.querySelectorAll(`.group-${groupIndex} .email-checkbox`);
        emailCheckboxes.forEach(cb => {
            cb.checked = mainCheckbox.checked;
        });
    }

    function toggleGroupByClick(headerEl, groupIndex) {
        const cb = headerEl.querySelector('input[type="checkbox"]');
        if (!cb) return;
        cb.checked = !cb.checked;
        toggleGroupCheckboxes(groupIndex, cb);
    }

    function updateEmailCount(subject) {
        const group = groupsMap.get(subject);
        if (group) {
            const count = group.emails.length;
            const countEl = group.section.querySelector('.email-count');
            if (countEl) {
                countEl.textContent = `${count} email${count !== 1 ? 's' : ''}`;
            }
        }
    }

    function addThreadToUI(thread, groupIndex) {
        const subject = thread.subject;
        
        // Create or get group
        if (!groupsMap.has(subject)) {
            const groupSection = document.createElement('div');
            groupSection.className = 'group-section';
            
            const header = document.createElement('div');
            header.className = 'group-header';
            header.onclick = () => toggleGroupByClick(header, groupIndex);
            
            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.className = 'group-checkbox';
            checkbox.checked = true;
            checkbox.onclick = (e) => e.stopPropagation();
            checkbox.onchange = (e) => toggleGroupCheckboxes(groupIndex, e.target);
            
            const title = document.createElement('span');
            title.className = 'subject-title';
            title.textContent = decodeHTMLEntities(subject);
            
            const count = document.createElement('span');
            count.className = 'email-count';
            count.textContent = '0 emails';
            
            header.appendChild(checkbox);
            header.appendChild(title);
            header.appendChild(count);
            
            const emailsList = document.createElement('div');
            emailsList.className = 'emails-list';
            
            const actions = document.createElement('div');
            actions.className = 'group-actions';
            
            const sendBtn = document.createElement('button');
            sendBtn.className = 'btn btn-primary';
            sendBtn.textContent = 'Send Follow-ups';
            sendBtn.onclick = () => sendSelectedFollowUps(groupIndex);
            
            actions.appendChild(sendBtn);
            
            groupSection.appendChild(header);
            groupSection.appendChild(emailsList);
            groupSection.appendChild(actions);
            
            document.getElementById('groups-container').appendChild(groupSection);
            
            groupsMap.set(subject, {
                section: groupSection,
                emails: [],
                emailsList: emailsList,
                groupIndex: groupIndex
            });
        }
        
        const group = groupsMap.get(subject);
        
        // Add email to list
        const emailItem = document.createElement('div');
        emailItem.className = `email-item group-${groupIndex}`;
        
        const cbEmail = document.createElement('input');
        cbEmail.type = 'checkbox';
        cbEmail.className = 'email-checkbox';
        cbEmail.dataset.emailId = thread.id;
        cbEmail.dataset.threadId = thread.thread_id;
        cbEmail.dataset.to = thread.to;
        cbEmail.dataset.subject = thread.subject;
        cbEmail.checked = true;
        
        const details = document.createElement('div');
        details.className = 'email-details';
        
        const toDiv = document.createElement('div');
        toDiv.className = 'email-to';
        toDiv.textContent = decodeHTMLEntities(thread.to);
        
        const dateDiv = document.createElement('div');
        dateDiv.className = 'email-date';
        dateDiv.textContent = decodeHTMLEntities(thread.date);
        
        const daysDiv = document.createElement('div');
        daysDiv.className = 'email-date';
        daysDiv.textContent = `${thread.days_since_last} days since follow-up`;
        
        details.appendChild(toDiv);
        details.appendChild(dateDiv);
        details.appendChild(daysDiv);
        
        if (thread.snippet) {
            const snippetDiv = document.createElement('div');
            snippetDiv.className = 'snippet-text';
            snippetDiv.textContent = decodeHTMLEntities(thread.snippet);
            details.appendChild(snippetDiv);
        }
        
        emailItem.appendChild(cbEmail);
        emailItem.appendChild(details);
        group.emailsList.appendChild(emailItem);
        group.emails.push(thread);
        updateEmailCount(subject);
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
            setTimeout(() => {
                fetch('/send-followup', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(email)
                })
                .then(r => r.json())
                .then(result => {
                    if (result.success) {
                        completed++;
                        const checkbox = document.querySelector(
                            `.email-checkbox[data-email-id="${email.email_id}"]`
                        );
                        if (checkbox) {
                            checkbox.parentElement.style.opacity = '0.5';
                            checkbox.disabled = true;
                        }
                    } else {
                        failed++;
                    }
                    const progress = completed + failed;
                    button.textContent = `${progress}/${selectedEmails.length}`;
                    
                    if (progress === selectedEmails.length) {
                        button.disabled = false;
                        button.textContent = originalText;
                        if (failed === 0) {
                            button.innerHTML += '<span class="status-message status-success"> ✓ Done</span>';
                        } else {
                            button.innerHTML += `<span class="status-message status-error"> ${failed} failed</span>`;
                        }
                    }
                });
            }, index * 500);
        });
    }

    // Connect to SSE stream
    function connectToStream() {
        const eventSource = new EventSource('/api/threads-stream');
        let groupIndex = 0;
        
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === 'complete') {
                eventSource.close();
                const loadingEl = document.querySelector('.loading-indicator');
                if (loadingEl) {
                    loadingEl.classList.remove('active');
                }
                const container = document.getElementById('groups-container');
                if (container.children.length === 0) {
                    const emptyState = document.createElement('div');
                    emptyState.className = 'empty-state';
                    emptyState.textContent = 'No emails require follow-up at this time.';
                    container.appendChild(emptyState);
                }
            } else if (data.type === 'thread') {
                addThreadToUI(data.thread, groupIndex);
                if (data.current_subject !== data.thread.subject) {
                    groupIndex++;
                }
            }
        };
        
        eventSource.onerror = (error) => {
            console.error('Stream error:', error);
            eventSource.close();
            const loadingEl = document.querySelector('.loading-indicator');
            if (loadingEl) {
                loadingEl.classList.remove('active');
                loadingEl.innerHTML = '<p style="color: #d33b27;">Error loading emails. Please refresh the page.</p>';
            }
        };
    }

    // Start streaming when page loads
    window.addEventListener('load', connectToStream);
    </script>
</head>
<body>
    <h1>Follow-up Required Emails</h1>
    <div class="loading-indicator active">
        <span class="spinner"></span>Loading emails...
    </div>
    <div id="groups-container"></div>
</body>
</html>
"""


@app.route('/api/threads-stream')
def threads_stream():
    """Stream threads as SSE for progressive UI rendering."""
    def generate():
        service = get_gmail_service()
        current_subject = None
        group_index = 0
        
        for thread in get_threads_to_follow_up_generator(service):
            data = {
                'type': 'thread',
                'thread': thread,
                'group_index': group_index,
                'current_subject': thread['subject']
            }
            # Track subject changes for grouping
            if current_subject != thread['subject']:
                current_subject = thread['subject']
                group_index += 1
            
            yield f"data: {json.dumps(data)}\n\n"
        
        # Signal completion
        yield "data: {\"type\": \"complete\"}\n\n"
    
    return Response(generate(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no'
    })


@app.route('/')
def index():
    """Render the main page with progressive loading."""
    return render_template_string(TEMPLATE)


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