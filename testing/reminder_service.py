import logging
from typing import List, Dict, Optional, Any
from notion_connection import NotionClient
from messenger_client import MessengerClient
from synchronizer_service import SynchronizerService

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
            sync_first: Whether to synchronize with Google Forms first
        """
        summary = {"sync_results": None, "reminders": {}}
        
        # Step 1: Synchronize with Google Forms first (if enabled)
        if sync_first:
            logger.info("🔄 Starting synchronization before sending reminders")
            sync_results = self.synchronizer.synchronize_all_forms()
            summary["sync_results"] = sync_results
            
            # Log sync summary
            total_updated = sum(result.get("updated_count", 0) for result in sync_results.values() 
                              if isinstance(result, dict))
            logger.info(f"✅ Synchronization completed: {total_updated} responses updated")
        
        # Step 2: Send reminders based on updated data
        all_non_responders = self.notion.get_all_non_responders()
        
        for form_name, people in all_non_responders.items():
            if not people:
                logger.info(f"Form '{form_name}': No reminders needed")
                summary["reminders"][form_name] = 0
                continue
            
            # Send reminders to each person
            sent_count = 0
            message = custom_message or f"Hello! Petit rappel pour remplir le formulaire '{form_name}' 😉"
            
            for person in people:
                success = self._send_reminder_to_person(person, message)
                if success:
                    sent_count += 1
            
            summary["reminders"][form_name] = sent_count
            logger.info(f"Form '{form_name}': {sent_count}/{len(people)} reminders sent")
        
        return summary
    
    def send_reminders_for_specific_form(self, form_id: str, custom_message: Optional[str] = None, sync_first: bool = True) -> Dict[str, Any]:
        """
        Send reminders for a specific form. Returns summary with sync and reminder info.
        
        Args:
            form_id: Notion form ID
            custom_message: Optional custom message template
            sync_first: Whether to synchronize with Google Forms first
        """
        summary = {"sync_result": None, "reminders_sent": 0}
        
        # Get form name and Google Form ID
        form_name = self._get_form_name(form_id)
        
        # Step 1: Synchronize this specific form first (if enabled)
        if sync_first:
            logger.info(f"🔄 Synchronizing form '{form_name}' before sending reminders")
            
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
                logger.info(f"✅ Sync completed: {sync_result.get('updated_count', 0)} responses updated")
            else:
                logger.warning(f"⚠️  No Google Form ID found for '{form_name}', skipping sync")
                summary["sync_result"] = {"status": "skipped", "reason": "No Google Form ID"}
        
        # Step 2: Send reminders based on updated data
        non_responders = self.notion.get_non_responders_for_form(form_id)
        
        if not non_responders:
            logger.info(f"No reminders needed for form '{form_name}'")
            return summary
        
        message = custom_message or f"Hello! Petit rappel pour remplir le formulaire '{form_name}' 😉"
        
        sent_count = 0
        for person in non_responders:
            success = self._send_reminder_to_person(person, message)
            if success:
                sent_count += 1
        
        summary["reminders_sent"] = sent_count
        logger.info(f"Sent {sent_count}/{len(non_responders)} reminders for form '{form_name}'")
        return summary
    
    def sync_only_all_forms(self) -> Dict[str, Dict]:
        """
        Only synchronize all forms without sending reminders.
        Useful for webhook-triggered sync operations.
        """
        logger.info("🔄 Starting sync-only operation for all forms")
        return self.synchronizer.synchronize_all_forms()
    
    def sync_only_specific_form(self, form_id: str) -> Dict:
        """
        Only synchronize a specific form without sending reminders.
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
        
        logger.info(f"🔄 Starting sync-only operation for form '{form_name}'")
        return self.synchronizer.synchronize_single_form(form_id, google_form_id, form_name)
    
    def _send_reminder_to_person(self, person: dict, message: str) -> bool:
        """Send reminder to a specific person."""
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
            include_sync_report: Whether to include Google Forms sync information
        """
        report = "📊 COMPREHENSIVE REMINDER & SYNC REPORT\n"
        report += "=" * 50 + "\n\n"
        
        # Sync report section
        if include_sync_report:
            sync_report = self.synchronizer.get_sync_report()
            report += sync_report + "\n\n"
            report += "=" * 50 + "\n\n"
        
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
        report += "1. Run sync to update response statuses from Google Forms\n"
        report += "2. Send reminders to remaining non-responders\n"
        report += "3. Monitor webhook endpoints for automated triggers\n"
        
        return report