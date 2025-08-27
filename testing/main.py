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
    """Main application entry point."""
    logger.info("🚀 Starting Reminder Application")
    
    try:
        service = ReminderService()
        
        # Option 1: Get summary report (no messages sent)
        print("\n" + service.get_summary_report())
        
        # Option 2: Send reminders for all forms
        # summary = service.send_reminders_for_all_forms()
        # print(f"\n📊 Summary: {summary}")
        
        # Option 3: Send reminders for specific form
        # form_id = "your_form_id_here"
        # sent_count = service.send_reminders_for_specific_form(form_id)
        # print(f"Sent {sent_count} reminders")
        
        logger.info("✅ Application completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Application failed: {e}")
        raise

if __name__ == "__main__":
    main()