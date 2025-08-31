import logging
from typing import List, Dict, Set
from notion_connection import NotionClient
from google_forms_client import GoogleFormsClient
from config import config
import requests

logger = logging.getLogger(__name__)

class SynchronizerService:
    def __init__(self):
        self.notion = NotionClient()
        self.google_forms = GoogleFormsClient()
    
    def synchronize_all_forms(self) -> Dict[str, Dict]:
        """
        Synchronize all forms by updating Notion responses based on Google Forms data.
        
        Returns:
            Summary dictionary with sync results for each form
        """
        logger.info("🔄 Starting full synchronization process")
        
        # Get all forms from Notion
        notion_forms = self.notion.get_all_forms()
        sync_summary = {}
        
        for form in notion_forms:
            form_id = form["id"]
            form_name = self.notion.get_property_content(form, self.notion.columns.FORM_NAME)
            
            # Get Google Form ID from Notion form (you'll need to add this field)
            google_form_id = self.notion.get_property_content(form, "Google Form ID")
            
            if not google_form_id:
                logger.warning(f"⚠️  No Google Form ID found for '{form_name}', skipping")
                sync_summary[form_name] = {"status": "skipped", "reason": "No Google Form ID"}
                continue
            
            # Synchronize this specific form
            result = self.synchronize_single_form(form_id, google_form_id, form_name)
            sync_summary[form_name] = result
        
        logger.info(f"✅ Synchronization completed for {len(sync_summary)} forms")
        return sync_summary
    
    def synchronize_single_form(self, notion_form_id: str, google_form_id: str, form_name: str) -> Dict:
        """
        Synchronize a single form between Google Forms and Notion.
        
        Args:
            notion_form_id: Notion form page ID
            google_form_id: Google Form ID
            form_name: Name of the form for logging
            
        Returns:
            Dictionary with sync results
        """
        logger.info(f"🔄 Synchronizing form '{form_name}'")
        
        try:
            # Step 1: Get Google Forms responses
            google_responses = self.google_forms.get_form_responses(google_form_id)
            google_emails = {resp['email'] for resp in google_responses}
            
            logger.info(f"📊 Found {len(google_emails)} unique email responses in Google Form")
            
            # Step 2: Get Notion responses for this form
            notion_responses = self.notion.get_responses_for_form(notion_form_id)
            
            # Step 3: Compare and update
            updated_count = 0
            
            for response in notion_responses:
                # Get person data for this response
                person_ids = self.notion.get_relation_ids(response, self.notion.columns.PERSON_RELATION)
                
                if not person_ids:
                    logger.warning(f"No person relation found for response {response['id']}")
                    continue
                
                person = self.notion.get_person_by_id(person_ids[0])
                if not person:
                    continue
                
                # Get person's email
                person_email = self.notion.get_property_content(person, "Email")  # You'll need this field
                
                if not person_email:
                    logger.warning(f"No email found for person in response {response['id']}")
                    continue
                
                # Check if this email has responded in Google Forms
                person_email_normalized = person_email.lower().strip()
                has_responded_google = person_email_normalized in google_emails
                has_responded_notion = self.notion.get_checkbox_value(response, self.notion.columns.HAS_RESPONDED)
                
                # Update if status doesn't match
                if has_responded_google and not has_responded_notion:
                    success = self.notion.update_response_status(response['id'], True)
                    if success:
                        updated_count += 1
                        logger.info(f"✅ Updated response status for {person_email}")
                    else:
                        logger.error(f"❌ Failed to update response status for {person_email}")
            
            result = {
                "status": "success",
                "google_responses": len(google_responses),
                "notion_responses": len(notion_responses),
                "updated_count": updated_count
            }
            
            logger.info(f"✅ Form '{form_name}': {updated_count} responses updated")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to synchronize form '{form_name}': {e}")
            return {"status": "error", "error": str(e)}
    
    def get_sync_report(self) -> str:
        """Get a detailed synchronization report without actually syncing."""
        logger.info("📊 Generating synchronization report")
        
        notion_forms = self.notion.get_all_forms()
        
        report = "🔄 SYNCHRONIZATION REPORT\n"
        report += "=" * 40 + "\n\n"
        
        total_forms = len(notion_forms)
        forms_with_google_id = 0
        
        for form in notion_forms:
            form_name = self.notion.get_property_content(form, self.notion.columns.FORM_NAME)
            google_form_id = self.notion.get_property_content(form, "Google Form ID")
            
            if google_form_id:
                forms_with_google_id += 1
                report += f"✅ {form_name}\n"
                report += f"   Google Form ID: {google_form_id}\n"
                
                # Get response counts
                notion_responses = self.notion.get_responses_for_form(form["id"])
                responded_count = sum(1 for r in notion_responses 
                                    if self.notion.get_checkbox_value(r, self.notion.columns.HAS_RESPONDED))
                
                report += f"   Notion responses: {len(notion_responses)} ({responded_count} marked as responded)\n\n"
            else:
                report += f"⚠️  {form_name}\n"
                report += f"   Missing Google Form ID - will be skipped\n\n"
        
        report += f"📊 SUMMARY:\n"
        report += f"Total forms: {total_forms}\n"
        report += f"Ready for sync: {forms_with_google_id}\n"
        report += f"Missing Google ID: {total_forms - forms_with_google_id}\n"
        
        return report