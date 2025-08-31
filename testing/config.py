import os
from dotenv import load_dotenv

class Config:
    def __init__(self):
        load_dotenv()
        
        # Notion configuration
        self.notion_token = self._get_required_env("NOTION_TOKEN")
        self.notion_people_db_id = self._get_required_env("NOTION_PEOPLE_DB_ID")
        self.notion_forms_db_id = self._get_required_env("NOTION_FORMS_DB_ID")
        self.notion_responses_db_id = self._get_required_env("NOTION_RESPONSES_DB_ID")
        
        # Messenger configuration
        self.page_token = self._get_required_env("PAGE_TOKEN")
        
        # Google Forms configuration
        self.google_service_account_path = self._get_required_env("GOOGLE_SERVICE_ACCOUNT_PATH")
    
    def _get_required_env(self, key):
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Missing required environment variable: {key}")
        return value

# Global config instance
config = Config()