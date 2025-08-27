import logging
from typing import List, Dict
from notion_client import NotionClient
from messenger_client import MessengerClient

logger = logging.getLogger(__name__)

class ReminderService:
    def __init__(self):
        self.notion = NotionClient()
        self.messenger = MessengerClient()
    
    def send_reminders_for_all_forms(self, custom_message: str = None) -> Dict[str, int]:
        """Send reminders for all forms. Returns summary of sent messages."""
        all_non_responders = self.notion.get_all_non_responders()
        summary = {}
        
        for form_name, people in all_non_responders.items():
            if not people:
                logger.info(f"Form '{form_name}': No reminders needed")
                summary[form_name] = 0
                continue
            
            # Send reminders to each person
            sent_count = 0
            message = custom_message or f"Hello! Petit rappel pour remplir le formulaire '{form_name}' 😉"
            
            for person in people:
                success = self._send_reminder_to_person(person, message)
                if success:
                    sent_count += 1
            
            summary[form_name] = sent_count
            logger.info(f"Form '{form_name}': {sent_count}/{len(people)} reminders sent")
        
        return summary
    
    def send_reminders_for_specific_form(self, form_id: str, custom_message: str = None) -> int:
        """Send reminders for a specific form. Returns number of messages sent."""
        non_responders = self.notion.get_non_responders_for_form(form_id)
        
        if not non_responders:
            logger.info(f"No reminders needed for form {form_id}")
            return 0
        
        # Get form name for the message
        form_name = self._get_form_name(form_id)
        message = custom_message or f"Hello! Petit rappel pour remplir le formulaire '{form_name}' 😉"
        
        sent_count = 0
        for person in non_responders:
            success = self._send_reminder_to_person(person, message)
            if success:
                sent_count += 1
        
        logger.info(f"Sent {sent_count}/{len(non_responders)} reminders for form '{form_name}'")
        return sent_count
    
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
    
    def get_summary_report(self) -> str:
        """Get a summary of all forms and their non-responder counts."""
        all_non_responders = self.notion.get_all_non_responders()
        
        report = "📊 REMINDER SUMMARY REPORT\n"
        report += "=" * 30 + "\n\n"
        
        total_people = 0
        for form_name, people in all_non_responders.items():
            count = len(people)
            total_people += count
            
            if count > 0:
                report += f"📋 {form_name}: {count} people need reminders\n"
                for person in people:
                    name = self.notion.get_property_content(person, self.notion.columns.PERSON_NAME)
                    report += f"   • {name}\n"
                report += "\n"
            else:
                report += f"✅ {form_name}: All responses received\n\n"
        
        report += f"🎯 TOTAL: {total_people} reminders needed across all forms"
        return report