import logging
from utils.reminder_service import ReminderService
from typing import Optional

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
    """Main application entry point with App Script integration."""
    logger.info("🚀 Starting Enhanced Reminder Application with Google App Script Integration")
    
    try:
        service = ReminderService()
        
        # ===== CHOOSE YOUR OPERATION MODE =====
        
        # Mode 1: Get comprehensive report (includes App Script sync status + reminders needed)
        #print("\n" + service.get_summary_report(include_sync_report=True))
        
        # Mode 2: TEST APP SCRIPT CONNECTION - Verify your setup works
        # test_results = service.test_app_script_connection()
        # print(f"\n🧪 App Script Test Results: {test_results}")
        
        # Mode 3: SYNC ONLY - Update Notion responses from Google Forms via App Script
        # This is perfect for webhook triggers for synchronization
        # sync_results = service.sync_only_all_forms()
        # print(f"\n🔄 App Script Sync Summary: {sync_results}")
        
        # Mode 4: SYNC + SEND REMINDERS - Complete workflow via App Script
        # This synchronizes first via App Script, then sends reminders based on updated data
        summary = service.send_reminders_for_all_forms(sync_first=True)
        print(f"\n📊 Complete App Script Summary: {summary}")
        
        # Mode 5: SEND REMINDERS ONLY - Skip sync, use current Notion data
        # Useful when you've already synced recently
        # summary = service.send_reminders_for_all_forms(sync_first=False)
        # print(f"\n📧 Reminders Summary: {summary}")
        
        # Mode 6: SPECIFIC FORM operations
        # form_id = "your_specific_notion_form_id_here"
        
        # 6a: Sync only specific form via App Script
        # sync_result = service.sync_only_specific_form(form_id)
        # print(f"\n🔄 Form Sync Result: {sync_result}")
        
        # 6b: Sync + Send reminders for specific form
        # result = service.send_reminders_for_specific_form(form_id, sync_first=True)
        # print(f"\n📊 Specific Form Result: {result}")
        
        logger.info("✅ Application completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Application failed: {e}")
        raise

def webhook_sync_handler(form_id: Optional[str] = None):
    """
    Handler function for webhook-triggered synchronization via App Script.
    This can be called by external webhook systems.
    
    Args:
        form_id: Optional specific form ID. If None, syncs all forms.
    """
    logger.info(f"🔗 Webhook triggered App Script sync - Form ID: {form_id or 'ALL'}")
    
    try:
        service = ReminderService()
        
        if form_id:
            # Sync specific form via App Script
            result = service.sync_only_specific_form(form_id)
            logger.info(f"✅ Webhook App Script sync completed for form {form_id}: {result}")
            return result
        else:
            # Sync all forms via App Script
            results = service.sync_only_all_forms()
            total_updated = sum(r.get("updated_count", 0) for r in results.values() 
                              if isinstance(r, dict))
            logger.info(f"✅ Webhook App Script sync completed for all forms: {total_updated} updates")
            return results
            
    except Exception as e:
        logger.error(f"❌ Webhook App Script sync failed: {e}")
        return {"status": "error", "error": str(e)}

def webhook_reminder_handler(form_id: Optional[str] = None):
    """
    Handler function for webhook-triggered reminders with App Script sync.
    This can be called by external webhook systems.
    
    Args:
        form_id: Optional specific form ID. If None, sends for all forms.
    """
    logger.info(f"🔗 Webhook triggered reminders with App Script - Form ID: {form_id or 'ALL'}")
    
    try:
        service = ReminderService()
        
        if form_id:
            # Send reminders for specific form (with App Script sync)
            result = service.send_reminders_for_specific_form(form_id, sync_first=True)
            logger.info(f"✅ Webhook reminders completed for form {form_id}: {result}")
            return result
        else:
            # Send reminders for all forms (with App Script sync)
            result = service.send_reminders_for_all_forms(sync_first=True)
            total_sent = sum(count for count in result["reminders"].values())
            logger.info(f"✅ Webhook reminders completed: {total_sent} reminders sent")
            return result
            
    except Exception as e:
        logger.error(f"❌ Webhook reminders failed: {e}")
        return {"status": "error", "error": str(e)}

def test_app_script_setup():
    """
    Quick test function to verify App Script integration is working.
    """
    logger.info("🧪 Testing App Script setup")
    
    try:
        service = ReminderService()
        
        # Test App Script connection
        test_results = service.test_app_script_connection()
        
        accessible_forms = sum(1 for result in test_results.values() 
                              if result.get("status") == "success")
        
        if accessible_forms > 0:
            print(f"🎉 App Script integration working! {accessible_forms} forms accessible")
            return True
        else:
            print("⚠️  App Script setup needs attention - check forms sharing and IDs")
            return False
            
    except Exception as e:
        logger.error(f"❌ App Script test failed: {e}")
        return False

if __name__ == "__main__":
    # For manual execution
    main()
    
    # For App Script testing (uncomment to test):
    # test_app_script_setup()
    
    # For webhook testing (uncomment to test):
    # webhook_sync_handler()  # Sync all forms via App Script
    # webhook_sync_handler("specific_form_id")  # Sync specific form
    # webhook_reminder_handler()  # Send reminders for all forms
    # webhook_reminder_handler("specific_form_id")  # Send reminders for specific form

# Import statement for webhook handlers
from typing import Optional