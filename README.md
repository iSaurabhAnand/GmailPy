# GmailPy

A Python project to connect to Gmail and automatically send follow-up emails to contacts based on configurable criteria. Features a responsive web UI with real-time email streaming and AI-powered reply suggestions.

## Features
- **Gmail Authentication**: Securely authenticate with Gmail using OAuth2
- **Automated Follow-ups**: Automatically identify threads that need follow-up based on time elapsed
- **Web UI**: Interactive dashboard to preview and manage follow-up emails
- **Progressive Rendering**: Stream email data in real-time for responsive UI experience
- **Email Threading**: Maintain proper email threading with Message-ID headers
- **Previous Message Attachment**: Automatically include previous messages in follow-up emails like Gmail web version
- **Dynamic Separator**: Cycle through different separators (|, -, ||) for visual distinction across follow-ups
- **AI Integration**: Optional OpenAI API integration for smart email suggestions
- **Email Reporting**: Generate CSV reports of follow-up activities
- **Dry-run Mode**: Test email sending without actually sending

## Features Details

### Automated Follow-up Detection
- Identifies emails matching follow-up criteria (subject starts with "Interest in")
- Filters by date range (configurable MIN_DAYS and MAX_DAYS)
- Limits follow-ups per thread (configurable MAX_FOLLOW_UPS)
- Tracks follow-up count using email subject patterns

### Email Formatting
- **Dynamic Separators**: Each follow-up uses a different separator to make threads visually distinct
- **Previous Messages**: Automatically includes the original message with separator line
- **Proper Threading**: Uses Message-ID and References headers for correct Gmail threading
- **HTML Entity Decoding**: Properly decodes Gmail API HTML entities in email text

### Web Interface
- Real-time email streaming with loading indicator
- Group emails by subject with expand/collapse functionality
- Bulk selection and sending with progress tracking
- Visual feedback for success/failed sends

## Setup Instructions

1. Create a Google Cloud project and enable the Gmail API:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Gmail API
   - Create OAuth2 credentials (Desktop application)
   - Download the credentials as `credentials.json`

2. Place credentials file:
   ```bash
   # Option 1: Use default location
   cp credentials.json ./
   
   # Option 2: Use custom path (via GMAIL_CREDENTIALS_PATH env var)
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. First run will prompt you to authorize the application with your Gmail account.

## Configuration

Set these environment variables to customize behavior:

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `GMAIL_CREDENTIALS_PATH` | String | `./credentials.json` | Path to Gmail OAuth2 credentials file |
| `OPENAI_API_KEY` | String | Optional | OpenAI API key for AI-powered suggestions |
| `USE_AI` | Boolean (0/1) | `0` | Enable AI integration for email suggestions |
| `DEBUG` | Boolean (0/1) | `0` | Enable debug logging |
| `DISABLE_SEND_FOLLOWUP` | Boolean (0/1) | `0` | Dry-run mode: preview without sending |
| `ENABLE_FLASK_UI` | Boolean (0/1) | `0` | Enable web UI on port 5000 |
| `MIN_DAYS` | Integer | `5` | Minimum days before sending follow-up |
| `MAX_DAYS` | Integer | `30` | Maximum days to look back for emails |
| `BATCH_SIZE` | Integer | `20` | Number of messages per API batch |
| `MAX_FOLLOW_UPS` | Integer | `3` | Maximum follow-ups per thread |
| `SENDER_NAME` | String | `Your Name` | Name to use in email signatures |
| `SENDER_EMAIL` | String | `your-email@example.com` | Email address for follow-ups |
| `SENDER_PHONE` | String | `(555) 555-5555` | Phone number in signature |

## Usage

### Run with Web UI (Interactive Mode)
```bash
GMAIL_CREDENTIALS_PATH=/path/to/credentials.json \
OPENAI_API_KEY=your-api-key \
DEBUG=true \
USE_AI=false \
DISABLE_SEND_FOLLOWUP=1 \
ENABLE_FLASK_UI=1 \
python run.py
```

Then open [http://localhost:5000](http://localhost:5000) in your browser.

### Dry-run Mode (Preview without sending)
```bash
GMAIL_CREDENTIALS_PATH=/path/to/credentials.json \
DEBUG=true \
DISABLE_SEND_FOLLOWUP=1 \
python run.py
```

### Actually Send Follow-ups
```bash
GMAIL_CREDENTIALS_PATH=/path/to/credentials.json \
OPENAI_API_KEY=your-api-key \
USE_AI=true \
python run.py
```

### Minimal Configuration
```bash
GMAIL_CREDENTIALS_PATH=/path/to/credentials.json \
ENABLE_FLASK_UI=1 \
python run.py
```

## Web UI Features

The interactive web dashboard allows you to:
- **View all emails** needing follow-up, grouped by subject
- **Preview emails** before sending
- **Select/deselect** which emails to follow up on
- **Send bulk follow-ups** with progress tracking
- **Real-time feedback** on send success/failure

## Email Template

Emails are sent with:
1. **Salutation**: Auto-extracted from original message (e.g., "Hi James,")
2. **Body**: Template from `FOLLOWUP_TEMPLATES` (alternates each follow-up)
3. **Threading**: Maintains email thread with previous messages
4. **Separator**: Cycles through `|`, `-`, and `||` for visual distinction
5. **Signature**: Auto-formatted with name, email, and phone

Example:
```
Hi James,

I hope you are doing well. I just wanted to check in and gently 
follow up with you on my previous message. Looking forward to 
hearing back from you. Thank you for your time and consideration.

Thanks,

Your Name
your-email@example.com | (555) 555-5555

============================================================
Previous message:
============================================================
[Original email content here]
```

## Output

Follow-up activities are logged to:
- **Console**: Real-time progress logs
- **CSV Reports**: `followup_report_YYYY-MM-DD.csv` - records of sent follow-ups
- **Debug Logs**: When `DEBUG=1` is set

## Troubleshooting

### "No emails require follow-up at this time"
- Check that your Gmail account has sent emails matching the criteria
- Verify MIN_DAYS and MAX_DAYS settings
- Ensure emails have "Interest in" in the subject line

### "Permission denied" errors
- Ensure `GMAIL_CREDENTIALS_PATH` points to a valid credentials file
- Clear `token.json` and re-authenticate:
  ```bash
  rm token.json
  python run.py
  ```

### UI not loading
- Ensure `ENABLE_FLASK_UI=1` is set
- Check that port 5000 is not in use
- Verify `DEBUG=1` for error details

## Documentation

- [Gmail API Python Quickstart](https://developers.google.com/gmail/api/quickstart/python)
- [Gmail API Reference](https://developers.google.com/gmail/api/reference/rest)

---
