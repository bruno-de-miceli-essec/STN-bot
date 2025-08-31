import logging
from reminder_service import ReminderService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('reminder_app.log'),  # Save logs to file
        logging.StreamHandler()  # Also print to console
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main application entry point with various operation modes."""
    logger.info("🚀 Starting Enhanced Reminder Application with Google Forms Integration")
    
    try:
        service = ReminderService()
        
        # ===== CHOOSE YOUR OPERATION MODE =====
        
        # Mode 1: Get comprehensive report (includes sync status + reminders needed)
        print("\n" + service.get_summary_report(include_sync_report=True))
        
        # Mode 2: SYNC ONLY - Update Notion responses from Google Forms (no reminders sent)
        # This is perfect for webhook triggers for synchronization
        # sync_results = service.sync_only_all_forms()
        # print(f"\n🔄 Sync Summary: {sync_results}")
        
        # Mode 3: SYNC + SEND REMINDERS - Complete workflow
        # This synchronizes first, then sends reminders based on updated data
        # summary = service.send_reminders_for_all_forms(sync_first=True)
        # print(f"\n📊 Complete Summary: {summary}")
        
        # Mode 4: SEND REMINDERS ONLY - Skip sync, use current Notion data
        # Useful when you've already synced recently
        # summary = service.send_reminders_for_all_forms(sync_first=False)
        # print(f"\n📧 Reminders Summary: {summary}")
        
        # Mode 5: SPECIFIC FORM operations
        # form_id = "your_specific_form_id_here"
        
        # 5a: Sync only specific form
        # sync_result = service.sync_only_specific_form(form_id)
        # print(f"\n🔄 Form Sync Result: {sync_result}")
        
        # 5b: Sync + Send reminders for specific form
        # result = service.send_reminders_for_specific_form(form_id, sync_first=True)
        # print(f"\n📊 Specific Form Result: {result}")
        
        logger.info("✅ Application completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Application failed: {e}")
        raise

from typing import Optional

def webhook_sync_handler(form_id: Optional[str] = None):
    """
    Handler function for webhook-triggered synchronization.
    This can be called by external webhook systems.
    
    Args:
        form_id: Optional specific form ID. If None, syncs all forms.
    """
    logger.info(f"🔗 Webhook triggered sync - Form ID: {form_id or 'ALL'}")
    
    try:
        service = ReminderService()
        
        if form_id:
            # Sync specific form
            result = service.sync_only_specific_form(form_id)
            logger.info(f"✅ Webhook sync completed for form {form_id}: {result}")
            return result
        else:
            # Sync all forms
            results = service.sync_only_all_forms()
            total_updated = sum(r.get("updated_count", 0) for r in results.values() 
                              if isinstance(r, dict))
            logger.info(f"✅ Webhook sync completed for all forms: {total_updated} updates")
            return results
            
    except Exception as e:
        logger.error(f"❌ Webhook sync failed: {e}")
        return {"status": "error", "error": str(e)}

from typing import Optional

def webhook_reminder_handler(form_id: Optional[str] = None):
    """
    Handler function for webhook-triggered reminders.
    This can be called by external webhook systems.
    
    Args:
        form_id: Optional specific form ID. If None, sends for all forms.
    """
    logger.info(f"🔗 Webhook triggered reminders - Form ID: {form_id or 'ALL'}")
    
    try:
        service = ReminderService()
        
        if form_id:
            # Send reminders for specific form (with sync)
            result = service.send_reminders_for_specific_form(form_id, sync_first=True)
            logger.info(f"✅ Webhook reminders completed for form {form_id}: {result}")
            return result
        else:
            # Send reminders for all forms (with sync)
            result = service.send_reminders_for_all_forms(sync_first=True)
            total_sent = sum(count for count in result["reminders"].values())
            logger.info(f"✅ Webhook reminders completed: {total_sent} reminders sent")
            return result
            
    except Exception as e:
        logger.error(f"❌ Webhook reminders failed: {e}")
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    # For manual execution
    main()
    
    # For webhook testing (uncomment to test):
    # webhook_sync_handler()  # Sync all forms
    # webhook_sync_handler("specific_form_id")  # Sync specific form
    # webhook_reminder_handler()  # Send reminders for all forms
    # webhook_reminder_handler("specific_form_id")  # Send reminders for specific form