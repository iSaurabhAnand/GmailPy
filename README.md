# GmailPy

A Python project to connect to Gmail and read sent emails using the Gmail API.

## Features
- Authenticate with Gmail using OAuth2
- Read sent emails from your Gmail account

## Setup Instructions
1. Create a Google Cloud project and enable the Gmail API.
2. Download your OAuth2 credentials (`credentials.json`).
3. By default, the script looks for `credentials.json` in the project root. You can specify a custom path using the `GMAIL_CREDENTIALS_PATH` environment variable:
   ```zsh
   export GMAIL_CREDENTIALS_PATH=/path/to/your/credentials.json
   ```
4. Install dependencies:
   ```bash
   pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
   ```
5. Run the script to authenticate and read sent emails.

## Usage
- See `main.py` for example usage.
- The credentials file path can be set via the `GMAIL_CREDENTIALS_PATH` environment variable.

## Documentation
- [Gmail API Python Quickstart](https://developers.google.com/gmail/api/quickstart/python)

---
Replace placeholders with your actual credentials and follow Google security best practices.
