"""Enhanced test file to check each component works including Google Forms integration"""
import logging
from config import config

# Set up simple logging for testing
logging.basicConfig(level=logging.INFO)

def test_config():
    """Test 1: Check if config loads correctly"""
    print("🧪 Testing config...")
    try:
        from config import config
        print(f"✅ Config loaded. Notion token exists: {bool(config.notion_token)}")
        print(f"✅ Forms DB ID: {config.notion_forms_db_id[:10]}...")
        print(f"✅ Google service account path: {config.google_service_account_path}")
        return True
    except Exception as e:
        print(f"❌ Config failed: {e}")
        return False

def test_notion_client():
    """Test 2: Check if Notion client works"""
    print("\n🧪 Testing Notion client...")
    try:
        from notion_connection import NotionClient
        notion = NotionClient()
        
        # Try to get forms
        forms = notion.get_all_forms()
        print(f"✅ Found {len(forms)} forms in database")
        
        if forms:
            first_form = forms[0]
            form_name = notion.get_property_content(first_form, notion.columns.FORM_NAME)
            google_form_id = notion.get_property_content(first_form, notion.columns.GOOGLE_FORM_ID)
            print(f"✅ First form name: '{form_name}'")
            print(f"✅ Google Form ID: {google_form_id or 'Not set'}")
        
        return True
    except Exception as e:
        print(f"❌ Notion client failed: {e}")
        return False

def test_google_forms_client():
    """Test 3: Check if Google Forms client initializes"""
    print("\n🧪 Testing Google Forms client...")
    try:
        from google_forms_client import GoogleFormsClient
        google_forms = GoogleFormsClient()
        print("✅ Google Forms client created successfully")
        print("⚠️  Note: Not fetching actual responses (would need valid Form ID)")
        return True
    except Exception as e:
        print(f"❌ Google Forms client failed: {e}")
        print("💡 Make sure you have:")
        print("   1. Valid service account JSON file")
        print("   2. Google Forms API enabled")
        print("   3. Correct file path in GOOGLE_SERVICE_ACCOUNT_PATH")
        return False

def test_messenger_client():
    """Test 4: Check if Messenger client initializes"""
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

def test_synchronizer_service():
    """Test 5: Check if synchronizer service works"""
    print("\n🧪 Testing Synchronizer service...")
    try:
        from synchronizer_service import SynchronizerService
        synchronizer = SynchronizerService()
        
        # Get sync report (safe - no actual sync)
        report = synchronizer.get_sync_report()
        print("✅ Sync report generated:")
        print(report[:300] + "..." if len(report) > 300 else report)
        
        return True
    except Exception as e:
        print(f"❌ Synchronizer service failed: {e}")
        return False

def test_reminder_service():
    """Test 6: Check if enhanced reminder service works"""
    print("\n🧪 Testing Enhanced Reminder service...")
    try:
        from reminder_service import ReminderService
        service = ReminderService()
        
        # Get comprehensive summary report (safe - no messages sent)
        report = service.get_summary_report(include_sync_report=True)
        print("✅ Comprehensive summary report generated:")
        print(report[:400] + "..." if len(report) > 400 else report)
        
        return True
    except Exception as e:
        print(f"❌ Enhanced Reminder service failed: {e}")
        return False

def test_database_structure():
    """Test 7: Check if required Notion database fields exist"""
    print("\n🧪 Testing Notion database structure...")
    try:
        from notion_connection import NotionClient
        notion = NotionClient()
        
        # Check Forms database structure
        forms = notion.get_all_forms()
        if forms:
            first_form = forms[0]
            required_form_fields = [
                notion.columns.FORM_NAME,
                notion.columns.GOOGLE_FORM_ID
            ]
            
            missing_fields = []
            for field in required_form_fields:
                if not notion.columns.validate_property_exists(first_form, field):
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"⚠️  Missing fields in Forms database: {missing_fields}")
                print("💡 You need to add these fields to your Notion Forms database:")
                for field in missing_fields:
                    if field == notion.columns.GOOGLE_FORM_ID:
                        print(f"   - {field} (Text property)")
            else:
                print("✅ Forms database has all required fields")
        
        # Check People database structure
        people = notion.get_database_entries(config.notion_people_db_id)
        if people:
            first_person = people[0]
            if not notion.columns.validate_property_exists(first_person, notion.columns.PERSON_EMAIL):
                print(f"⚠️  Missing 'Email' field in People database")
                print("💡 Add an 'Email' property to your Notion People database")
            else:
                print("✅ People database has required Email field")
        
        return True
    except Exception as e:
        print(f"❌ Database structure test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 RUNNING ENHANCED TESTS")
    print("=" * 50)
    
    tests = [
        test_config,
        test_notion_client,
        test_google_forms_client,
        test_messenger_client,
        test_synchronizer_service,
        test_reminder_service,
        test_database_structure
    ]
    results = []
    
    for test in tests:
        results.append(test())
    
    print("\n📊 TEST RESULTS:")
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Your enhanced app is ready to use!")
        print("\n💡 SETUP REMINDERS:")
        print("1. Add 'Google Form ID' field to your Notion Forms database")
        print("2. Add 'Email' field to your Notion People database")
        print("3. Fill in Google Form IDs for each form you want to sync")
        print("4. Test with a small form first")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        print("\n🔧 COMMON ISSUES:")
        print("- Missing Google service account file")
        print("- Missing Notion database fields")
        print("- Invalid API credentials")
        print("- Google Forms API not enabled")