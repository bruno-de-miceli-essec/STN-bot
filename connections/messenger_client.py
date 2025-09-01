import requests
import logging
from typing import Dict
from config.config import config

logger = logging.getLogger(__name__)

class MessengerClient:
    def __init__(self):
        self.base_url = "https://graph.facebook.com/v17.0/me/messages"
        self.access_token = config.page_token
    
    def send_message(self, recipient_id: str, message: str) -> bool:
        """Send a message via Facebook Messenger."""
        url = f"{self.base_url}?access_token={self.access_token}"
        
        message_data = {
            "recipient": {"id": recipient_id},
            "message": {"text": message}
        }
        
        try:
            response = requests.post(url, json=message_data)
            response.raise_for_status()
            logger.info(f"Message sent successfully to {recipient_id}")
            return True
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send message to {recipient_id}: {e}")
            return False