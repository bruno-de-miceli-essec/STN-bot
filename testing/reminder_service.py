import logging
from typing import List, Dict, Optional
from notion_connection import NotionClient
from messenger_client import MessengerClient

logger = logging.getLogger(__name__)

class ReminderService:
    def __init__(self):
        self.notion = NotionClient()
        self.messenger = MessengerClient()
    
    def send_reminders_for_all_forms(self, custom_message: Optional[str] = None) -> Dict[str, int]:
        """Send reminders for all forms. Returns summary of sent messages."""
        forms = self.notion.get_all_forms()
        summary: Dict[str, int] = {}
        for form in forms:
            form_id = form["id"]
            form_name = self.notion.get_form_name(form_id) or "Unknown Form"
            people = self.notion.get_non_responders_for_form(form_id)
            if not people:
                logger.info(f"Form '{form_name}': No reminders needed")
                summary[form_name] = 0
                continue
            sent_count = 0
            for person in people:
                message = self._build_message(form_id, person, custom_message)
                if self._send_reminder_to_person(person, message):
                    sent_count += 1
            summary[form_name] = sent_count
            logger.info(f"Form '{form_name}': {sent_count}/{len(people)} reminders sent")
        return summary
    
    def send_reminders_for_specific_form(self, form_id: str, custom_message: Optional[str] = None) -> int:
        """Send reminders for a specific form. Returns number of messages sent."""
        non_responders = self.notion.get_non_responders_for_form(form_id)
        
        if not non_responders:
            logger.info(f"No reminders needed for form {form_id}")
            return 0
        
        form_name = self._get_form_name(form_id)
        sent_count = 0
        for person in non_responders:
            message = self._build_message(form_id, person, custom_message)
            if self._send_reminder_to_person(person, message):
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
    
    def _build_message(self, form_id: str, person: dict, custom_message: Optional[str]) -> str:
        """Build a localized message including form name, link, and dates."""
        form_name = self._get_form_name(form_id)
        form_url = self.notion.get_form_link(form_id)
        person_name = self.notion.get_property_content(person, self.notion.columns.PERSON_NAME) or ""
        first_name = (person_name.strip().split(" ")[0]) if person_name else ""
        # Fetch the response page to read date fields
        person_id = person.get("id", "")
        response = self.notion.get_response_for_person_form(form_id, person_id)
        date_envoi_iso = self.notion.get_date_property(response, self.notion.columns.DATE_SENT) if response else None
        last_reminder_iso = self.notion.get_date_property(response, self.notion.columns.LAST_REMINDER) if response else None
        date_envoi_fmt = self.notion.format_datetime_fr(date_envoi_iso)
        last_reminder_fmt = self.notion.format_datetime_fr(last_reminder_iso)
        # Base text
        if custom_message:
            base = custom_message
        else:
            base = f"Bonjour {first_name}, merci de compléter le formulaire « {form_name} »."
        details = []
        if form_url:
            details.append(f"Lien : {form_url}")
        if date_envoi_fmt:
            details.append(f"envoyé {date_envoi_fmt}")
        if last_reminder_fmt:
            details.append(f"tu as été relancé {last_reminder_fmt}")
        if details:
            return base + "\n(" + " – ".join(details) + ")"
        return base
    
    def _get_form_name(self, form_id: str) -> str:
        return self.notion.get_form_name(form_id) or "Unknown Form"
    
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