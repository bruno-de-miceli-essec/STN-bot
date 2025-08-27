"""Basic test file to check each component works"""
import logging

# Set up simple logging for testing
logging.basicConfig(level=logging.INFO)

def test_config():
    """Test 1: Check if config loads correctly"""
    print("🧪 Testing config...")
    try:
        from config import config
        print(f"✅ Config loaded. Token exists: {bool(config.notion_token)}")
        print(f"✅ Forms DB ID: {config.notion_forms_db_id[:10]}...")
        return True
    except Exception as e:
        print(f"❌ Config failed: {e}")
        return False

def test_notion_client():
    """Test 2: Check if Notion client works"""
    print("\n🧪 Testing Notion client...")
    try:
        from notion_client import NotionClient
        notion = NotionClient()
        
        # Try to get forms
        forms = notion.get_all_forms()
        print(f"✅ Found {len(forms)} forms in database")
        
        if forms:
            first_form = forms[0]
            form_name = notion.get_property_content(first_form, notion.columns.FORM_NAME)
            print(f"✅ First form name: '{form_name}'")
        
        return True
    except Exception as e:
        print(f"❌ Notion client failed: {e}")
        return False

def test_messenger_client():
    """Test 3: Check if Messenger client initializes"""
    print("\n🧪 Testing Messenger client...")
    try:
        from messenger_client import MessengerClient
        messenger = MessengerClient()
        print("✅ Messenger client created successfully")
        print("⚠️  Note: Not sending actual message (would need valid PSID)")
        return True
    except Exception as e:
        print(f"❌ Messenger client failed: {e}")
        return False

def test_reminder_service():
    """Test 4: Check if reminder service works"""
    print("\n🧪 Testing Reminder service...")
    try:
        from reminder_service import ReminderService
        service = ReminderService()
        
        # Get summary report (safe - no messages sent)
        report = service.get_summary_report()
        print("✅ Summary report generated:")
        print(report[:200] + "..." if len(report) > 200 else report)
        
        return True
    except Exception as e:
        print(f"❌ Reminder service failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 RUNNING BASIC TESTS")
    print("=" * 40)
    
    tests = [test_config, test_notion_client, test_messenger_client, test_reminder_service]
    results = []
    
    for test in tests:
        results.append(test())
    
    print("\n📊 TEST RESULTS:")
    print("=" * 40)
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Your app is ready to use!")
    else:
        print("⚠️  Some tests failed. Check the errors above.")