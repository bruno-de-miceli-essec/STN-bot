import logging
from typing import List, Dict, Optional, Any
from connections.notion_connection import NotionClient
from connections.messenger_client import MessengerClient
from utils.synchronizer_service import SynchronizerService

logger = logging.getLogger(__name__)

class ReminderService:
    def __init__(self):
        self.notion = NotionClient()
        self.messenger = MessengerClient()
        self.synchronizer = SynchronizerService()
    
    def send_reminders_for_all_forms(self, custom_message: Optional[str] = None, sync_first: bool = True) -> Dict[str, Any]:
        """
        Send reminders for all forms. Returns summary of sync and sent messages.
        
        Args:
            custom_message: Optional custom message template
            sync_first: Whether to synchronize with Google Forms via App Script first
        """
        summary = {"sync_results": None, "reminders": {}}
        
        # Step 1: Synchronize with Google Forms via App Script first (if enabled)
        if sync_first:
            logger.info("🔄 Starting App Script synchronization before sending reminders")
            sync_results = self.synchronizer.synchronize_all_forms()
            summary["sync_results"] = sync_results
            
            # Log sync summary
            total_updated = sum(result.get("updated_count", 0) for result in sync_results.values() 
                              if isinstance(result, dict))
            logger.info(f"✅ App Script synchronization completed: {total_updated} responses updated")
        
        # Step 2: Send reminders based on updated data
        all_non_responders = self.notion.get_all_non_responders()
        
        # Get form details for personalized messages
        all_forms = self.notion.get_all_forms()
        forms_data = {}
        for form in all_forms:
            form_id = form["id"]
            form_name = self.notion.get_property_content(form, self.notion.columns.FORM_NAME)
            google_form_id = self.notion.get_property_content(form, self.notion.columns.GOOGLE_FORM_ID)
            form_url = f"https://docs.google.com/forms/d/{google_form_id}/viewform" if google_form_id else None
            forms_data[form_name] = {
                "date_envoi": self.notion.get_property_content(form, self.notion.columns.DATE_ENVOI),
                "id": form_id,
                "google_form_id": google_form_id,
                "url": form_url
            }
        
        for form_name, people in all_non_responders.items():
            if not people:
                logger.info(f"Form '{form_name}': No reminders needed")
                summary["reminders"][form_name] = 0
                continue
            
            # Get form data for this form
            form_data = forms_data.get(form_name, {})
            
            # Send reminders to each person
            sent_count = 0

            for person_entry in people:
                person = person_entry.get('non_responder', {})
                success = self._send_personalized_reminder(person, form_name, form_data, custom_message)
                if success:
                    sent_count += 1
                    response_id = person_entry.get('ID_reponse')
                    if response_id:
                        self.notion.update_Dernier_rappel(response_id)
            
            summary["reminders"][form_name] = sent_count
            logger.info(f"Form '{form_name}': {sent_count}/{len(people)} reminders sent")
        
        return summary
    
    def send_reminders_for_specific_form(self, form_id: str, custom_message: Optional[str] = None, sync_first: bool = True) -> Dict[str, Any]:
        """
        Send reminders for a specific form. Returns summary with sync and reminder info.
        
        Args:
            form_id: Notion form ID
            custom_message: Optional custom message template
            sync_first: Whether to synchronize with Google Forms via App Script first
        """
        summary = {"sync_result": None, "reminders_sent": 0}
        
        # Get form name and Google Form ID
        form_name = self._get_form_name(form_id)
        
        # Step 1: Synchronize this specific form first (if enabled)
        if sync_first:
            logger.info(f"🔄 Synchronizing form '{form_name}' via App Script before sending reminders")
            
            # Get Google Form ID from Notion
            all_forms = self.notion.get_all_forms()
            google_form_id = None
            for form in all_forms:
                if form["id"] == form_id:
                    google_form_id = self.notion.get_property_content(form, self.notion.columns.GOOGLE_FORM_ID)
                    break
            
            if google_form_id:
                sync_result = self.synchronizer.synchronize_single_form(form_id, google_form_id, form_name)
                summary["sync_result"] = sync_result
                logger.info(f"✅ App Script sync completed: {sync_result.get('updated_count', 0)} responses updated")
            else:
                logger.warning(f"⚠️  No Google Form ID found for '{form_name}', skipping sync")
                summary["sync_result"] = {"status": "skipped", "reason": "No Google Form ID"}
        
        # Step 2: Send reminders based on updated data
        non_responders_raw = self.notion.get_non_responders_for_form(form_id)
        non_responders_list = [d['non_responder'] for d in non_responders_raw if 'non_responder' in d]

        if not non_responders_list:
            logger.info(f"No reminders needed for form '{form_name}'")
            return summary

        # Get form data for personalized messages
        all_forms = self.notion.get_all_forms()
        form_data = {}
        for form in all_forms:
            if form["id"] == form_id:
                google_form_id = self.notion.get_property_content(form, self.notion.columns.GOOGLE_FORM_ID)
                form_data = {
                    "date_envoi": self.notion.get_property_content(form, self.notion.columns.DATE_ENVOI),
                    "id": form_id,
                    "google_form_id": google_form_id,
                    "url": f"https://docs.google.com/forms/d/{google_form_id}/viewform" if google_form_id else None
                }
                break

        sent_count = 0

        for non_responder in non_responders_raw:
            person = non_responder.get('non_responder', {})
            response_id = non_responder.get('ID_reponse')
            name_person = non_responder.get('Name_person')

            success = self._send_personalized_reminder(person, form_name, form_data, custom_message)
            if success:
                sent_count += 1
            success_b = self.notion.update_Dernier_rappel(response_id) if response_id else False
            if success_b:
                logger.info(f"✅ Updated 'Dernier Rappel' for response '{name_person}' in Notion")

        summary["reminders_sent"] = sent_count
        logger.info(f"Sent {sent_count}/{len(non_responders_list)} reminders for form '{form_name}'")
        return summary
    
    def sync_only_all_forms(self) -> Dict[str, Dict]:
        """
        Only synchronize all forms via App Script without sending reminders.
        Useful for webhook-triggered sync operations.
        """
        logger.info("🔄 Starting sync-only operation for all forms via App Script")
        return self.synchronizer.synchronize_all_forms()
    
    def sync_only_specific_form(self, form_id: str) -> Dict:
        """
        Only synchronize a specific form via App Script without sending reminders.
        Useful for webhook-triggered sync operations.
        """
        # Get form details
        form_name = self._get_form_name(form_id)
        all_forms = self.notion.get_all_forms()
        google_form_id = None
        
        for form in all_forms:
            if form["id"] == form_id:
                google_form_id = self.notion.get_property_content(form, self.notion.columns.GOOGLE_FORM_ID)
                break
        
        if not google_form_id:
            logger.warning(f"⚠️  No Google Form ID found for '{form_name}'")
            return {"status": "error", "error": "No Google Form ID found"}
        
        logger.info(f"🔄 Starting sync-only operation for form '{form_name}' via App Script")
        return self.synchronizer.synchronize_single_form(form_id, google_form_id, form_name)
    
    def _send_personalized_reminder(self, person: dict, form_name: str, form_data: dict, custom_message: Optional[str] = None) -> bool:
        """Send personalized reminder to a specific person."""
        name = self.notion.get_property_content(person, self.notion.columns.PERSON_NAME)
        psid = self.notion.get_property_content(person, self.notion.columns.PERSON_PSID)
        date_envoi = form_data.get("date_envoi", "N/A")
        
        if not psid:
            logger.warning(f"No PSID found for {name}")
            return False
        
        # Create personalized message
        if custom_message:
            message = custom_message
        else:
            # Build personalized message
            message = f"Hello {name},\n\nPetit rappel pour remplir le formulaire *{form_name}*, diffusé le {date_envoi}."
            
            # Add form link if available
            if form_data.get("url"):
                message += f"\n\n Lien du formulaire 👉👉 {form_data['url']}."
            
            message += "\n\nBien à toi,\nLa bise Santana"
        
        success = self.messenger.send_message(psid, message)
        if success:
            logger.info(f"✅ Personalized reminder sent to {name}")
        else:
            logger.error(f"❌ Failed to send personalized reminder to {name}")
        return success
    
    def _send_reminder_to_person(self, person: dict, message: str) -> bool:
        """Send reminder to a specific person (legacy method for backward compatibility)."""
        name = self.notion.get_property_content(person, self.notion.columns.PERSON_NAME)
        psid = self.notion.get_property_content(person, self.notion.columns.PERSON_PSID)
        
        if not psid:
            logger.warning(f"No PSID found for {name}")
            return False
        
        success = self.messenger.send_message(psid, message)
        if success:
            logger.info(f"✅ Reminder sent to {name}")
        else:
            logger.error(f"❌ Failed to send reminder to {name}")
        
        return success
    
    def _get_form_name(self, form_id: str) -> str:
        """Get form name by ID."""
        all_forms = self.notion.get_all_forms()
        for form in all_forms:
            if form["id"] == form_id:
                return self.notion.get_property_content(form, self.notion.columns.FORM_NAME)
        return "Unknown Form"
    
    def get_summary_report(self, include_sync_report: bool = True) -> str:
        """
        Get a comprehensive summary of all forms, their sync status, and non-responder counts.
        
        Args:
            include_sync_report: Whether to include Google Forms App Script sync information
        """
        report = "📊 COMPREHENSIVE REMINDER & SYNC REPORT (APP SCRIPT)\n"
        report += "=" * 55 + "\n\n"
        
        # Sync report section
        if include_sync_report:
            sync_report = self.synchronizer.get_sync_report()
            report += sync_report + "\n\n"
            report += "=" * 55 + "\n\n"
        
        # Reminder report section
        all_non_responders = self.notion.get_all_non_responders()
        
        report += "📋 REMINDER STATUS:\n\n"
        
        total_people = 0
        for form_name, people in all_non_responders.items():
            count = len(people)
            total_people += count
            
            if count > 0:
                report += f"📋 {form_name}: {count} people need reminders\n"
                for person in people:
                    name = self.notion.get_property_content(person, self.notion.columns.PERSON_NAME)
                    email = self.notion.get_property_content(person, self.notion.columns.PERSON_EMAIL)
                    report += f"   • {name}"
                    if email:
                        report += f" ({email})"
                    report += "\n"
                report += "\n"
            else:
                report += f"✅ {form_name}: All responses received\n\n"
        
        report += f"🎯 TOTAL REMINDERS NEEDED: {total_people} across all forms\n\n"
        
        # Instructions section
        report += "💡 NEXT STEPS:\n"
        report += "1. Run sync to update response statuses from Google Forms via App Script\n"
        report += "2. Send personalized reminders to remaining non-responders\n"
        report += "3. Monitor webhook endpoints for automated triggers\n\n"
        
        # App Script specific notes
        report += "🔗 APP SCRIPT NOTES:\n"
        report += "• Make sure your App Script is deployed as a web app\n"
        report += "• Forms must be shared with the App Script owner\n"
        report += "• Email collection must be enabled in your Google Forms\n"
        report += "• Personalized messages include: name, form name, date, and direct link\n"
        
        return report
    
    def test_app_script_connection(self) -> Dict[str, Any]:
        """
        Test the App Script connection with all configured forms.
        
        Returns:
            Dictionary with test results for each form
        """
        logger.info("🧪 Testing App Script connection for all forms")
        
        notion_forms = self.notion.get_all_forms()
        test_results = {}
        
        for form in notion_forms:
            form_name = self.notion.get_property_content(form, self.notion.columns.FORM_NAME)
            google_form_id = self.notion.get_property_content(form, self.notion.columns.GOOGLE_FORM_ID)
            
            if not google_form_id:
                test_results[form_name] = {
                    "status": "skipped",
                    "reason": "No Google Form ID"
                }
                continue
            
            # Test App Script access
            try:
                responses = self.synchronizer.google_forms.get_form_responses(google_form_id)
                test_results[form_name] = {
                    "status": "success",
                    "google_form_id": google_form_id,
                    "responses_found": len(responses),
                    "emails_found": len([r for r in responses if r.get('email')])
                }
                logger.info(f"✅ Form '{form_name}': {len(responses)} responses accessible")
                
            except Exception as e:
                test_results[form_name] = {
                    "status": "error",
                    "google_form_id": google_form_id,
                    "error": str(e)
                }
                logger.error(f"❌ Form '{form_name}': {e}")
        
        return test_results
