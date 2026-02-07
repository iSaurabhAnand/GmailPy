import os
from app import app
from app.logger import setup_logger
from app.followup_service import run_followup_and_report

# Configurable flag to enable/disable Flask UI
ENABLE_FLASK_UI = bool(int(os.getenv('ENABLE_FLASK_UI', '1')))

if __name__ == '__main__':
    debug_mode = os.getenv('DEBUG', 'false').lower() == 'true'
    setup_logger(debug_mode)
    if ENABLE_FLASK_UI:
        # Run Flask UI only (no background job)
        print("Starting Flask UI on http://localhost:5000")
        app.run(debug=debug_mode, port=5000)
    else:
        print("Flask UI is disabled. Running background follow-up job.")
        run_followup_and_report()
