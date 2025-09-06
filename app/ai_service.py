import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        """Initialize OpenAI client with API key from environment."""
        logger.debug("Initializing AIService")
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("OPENAI_API_KEY environment variable not set")
            raise ValueError("OPENAI_API_KEY environment variable not set")
        self.client = OpenAI(api_key=api_key)
        logger.debug("AIService initialized successfully")

    def analyze_thread_urgency(self, thread_content, days_since_sent):
        """Analyze if a job-related email thread needs follow-up."""
        logger.debug(f"Analyzing thread urgency for content from {days_since_sent} days ago")
        
        prompt = f"""
        Analyze this email thread for job-seeking context and determine if it needs a follow-up.
        Thread Content: {thread_content}
        Days Since Sent: {days_since_sent}

        Rules:
        1. Only recommend follow-up if the thread is about:
           - Job applications
           - Interview follow-ups
           - Networking for job opportunities
           - Recruiter communications
        2. Consider timing:
           - 3-5 days for interview follow-ups
           - 7-10 days for applications
           - 14+ days for general networking
        
        Return a JSON object:
        {{
            "needs_followup": true/false,
            "reason": "Clear explanation of why follow-up is needed or not needed",
            "urgency": "low/medium/high",
            "context": "job_application/interview/networking/other",
            "original_role": "The job role/title discussed"
        }}

        Return needs_followup=false if:
        1. Not job-related
        2. Already received a definitive response
        3. Company explicitly asked not to follow up
        """
        
        try:
            logger.debug("Sending request to OpenAI API for thread analysis")
            response = self.client.chat.completions.create(
                model="gpt-5-nano",
                messages=[{"role": "user", "content": prompt}]
            )
            result = response.choices[0].message.content
            logger.debug(f"Received analysis from OpenAI: {result}")
            return result
        except Exception as e:
            logger.error(f"Error analyzing thread urgency: {str(e)}")
            raise

    def generate_followup_email(self, original_thread, recipient_name, last_email_content, days_since_sent):
        """Generate a job-seeking follow-up email."""
        logger.debug(f"Generating follow-up email for recipient: {recipient_name}, days since sent: {days_since_sent}")
        
        prompt = f"""
        Generate a concise, professional follow-up email for a job seeker.

        Context:
        - Original Thread: {original_thread}
        - Recipient Name: {recipient_name}
        - Last Email: {last_email_content}
        - Days Since Sent: {days_since_sent}

        Requirements:
        1. Keep it short (2-3 sentences maximum)
        2. Be specific about the previous interaction
        3. Include the job role/title
        4. End with a clear next step
        5. Be confident but not pushy

        Format:
        Subject: Re: [Original Subject]

        Hi [Use actual name, no placeholders],

        [One sentence referencing specific previous interaction]
        [One sentence expressing continued interest]
        [One sentence with clear call to action]

        Best regards,
        [Sender name will be added automatically]

        Example:
        Hi John,
        I wanted to follow up on my application for the Senior Developer position we discussed last week. I remain very interested in the role and would appreciate any updates on the hiring process. Would it be possible to schedule a brief call this week to discuss next steps?

        Best regards,
        [Name]
        """
        
        try:
            logger.debug("Sending request to OpenAI API for email generation")
            response = self.client.chat.completions.create(
                model="gpt-5-nano",
                messages=[{"role": "user", "content": prompt}]
            )
            result = response.choices[0].message.content
            logger.debug(f"Generated follow-up email: {result}")
            return result
        except Exception as e:
            logger.error(f"Error generating follow-up email: {str(e)}")
            raise
