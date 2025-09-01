import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

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
        
        # Google App Script configuration (renamed for clarity)
        self.google_app_script_url = self._get_required_env("GOOGLE_APP_SCRIPT_URL")
        
        # Backward compatibility (if you have old .env files)
        if not hasattr(self, 'google_app_script_url'):
            # Try the old name for backward compatibility
            old_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_PATH")
            if old_path:
                self.google_app_script_url = old_path
                logger.warning("Using GOOGLE_SERVICE_ACCOUNT_PATH as App Script URL - consider renaming to GOOGLE_APP_SCRIPT_URL")
    
    def _get_required_env(self, key):
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Missing required environment variable: {key}")
        return value

# Global config instance
config = Config()