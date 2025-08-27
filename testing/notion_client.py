import requests
import logging
from typing import List, Dict, Optional
from config import config

logger = logging.getLogger(__name__)

class NotionColumns:
    """Centralized column name management - single source of truth"""
    
    # Forms database columns
    FORM_NAME = "Nom du formulaire"
    
    # Responses database columns  
    FORMS_RELATION = "Forms"
    PERSON_RELATION = "Person"
    HAS_RESPONDED = "A répondu"
    
    # People database columns
    PERSON_NAME = "Prénom & Nom"
    PERSON_PSID = "PSID"
    
    @classmethod
    def validate_property_exists(cls, page: Dict, property_name: str) -> bool:
        """Check if a property exists in a Notion page"""
        return property_name in page.get("properties", {})

class NotionClient:
    def __init__(self):
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {config.notion_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        self.columns = NotionColumns()
    
    def get_database_entries(self, database_id: str) -> List[Dict]:
        """Fetch all entries from a Notion database."""
        url = f"{self.base_url}/databases/{database_id}/query"
        
        try:
            response = requests.post(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch database entries: {e}")
            return []
    
    def get_property_content(self, page: Dict, property_name: str) -> str:
        """Extract content from a Notion page property."""
        try:
            if not self.columns.validate_property_exists(page, property_name):
                logger.warning(f"Property '{property_name}' does not exist in page")
                return ""
            
            property_data = page["properties"][property_name]
            property_type = property_data["type"]
            content_value = property_data[property_type]
            
            if property_type == "rich_text" and content_value:
                return content_value[0]["plain_text"]
            elif property_type == "title" and content_value:
                return content_value[0]["plain_text"]
            
            return ""
        except (KeyError, IndexError, TypeError) as e:
            logger.warning(f"Could not extract content for property '{property_name}': {e}")
            return ""
    
    def get_checkbox_value(self, page: Dict, property_name: str) -> bool:
        """Extract boolean value from a checkbox property."""
        try:
            if not self.columns.validate_property_exists(page, property_name):
                logger.warning(f"Checkbox property '{property_name}' does not exist")
                return False
            
            property_data = page["properties"][property_name]
            if property_data["type"] != "checkbox":
                logger.error(f"Property '{property_name}' is not a checkbox")
                return False
            
            return property_data["checkbox"]
        
        except (KeyError, TypeError) as e:
            logger.warning(f"Could not extract checkbox value for '{property_name}': {e}")
            return False
    
    def get_relation_ids(self, page: Dict, property_name: str) -> List[str]:
        """Extract list of related page IDs from a relation property."""
        try:
            if not self.columns.validate_property_exists(page, property_name):
                logger.warning(f"Relation property '{property_name}' does not exist")
                return []
            
            property_data = page["properties"][property_name]
            if property_data["type"] != "relation":
                logger.error(f"Property '{property_name}' is not a relation")
                return []
            
            relation_data = property_data["relation"]
            return [item["id"] for item in relation_data]
        
        except (KeyError, TypeError) as e:
            logger.warning(f"Could not extract relation IDs for '{property_name}': {e}")
            return []
    
    def get_all_forms(self) -> List[Dict]:
        """Get all forms from the forms database."""
        return self.get_database_entries(config.notion_forms_db_id)
    
    def get_responses_for_form(self, form_id: str) -> List[Dict]:
        """Get all responses that are related to a specific form."""
        all_responses = self.get_database_entries(config.notion_responses_db_id)
        
        form_responses = []
        for response in all_responses:
            # Get the form IDs this response is related to
            related_form_ids = self.get_relation_ids(response, self.columns.FORMS_RELATION)
            
            # Check if our form_id is in the relations
            if form_id in related_form_ids:
                form_responses.append(response)
        
        logger.info(f"Found {len(form_responses)} responses for form {form_id}")
        return form_responses
    
    def get_non_responders_for_form(self, form_id: str) -> List[Dict]:
        """Get list of people who haven't responded to a specific form."""
        responses = self.get_responses_for_form(form_id)
        
        non_responders = []
        for response in responses:
            # Check if "A répondu" checkbox is unchecked
            has_responded = self.get_checkbox_value(response, self.columns.HAS_RESPONDED)
            
            if not has_responded:
                # Get the person related to this response
                person_ids = self.get_relation_ids(response, self.columns.PERSON_RELATION)
                
                if person_ids:
                    # Get the actual person data
                    person_id = person_ids[0]  # Assuming one person per response
                    person = self.get_person_by_id(person_id)
                    if person:
                        non_responders.append(person)
                
        logger.info(f"Found {len(non_responders)} non-responders for form {form_id}")
        return non_responders
    
    def get_person_by_id(self, person_id: str) -> Optional[Dict]:
        """Get a person's data by their Notion page ID."""
        url = f"{self.base_url}/pages/{person_id}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch person {person_id}: {e}")
            return None
    
    def get_all_non_responders(self) -> Dict[str, List[Dict]]:
        """Get non-responders for ALL forms. Returns dict: {form_name: [non_responders]}"""
        all_forms = self.get_all_forms()
        results = {}
        
        for form in all_forms:
            form_id = form["id"]
            form_name = self.get_property_content(form, self.columns.FORM_NAME)
            
            if not form_name:
                logger.warning(f"Form {form_id} has no name, skipping")
                continue
            
            non_responders = self.get_non_responders_for_form(form_id)
            results[form_name] = non_responders
            
            logger.info(f"Form '{form_name}': {len(non_responders)} non-responders")
        
        return results