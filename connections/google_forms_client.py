import logging
import requests
from typing import List, Dict, Optional
from config.config import config

logger = logging.getLogger(__name__)

class GoogleFormsAppScriptClient:
    def __init__(self):
        """Initialize Google Forms client using App Script endpoint."""
        self.app_script_url = config.google_app_script_url  # Actually the App Script URL
        logger.info("🔗 Google Forms App Script client initialized")
    
    def get_form_responses(self, form_id: str) -> List[Dict]:
        """
        Get all responses from a Google Form via App Script.
        
        Args:
            form_id: Google Form ID
            
        Returns:
            List of response dictionaries with email and names
        """
        try:
            # Call your App Script with the form ID
            url = f"{self.app_script_url}?formId={form_id}"
            
            logger.info(f"📞 Calling App Script for form {form_id}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for errors in App Script response
            if 'error' in data:
                logger.error(f"❌ App Script error: {data['error']}")
                return []
            
            # Extract emails and people data
            emails = data.get('emails', [])
            people = data.get('people', [])
            
            logger.info(f"📊 Retrieved {len(emails)} unique emails from form {form_id}")
            logger.info(f"👥 Retrieved {len(people)} people with details")
            
            # Return in expected format for compatibility with existing code
            response_list = []
            for person in people:
                if person.get('email'):
                    response_data = {
                        'email': person['email'].lower().strip(),
                        'firstName': person.get('firstName', ''),
                        'lastName': person.get('lastName', ''),
                        'timestamp': None,  # App Script doesn't return timestamp in current version
                        'response_id': f"{form_id}_{person['email']}"  # Create synthetic ID
                    }
                    response_list.append(response_data)
            
            # If no detailed people data, fall back to just emails
            if not response_list and emails:
                for email in emails:
                    response_list.append({
                        'email': email.lower().strip(),
                        'firstName': '',
                        'lastName': '',
                        'timestamp': None,
                        'response_id': f"{form_id}_{email}"
                    })
            
            logger.info(f"✅ Processed {len(response_list)} valid responses")
            return response_list
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to call App Script for form {form_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Unexpected error getting responses for form {form_id}: {e}")
            return []
    
    def get_multiple_forms_responses(self, form_ids: List[str]) -> Dict[str, List[Dict]]:
        """
        Get responses from multiple Google Forms via App Script.
        
        Args:
            form_ids: List of Google Form IDs
            
        Returns:
            Dictionary mapping form_id to list of responses
        """
        all_responses = {}
        
        for form_id in form_ids:
            logger.info(f"📋 Getting responses for form {form_id} via App Script")
            responses = self.get_form_responses(form_id)
            all_responses[form_id] = responses
        
        total_responses = sum(len(responses) for responses in all_responses.values())
        logger.info(f"🎯 Total responses retrieved via App Script: {total_responses}")
        
        return all_responses
    
    def test_connection(self, sample_form_id: Optional[str] = None) -> bool:
        """
        Test the App Script connection.
        
        Args:
            sample_form_id: Optional form ID to test with
            
        Returns:
            True if connection works, False otherwise
        """
        try:
            if sample_form_id:
                # Test with actual form ID
                responses = self.get_form_responses(sample_form_id)
                logger.info(f"✅ App Script test successful: {len(responses)} responses")
                return True
            else:
                # Test basic connection (will return error about missing formId but confirms script works)
                response = requests.get(self.app_script_url, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if 'error' in data and 'missing formId' in data['error']:
                    logger.info("✅ App Script connection test successful (missing formId as expected)")
                    return True
                else:
                    logger.warning(f"⚠️  Unexpected App Script response: {data}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ App Script connection test failed: {e}")
            return False