# frontend/streamlit_app_groq.py
# Groq/cloud-ready Streamlit entry point — replaces streamlit_app.py
#
# Local dev:  set BACKEND_URL=http://127.0.0.1:8000 in .env (or leave unset, defaults to that)
# Deployed:   set BACKEND_URL=https://your-backend.onrender.com in Streamlit Cloud secrets

import os
import streamlit as st
from dotenv import load_dotenv
from components.dashboard import show_dashboard
from components.chatbot import show_chatbot

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.sidebar.title("FinBot Navigation")
page = st.sidebar.radio("Go to:", ["Dashboard", "Chatbot"])

if page == "Dashboard":
    show_dashboard(BACKEND_URL)
elif page == "Chatbot":
    show_chatbot(BACKEND_URL)
