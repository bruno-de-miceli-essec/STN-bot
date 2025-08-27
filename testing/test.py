import os
import requests

from connections import load_env  # form_id n'est plus importé ici
from utils import check_participation, get_form_id

load_env()  # charge les variables depuis le .env

if __name__ == "__main__":
    form_name = "Rappel envoyé"
    form_id = get_form_id(form_name)
    check_participation(form_id)
    