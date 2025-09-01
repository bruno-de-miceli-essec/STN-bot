# 📋 Enhanced Reminder System with Google App Script Integration

Un système automatisé de relances qui synchronise les réponses Google Forms avec Notion et envoie des rappels via Facebook Messenger - **SANS compte Google Cloud requis !**

## 🚀 Avantages de l'App Script

### ✨ Plus Simple
- ❌ **Pas de compte Google Cloud** nécessaire
- ❌ **Pas de compte de service** à configurer 
- ❌ **Pas d'API complexe** à activer
- ✅ **Utilise votre App Script existant** "Link Forms - Notion"

### 🎯 Fonctionnalités
1. **Sync via App Script** - Récupère les réponses via votre script déployé
2. **Sync + Relances** - Synchronise puis envoie les rappels
3. **Relances seulement** - Utilise les données Notion actuelles
4. **Rapport complet** - Vue d'ensemble avec statut App Script

### 🔗 Préparation Webhook
- Fonctions dédiées pour les déclencheurs externes
- Support pour synchronisation et relances séparées
- Compatible avec les boutons Notion via webhook

## 📦 Installation Simplifiée

### 1. Dépendances Python (beaucoup plus simple!)
```bash
pip install requests python-dotenv
```

### 2. Configuration App Script

#### Votre App Script existant
Vous avez déjà le script "Link Forms - Notion" :
```javascript
function doGet(e) {
  const formId = e && e.parameter && e.parameter.formId;
  if (!formId) return _json({error: "missing formId"});
  // ... votre code existant
}
```

#### Déploiement requis
1. **Ouvrez votre App Script** "Link Forms - Notion"
2. **Déployez comme application web** :
   - Cliquez sur "Déployer" > "Nouveau déploiement"
   - Type : "Application web"
   - Exécuter en tant que : "Moi"
   - Qui a accès : "Tout le monde"
3. **Copiez l'URL de déploiement** (finit par `/exec`)

#### Partager vos formulaires
- Partagez chaque Google Form avec votre compte Google
- Vous devez être **éditeur** du formulaire (pas juste lecteur)

### 3. Configuration Notion

#### Champs requis dans vos bases de données :

**Base "Forms" :**
- `Nom du formulaire` (Titre)
- `Form ID` (Texte) - L'ID du Google Form correspondant

**Base "People" :**
- `Prénom & Nom` (Titre)
- `PSID` (Texte) - Pour Messenger
- `Email` (Email) - Pour la synchronisation

**Base "Responses" :**
- `Forms` (Relation vers Forms)
- `Personnes` (Relation vers People)
- `A répondu` (Case à cocher)

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

# Google App Script (votre URL de déploiement)
GOOGLE_APP_SCRIPT_URL=https://script.google.com/macros/s/xxxxx.../exec
```

## 🧪 Tests

Vérifiez que tout fonctionne avec App Script :
```bash
python test.py
```

Les tests incluent maintenant :
- ✅ Test de connexion App Script
- ✅ Test d'accès aux formulaires via App Script  
- ✅ Validation de la structure Notion
- ✅ Test end-to-end complet

## 🎮 Utilisation

### Mode Manuel

```python
from reminder_service import ReminderService

service = ReminderService()

# 1. Rapport complet avec statut App Script
print(service.get_summary_report(include_sync_report=True))

# 2. Test connexion App Script
test_results = service.test_app_script_connection()
print(f"App Script test: {test_results}")

# 3. Synchronisation seule via App Script
sync_results = service.sync_only_all_forms()

# 4. Synchronisation + Relances
summary = service.send_reminders_for_all_forms(sync_first=True)

# 5. Formulaire spécifique
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
1. ✅ **Déployez votre App Script** comme application web
2. ✅ **Configurez les variables d'environnement** avec l'URL App Script
3. ✅ **Ajoutez les champs requis** dans Notion
4. ✅ **Remplissez les Google Form IDs** dans Notion
5. ✅ **Testez** avec `python test.py`

### Utilisation Quotidienne
1. **Synchronisation** - Met à jour les statuts depuis Google Forms via App Script
2. **Relances** - Envoie les rappels aux non-répondants
3. **Monitoring** - Vérifiez les logs pour les erreurs

### Automatisation Future
- Configurez des webhooks Notion
- Créez des boutons pour déclencher sync/relances
- Programmez des exécutions périodiques

## 📊 Logs et Monitoring

Les logs incluent maintenant des informations spécifiques App Script :
- 🔗 Appels vers votre App Script
- 📊 Réponses reçues via App Script
- ⚠️ Erreurs de connexion App Script
- ✅ Synchronisations réussies

## 🔧 Dépannage App Script

### Erreurs Courantes

**App Script connection failed**
- Vérifiez que le script est déployé comme "Application web"
- Confirmez les permissions "Tout le monde"
- Testez l'URL directement dans le navigateur

**Missing formId error**
- Normal lors du test de connexion
- Vérifiez que les Form IDs sont corrects dans Notion

**No emails found**
- Activez la collecte d'emails dans Google Forms
- Ou ajoutez des questions "Email" dans vos formulaires
- Assurez-vous d'être éditeur des formulaires

**Forms not accessible**
- Partagez les formulaires avec votre compte Google
- Vous devez être **éditeur** (pas juste lecteur)

### Tests de Diagnostic
```bash
# Test complet avec App Script
python test.py

# Test App Script seulement
python -c "
from google_forms_appscript_client import GoogleFormsAppScriptClient
client = GoogleFormsAppScriptClient()
print('Connection test:', client.test_connection())
"
```

## 📈 Avantages vs Version Google Cloud

| Fonctionnalité | App Script ✅ | Google Cloud ❌ |
|---|---|---|
| Configuration | Simple | Complexe |
| Compte requis | Google normal | Google Cloud |
| Coût | Gratuit | Potentiellement payant |
| Maintenance | Faible | Élevée |
| Permissions | Partage formulaire | Service account |
| Déploiement | 1 clic | Multiples étapes |

## 🆘 Support App Script

En cas de problème :
1. **Testez l'URL App Script** directement dans le navigateur
2. **Vérifiez les logs** dans `reminder_app.log`
3. **Exécutez** `python test.py` pour diagnostiquer
4. **Confirmez** que les formulaires sont partagés

### URL de test App Script
Testez votre App Script avec : `VOTRE_URL?formId=FORM_ID_TEST`

---

🎉 **Votre système App Script est maintenant prêt - plus simple, plus rapide, plus fiable !**

## 🔄 Migration depuis Google Cloud

Si vous migrez depuis la version Google Cloud :
1. Remplacez `google_forms_client.py` par `google_forms_appscript_client.py`
2. Mettez à jour `GOOGLE_SERVICE_ACCOUNT_PATH` vers `GOOGLE_APP_SCRIPT_URL`
3. Supprimez les dépendances Google API
4. Testez avec `python test.py`