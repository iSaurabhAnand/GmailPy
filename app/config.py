import os

# Configurable follow-up templates (2 lines each)
FOLLOWUP_TEMPLATES = [
    os.getenv('FOLLOWUP_TEMPLATE_1', "Just checking in to see if you had a chance to review my previous email.\nLet me know if you need anything from me."),
    os.getenv('FOLLOWUP_TEMPLATE_2', "Wanted to follow up on my last message.\nPlease let me know if you have any questions."),
    os.getenv('FOLLOWUP_TEMPLATE_3', "Hope you're well!\nJust following up regarding my earlier email.")
]

# Configurable constants
MIN_DAYS = int(os.getenv('MIN_DAYS', 2))
MAX_DAYS = int(os.getenv('MAX_DAYS', 30))
BATCH_SIZE = int(os.getenv('BATCH_SIZE', 20))
MAX_FOLLOW_UPS = int(os.getenv('MAX_FOLLOW_UPS', 3))

# Flag to disable sending follow-up emails
DISABLE_SEND_FOLLOWUP = bool(int(os.getenv('DISABLE_SEND_FOLLOWUP', '0')))