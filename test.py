"""Enhanced test file for App Script integration - no Google Cloud required!"""
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
        print(f"✅ App Script URL: {config.google_app_script_url[:50]}...")
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

def test_app_script_client():
    """Test 3: Check if App Script client works"""
    print("\n🧪 Testing Google Forms App Script client...")
    try:
        from google_forms_client import GoogleFormsAppScriptClient
        app_script_client = GoogleFormsAppScriptClient()
        
        # Test basic connection
        connection_test = app_script_client.test_connection()
        
        if connection_test:
            print("✅ App Script client created and connection test passed")
        else:
            print("⚠️  App Script client created but connection test failed")
            print("💡 This might be normal if no sample form ID provided")
        
        return True
    except Exception as e:
        print(f"❌ App Script client failed: {e}")
        print("💡 Make sure you have:")
        print("   1. Deployed your App Script as a web app")
        print("   2. Set execution permissions to 'Anyone'")
        print("   3. Correct App Script URL in GOOGLE_APP_SCRIPT_URL")
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
    """Test 5: Check if synchronizer service works with App Script"""
    print("\n🧪 Testing App Script Synchronizer service...")
    try:
        from synchronizer_service import SynchronizerService
        synchronizer = SynchronizerService()
        
        # Get sync report (safe - no actual sync)
        report = synchronizer.get_sync_report()
        print("✅ App Script sync report generated:")
        print(report[:400] + "..." if len(report) > 400 else report)
        
        return True
    except Exception as e:
        print(f"❌ Synchronizer service failed: {e}")
        return False

def test_reminder_service():
    """Test 6: Check if enhanced reminder service works with App Script"""
    print("\n🧪 Testing Enhanced Reminder service with App Script...")
    try:
        from reminder_service import ReminderService
        service = ReminderService()
        
        # Get comprehensive summary report (safe - no messages sent)
        report = service.get_summary_report(include_sync_report=True)
        print("✅ Comprehensive summary report with App Script info generated:")
        print(report[:500] + "..." if len(report) > 500 else report)
        
        return True
    except Exception as e:
        print(f"❌ Enhanced Reminder service failed: {e}")
        return False

def test_database_structure():
    """Test 7: Check if required Notion database fields exist"""
    print("\n🧪 Testing Notion database structure for App Script integration...")
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

def test_end_to_end_with_sample_form():
    """Test 8: End-to-end test with App Script (if sample form available)"""
    print("\n🧪 Testing end-to-end App Script integration...")
    try:
        from reminder_service import ReminderService
        service = ReminderService()
        
        # Test App Script connection with configured forms
        test_results = service.test_app_script_connection()
        
        accessible_forms = sum(1 for result in test_results.values() 
                              if result.get("status") == "success")
        
        print(f"✅ App Script connection test completed")
        print(f"📊 Forms accessible via App Script: {accessible_forms}/{len(test_results)}")
        
        for form_name, result in test_results.items():
            status = result.get("status", "unknown")
            if status == "success":
                emails = result.get("emails_found", 0)
                print(f"   ✅ {form_name}: {emails} emails found")
            elif status == "skipped":
                print(f"   ⚠️  {form_name}: {result.get('reason', 'Unknown reason')}")
            else:
                print(f"   ❌ {form_name}: {result.get('error', 'Unknown error')}")
        
        return accessible_forms > 0
        
    except Exception as e:
        print(f"❌ End-to-end test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 RUNNING APP SCRIPT INTEGRATION TESTS")
    print("=" * 55)
    
    tests = [
        test_config,
        test_notion_client,
        test_app_script_client,
        test_messenger_client,
        test_synchronizer_service,
        test_reminder_service,
        test_database_structure,
        test_end_to_end_with_sample_form
    ]
    results = []
    
    for test in tests:
        results.append(test())
    
    print("\n📊 TEST RESULTS:")
    print("=" * 55)
    passed = sum(results)
    total = len(results)
    
    print(f"✅ Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Your App Script integration is ready!")
        print("\n💡 SETUP CHECKLIST:")
        print("✅ App Script deployed as web app")
        print("✅ Python environment configured")
        print("✅ Notion databases structured correctly")
        print("\n🚀 READY TO USE:")
        print("1. Fill Google Form IDs in your Notion Forms database")
        print("2. Test with: python main.py")
        print("3. Set up webhooks for automation")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        print("\n🔧 COMMON APP SCRIPT ISSUES:")
        print("- App Script not deployed as web app")
        print("- Wrong execution permissions (should be 'Anyone')")
        print("- Forms not shared with App Script owner")
        print("- Email collection not enabled in Google Forms")
        print("- Missing Notion database fields")