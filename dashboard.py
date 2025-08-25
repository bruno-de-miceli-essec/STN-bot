import streamlit as st
import scanner as s

st.title("STN Bot Dashboard")

if st.button("Synchroniser les réponses"):
    with st.spinner("Synchronisation en cours..."):
        updated = s.run_sync_from_forms_sync()
    st.success(f"{updated} nouvelles réponses mises à jour dans Notion")

if st.button("Envoyer les rappels"):
    with st.spinner("Envoi en cours..."):
        sent = s.run_send_reminders_sync()
    st.success(f"{sent} rappels envoyés")