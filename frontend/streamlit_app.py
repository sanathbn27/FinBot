import streamlit as st
from components.dashboard import show_dashboard
from components.chatbot import show_chatbot

BACKEND_URL = "http://127.0.0.1:8000"

st.sidebar.title("FinBot Navigation")
page = st.sidebar.radio("Go to:", ["Dashboard", "Chatbot"])


if page == "Dashboard":
    show_dashboard(BACKEND_URL)
elif page == "Chatbot":
    show_chatbot(BACKEND_URL)
