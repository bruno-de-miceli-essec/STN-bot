import os
import requests
from dotenv import load_dotenv

# Environment variables
def load_env():
    load_dotenv()
    return {
        "NOTION_TOKEN": os.getenv("NOTION_TOKEN"),
        "NOTION_PEOPLE_DB_ID": os.getenv("NOTION_PEOPLE_DB_ID"),
        "PAGE_TOKEN": os.getenv("PAGE_TOKEN"),
        "NOTION_FORMS_DB_ID": os.getenv("NOTION_FORMS_DB_ID"),
        "NOTION_RESPONSES_DB_ID": os.getenv("NOTION_RESPONSES_DB_ID")
    }

def get_notion_headers():
    return {
        "Authorization": f"Bearer {load_env()['NOTION_TOKEN']}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }


# NOTION
def fetch_database_entries(db_name):
    url = f"https://api.notion.com/v1/databases/{load_env()[db_name]}/query"
    response = requests.post(url, headers=get_notion_headers())
    
    if response.status_code != 200:
        print("❌ Erreur :", response.text)
        return []
    
    data = response.json()
    return data.get("results", [])




# Move find_content from utils.py
def find_content(person, content):
    property_type = person["properties"][content]["type"]
    content_value = person["properties"][content][property_type]
    content_type = content_value[0]["type"]
    value = content_value[0][content_type]["content"]
    return value


# MESSENGER
def sent_message(person, message):
    page_token = os.getenv("PAGE_TOKEN")
    messenger_url = f"https://graph.facebook.com/v17.0/me/messages?access_token={page_token}"
    message_data = {
        "recipient": {"id": find_content(person, "PSID")},
        "message": {"text": message}
    }
    response = requests.post(messenger_url, json=message_data)
    return response