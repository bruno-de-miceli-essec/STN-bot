import logging
from typing import List, Dict, Set
from connections.notion_connection import NotionClient
from connections.google_forms_client import GoogleFormsAppScriptClient
from config import config

logger = logging.getLogger(__name__)

class SynchronizerService:
    def __init__(self):
        self.notion = NotionClient()
        self.google_forms = GoogleFormsAppScriptClient()
    
    def synchronize_all_forms(self) -> Dict[str, Dict]:
        """
        Synchronize all forms by updating Notion responses based on Google Forms data via App Script.
        
        Returns:
            Summary dictionary with sync results for each form
        """
        logger.info("🔄 Starting full synchronization process via App Script")
        
        # Get all forms from Notion
        notion_forms = self.notion.get_all_forms()
        sync_summary = {}
        
        for form in notion_forms:
            form_id = form["id"]
            form_name = self.notion.get_property_content(form, self.notion.columns.FORM_NAME)
            
            # Get Google Form ID from Notion form
            google_form_id = self.notion.get_property_content(form, self.notion.columns.GOOGLE_FORM_ID)
            
            if not google_form_id:
                logger.warning(f"⚠️  No Google Form ID found for '{form_name}', skipping")
                sync_summary[form_name] = {"status": "skipped", "reason": "No Google Form ID"}
                continue
            
            # Synchronize this specific form
            result = self.synchronize_single_form(form_id, google_form_id, form_name)
            sync_summary[form_name] = result
        
        logger.info(f"✅ Synchronization completed for {len(sync_summary)} forms via App Script")
        return sync_summary
    
    def synchronize_single_form(self, notion_form_id: str, google_form_id: str, form_name: str) -> Dict:
        """
        Synchronize a single form between Google Forms (via App Script) and Notion.
        
        Args:
            notion_form_id: Notion form page ID
            google_form_id: Google Form ID
            form_name: Name of the form for logging
            
        Returns:
            Dictionary with sync results
        """
        logger.info(f"🔄 Synchronizing form '{form_name}' via App Script")
        
        try:
            # Step 1: Get Google Forms responses via App Script
            google_responses = self.google_forms.get_form_responses(google_form_id)
            google_emails = {resp['email'] for resp in google_responses if resp.get('email')}
            
            logger.info(f"📊 Found {len(google_emails)} unique email responses in Google Form via App Script")
            
            if not google_emails:
                logger.warning(f"⚠️  No email responses found for form '{form_name}' - check if email collection is enabled")
                return {
                    "status": "warning",
                    "google_responses": 0,
                    "notion_responses": 0,
                    "updated_count": 0,
                    "message": "No emails found in Google Form responses"
                }
            
            # Step 2: Get Notion responses for this form
            notion_responses = self.notion.get_responses_for_form(notion_form_id)
            
            logger.info(f"📊 Found {len(notion_responses)} responses in Notion for this form")
            
            # Step 3: Compare and update
            updated_count = 0
            people_checked = 0
            
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
                person_email = self.notion.get_property_content(person, self.notion.columns.PERSON_EMAIL)
                
                if not person_email:
                    person_name = self.notion.get_property_content(person, self.notion.columns.PERSON_NAME)
                    logger.warning(f"No email found for person '{person_name}' in response {response['id']}")
                    continue
                
                people_checked += 1
                
                # Check if this email has responded in Google Forms
                person_email_normalized = person_email.lower().strip()
                has_responded_google = person_email_normalized in google_emails
                has_responded_notion = self.notion.get_checkbox_value(response, self.notion.columns.HAS_RESPONDED)
                
                # Update if status doesn't match
                if has_responded_google and not has_responded_notion:
                    success = self.notion.update_response_status(response['id'], True)
                    if success:
                        updated_count += 1
                        person_name = self.notion.get_property_content(person, self.notion.columns.PERSON_NAME)
                        logger.info(f"✅ Updated response status for {person_name} ({person_email})")
                    else:
                        logger.error(f"❌ Failed to update response status for {person_email}")
                elif has_responded_google and has_responded_notion:
                    logger.debug(f"✓ {person_email} already marked as responded")
                elif not has_responded_google and not has_responded_notion:
                    logger.debug(f"- {person_email} still needs to respond")
                elif not has_responded_google and has_responded_notion:
                    logger.warning(f"⚠️  {person_email} marked as responded in Notion but not found in Google Forms")
            
            result = {
                "status": "success",
                "google_responses": len(google_responses),
                "notion_responses": len(notion_responses),
                "people_checked": people_checked,
                "updated_count": updated_count
            }
            
            logger.info(f"✅ Form '{form_name}': {updated_count} responses updated ({people_checked} people checked)")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to synchronize form '{form_name}' via App Script: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_sync_report(self) -> str:
        """Get a detailed synchronization report without actually syncing."""
        logger.info("📊 Generating synchronization report for App Script integration")
        
        notion_forms = self.notion.get_all_forms()
        
        report = "🔄 APP SCRIPT SYNCHRONIZATION REPORT\n"
        report += "=" * 45 + "\n\n"
        
        total_forms = len(notion_forms)
        forms_with_google_id = 0
        
        for form in notion_forms:
            form_name = self.notion.get_property_content(form, self.notion.columns.FORM_NAME)
            google_form_id = self.notion.get_property_content(form, self.notion.columns.GOOGLE_FORM_ID)
            
            if google_form_id:
                forms_with_google_id += 1
                report += f"✅ {form_name}\n"
                report += f"   Google Form ID: {google_form_id}\n"
                
                # Test App Script connection for this form
                test_result = self._test_form_access(google_form_id)
                if test_result["accessible"]:
                    report += f"   App Script access: ✅ OK ({test_result.get('email_count', 0)} emails found)\n"
                else:
                    report += f"   App Script access: ❌ {test_result.get('error', 'Unknown error')}\n"
                
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
        report += f"Missing Google ID: {total_forms - forms_with_google_id}\n\n"
        
        # App Script specific info
        report += f"🔗 App Script URL: {self.google_forms.app_script_url}\n"
        report += f"💡 Make sure your App Script is deployed and forms are shared with the script owner\n"
        
        return report
    
    def _test_form_access(self, google_form_id: str) -> Dict:
        """Test if a specific form is accessible via App Script."""
        try:
            responses = self.google_forms.get_form_responses(google_form_id)
            return {
                "accessible": True,
                "email_count": len(responses)
            }
        except Exception as e:
            return {
                "accessible": False,
                "error": str(e)
            }