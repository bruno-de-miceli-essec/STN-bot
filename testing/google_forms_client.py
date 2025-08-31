import logging
from typing import List, Dict, Optional
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from config import config

logger = logging.getLogger(__name__)

class GoogleFormsClient:
    def __init__(self):
        """Initialize Google Forms API client with service account credentials."""
        self.service = self._build_service()
    
    def _build_service(self):
        """Build Google Forms API service using service account credentials."""
        try:
            # Load service account credentials from config
            credentials = Credentials.from_service_account_file(
                config.google_service_account_path,
                scopes=['https://www.googleapis.com/auth/forms.responses.readonly']
            )
            
            service = build('forms', 'v1', credentials=credentials)
            logger.info("✅ Google Forms API service initialized successfully")
            return service
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Forms API: {e}")
            raise
    
    def get_form_responses(self, form_id: str) -> List[Dict]:
        """
        Get all responses from a Google Form.
        
        Args:
            form_id: Google Form ID
            
        Returns:
            List of response dictionaries with email and timestamp
        """
        try:
            # Get the form to understand its structure
            form = self.service.forms().get(formId=form_id).execute()
            
            # Get all responses
            responses = self.service.forms().responses().list(formId=form_id).execute()
            
            response_list = []
            
            if 'responses' in responses:
                for response in responses['responses']:
                    response_data = self._extract_response_data(form, response)
                    if response_data:
                        response_list.append(response_data)
            
            logger.info(f"📊 Retrieved {len(response_list)} responses from form {form_id}")
            return response_list
            
        except Exception as e:
            logger.error(f"❌ Failed to get responses for form {form_id}: {e}")
            return []
    
    def _extract_response_data(self, form: Dict, response: Dict) -> Optional[Dict]:
        """
        Extract email and response timestamp from a form response.
        
        Args:
            form: Google Form structure
            response: Individual response data
            
        Returns:
            Dictionary with email and timestamp, or None if email not found
        """
        try:
            # Get response timestamp
            timestamp = response.get('lastSubmittedTime')
            
            # Look for email in the response
            email = self._find_email_in_response(form, response)
            
            if email:
                return {
                    'email': email.lower().strip(),  # Normalize email
                    'timestamp': timestamp,
                    'response_id': response.get('responseId')
                }
            else:
                logger.warning(f"No email found in response {response.get('responseId', 'unknown')}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to extract response data: {e}")
            return None
    
    def _find_email_in_response(self, form: Dict, response: Dict) -> Optional[str]:
        """
        Find email address in form response by checking different possible locations.
        
        Args:
            form: Google Form structure
            response: Individual response data
            
        Returns:
            Email address string or None
        """
        try:
            # Method 1: Check if respondent email collection is enabled
            if 'responderUri' in response:
                # This means the form collects emails automatically
                respondent_email = response.get('respondentEmail')
                if respondent_email:
                    return respondent_email
            
            # Method 2: Look for email questions in the form
            form_items = form.get('items', [])
            answers = response.get('answers', {})
            
            for item in form_items:
                question_id = item.get('questionItem', {}).get('question', {}).get('questionId')
                if not question_id or question_id not in answers:
                    continue
                
                # Check if this question is asking for email
                title = item.get('title', '').lower()
                if any(keyword in title for keyword in ['email', 'e-mail', 'mail', 'adresse']):
                    # Get the answer
                    answer = answers[question_id]
                    if 'textAnswers' in answer:
                        email_answer = answer['textAnswers']['answers'][0]['value']
                        if self._is_valid_email(email_answer):
                            return email_answer
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding email in response: {e}")
            return None
    
    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email.strip()) is not None
    
    def get_multiple_forms_responses(self, form_ids: List[str]) -> Dict[str, List[Dict]]:
        """
        Get responses from multiple Google Forms.
        
        Args:
            form_ids: List of Google Form IDs
            
        Returns:
            Dictionary mapping form_id to list of responses
        """
        all_responses = {}
        
        for form_id in form_ids:
            logger.info(f"📋 Getting responses for form {form_id}")
            responses = self.get_form_responses(form_id)
            all_responses[form_id] = responses
        
        total_responses = sum(len(responses) for responses in all_responses.values())
        logger.info(f"🎯 Total responses retrieved: {total_responses}")
        
        return all_responses
    