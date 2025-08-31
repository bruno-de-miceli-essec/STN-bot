# 📋 Enhanced Reminder System with Google Forms Integration

Un système automatisé de relances qui synchronise les réponses Google Forms avec Notion et envoie des rappels via Facebook Messenger.

## 🚀 Nouvelles Fonctionnalités

### ✨ Synchronisation Google Forms
- Récupération automatique des réponses depuis Google Forms
- Comparaison des emails entre Google Forms et Notion
- Mise à jour automatique du statut "A répondu" dans Notion

### 🎯 Modes d'Opération
1. **Sync seulement** - Met à jour Notion depuis Google Forms
2. **Sync + Relances** - Synchronise puis envoie les rappels
3. **Relances seulement** - Utilise les données Notion actuelles
4. **Rapport complet** - Vue d'ensemble sans action

### 🔗 Préparation Webhook
- Fonctions dédiées pour les déclencheurs externes
- Support pour synchronisation et relances séparées
- Compatible avec les boutons Notion via webhook

## 📦 Installation

### 1. Dépendances Python
```bash
pip install -r requirements.txt
```

### 2. Configuration Google Forms API

#### Créer un compte de service
1. Allez sur [Google Cloud Console](https://console.cloud.google.com)
2. Créez un nouveau projet ou sélectionnez-en un
3. Activez l'API Google Forms
4. Créez un compte de service :
   - IAM & Admin > Comptes de service
   - Créer un compte de service
   - Téléchargez le fichier JSON des clés

#### Partager vos formulaires
- Partagez chaque Google Form avec l'email du compte de service
- Donnez les droits de "Lecteur"

### 3. Configuration Notion

#### Nouveaux champs requis dans vos bases de données :

**Base "Forms" :**
- `Google Form ID` (Texte) - L'ID du Google Form correspondant

**Base "People" :**
- `Email` (Email) - L'adresse email pour la synchronisation

#### Trouver l'ID d'un Google Form
L'ID se trouve dans l'URL : `https://docs.google.com/forms/d/[FORM_ID]/edit`

### 4. Variables d'environnement
Copiez `.env.example` vers `.env` et remplissez :

```bash
# Notion
NOTION_TOKEN=secret_xxxxxxxxx
NOTION_PEOPLE_DB_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
NOTION_FORMS_DB_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
NOTION_RESPONSES_DB_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Facebook Messenger
PAGE_TOKEN=your_facebook_page_access_token

# Google Forms
GOOGLE_SERVICE_ACCOUNT_PATH=/path/to/service-account-key.json
```

## 🧪 Tests

Vérifiez que tout fonctionne :
```bash
python test.py
```

## 🎮 Utilisation

### Mode Manuel

```python
from reminder_service import ReminderService

service = ReminderService()

# 1. Rapport complet (recommandé pour commencer)
print(service.get_summary_report(include_sync_report=True))

# 2. Synchronisation seule
sync_results = service.sync_only_all_forms()

# 3. Synchronisation + Relances
summary = service.send_reminders_for_all_forms(sync_first=True)

# 4. Formulaire spécifique
result = service.send_reminders_for_specific_form("form_id", sync_first=True)
```

### Mode Webhook (pour boutons Notion)

```python
# Synchronisation via webhook
from main import webhook_sync_handler
result = webhook_sync_handler()  # Tous les formulaires
result = webhook_sync_handler("form_id")  # Formulaire spécifique

# Relances via webhook
from main import webhook_reminder_handler
result = webhook_reminder_handler()  # Tous les formulaires
result = webhook_reminder_handler("form_id")  # Formulaire spécifique
```

## 🔄 Workflow Recommandé

### Configuration Initiale
1. ✅ Ajoutez les champs requis dans Notion
2. ✅ Configurez le compte de service Google
3. ✅ Remplissez les Google Form IDs dans Notion
4. ✅ Testez avec `python test.py`

### Utilisation Quotidienne
1. **Synchronisation** - Met à jour les statuts depuis Google Forms
2. **Relances** - Envoie les rappels aux non-répondants
3. **Monitoring** - Vérifiez les logs pour les erreurs

### Automatisation Future
- Configurez des webhooks Notion
- Créez des boutons pour déclencher sync/relances
- Programmez des exécutions périodiques

## 📊 Logs et Monitoring

Les logs sont sauvegardés dans `reminder_app.log` et affichés dans la console.

### Types de logs importants :
- ✅ Synchronisations réussies
- 📧 Messages envoyés
- ⚠️ Avertissements (champs manquants, etc.)
- ❌ Erreurs (API, permissions, etc.)

## 🔧 Dépannage

### Erreurs Courantes

**Google Forms API failed**
- Vérifiez que l'API est activée
- Confirmez le chemin vers le fichier JSON
- Assurez-vous que les formulaires sont partagés

**Missing Google Form ID**
- Ajoutez le champ dans la base Notion Forms
- Remplissez les IDs pour chaque formulaire

**No email found**
- Ajoutez le champ Email dans la base People
- Ou configurez la collecte d'emails dans Google Forms

### Tests de Diagnostic
```bash
# Test complet
python test.py

# Test d'un composant spécifique
python -c "from google_forms_client import GoogleFormsClient; print('OK')"
```

## 📈 Prochaines Étapes

1. **Testez** avec un petit formulaire
2. **Configurez** les webhooks Notion
3. **Automatisez** selon vos besoins
4. **Surveillez** les performances et logs

## 🆘 Support

En cas de problème :
1. Consultez les logs dans `reminder_app.log`
2. Exécutez `python test.py` pour diagnostiquer
3. Vérifiez les permissions et configurations API

---

🎉 **Votre système est maintenant prêt à automatiser vos relances avec une synchronisation complète Google Forms → Notion → Messenger !**