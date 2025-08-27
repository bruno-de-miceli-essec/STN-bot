
import os
from notion_client import Client

def load_env():
    return {
        "NOTION_TOKEN": os.getenv("NOTION_TOKEN"),
        "NOTION_FORMS_DB_ID": os.getenv("NOTION_FORMS_DB_ID"),
        "NOTION_RESPONSES_DB_ID": os.getenv("NOTION_RESPONSES_DB_ID")
    }

env_vars = load_env()
NOTION_CLIENT = Client(auth=env_vars["NOTION_TOKEN"])

import connections



# Ajout de get_form_id pour permettre de retrouver l'id d'un formulaire à partir de son nom
def get_form_id(form_name):
    forms_db_id = load_env()["NOTION_FORMS_DB_ID"]
    notion = NOTION_CLIENT
    entries = notion.get_database_entries(forms_db_id)
    for entry in entries:
        if (
            entry["properties"].get("Nom du formulaire")
            and entry["properties"]["Nom du formulaire"]["title"]
            and entry["properties"]["Nom du formulaire"]["title"][0]["plain_text"] == form_name
        ):
            return entry["id"]
    return None


def initialize_notion_page(results):
    if not results:
        print("Aucune entrée trouvée dans la base de données.")
        return
    print(f"Nombre d'entrées trouvées : {len(results)}")
    for person in results:
        print("Nom :", connections.find_content(person, "Prénom & Nom"))


def check(page, name):
    return page["properties"][name]["checkbox"]


def get_form_id_to_name(notion, forms_db_id):
    entries = notion.get_database_entries(forms_db_id)
    return {
        entry["id"]: entry["properties"]["Nom du formulaire"]["title"][0]["plain_text"]
        for entry in entries
        if entry["properties"]["Nom du formulaire"]["title"]
    }


def check_participation(form_id, reminder_message=None):
    # Récupération des réponses associées au formulaire
    responses_db = connections.fetch_database_entries('NOTION_RESPONSES_DB_ID')
    RESPONSES_DB_ID = connections.load_env()['NOTION_RESPONSES_DB_ID']
    NOTION_CLIENT = connections.load_env()['NOTION_CLIENT']
    FORMS_DB_ID = connections.load_env()['FORMS_DB_ID']
    notion = NOTION_CLIENT

    form_id_to_name = get_form_id_to_name(notion, FORMS_DB_ID)
    form_name = form_id_to_name.get(form_id, "Nom inconnu")

    #print(responses_db)
    response_pages = [
        resp for resp in responses_db
        if resp.get("properties", {}).get("Forms", {}).get("relation")
        and resp["properties"]["Forms"]["relation"][0]["id"] == form_id
    ]

    print(response_pages)

    # Pour chaque réponse, on vérifie la personne
    for page in response_pages:
        print(connections.find_content(page, "Prénom & Nom"), " N'a pas répondu au formulaire. Message de relance envoyé.")
        if reminder_message is not None:
            response = connections.sent_message(page, reminder_message)
        else:
            response = connections.sent_message(page, "Hello ! Petit rappel pour remplir ton formulaire BDE 😉")

    return False  # aucune participation trouvée
