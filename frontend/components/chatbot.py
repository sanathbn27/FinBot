import streamlit as st
import requests


def show_chatbot(BACKEND_URL):
    st.header("💬 FinBot Chat Assistant")

    # Chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Warning placeholder (so warning appears top-right near input, not in chat)
    warning_box = st.empty()

    # -------------------------
    # INPUT FORM (Fixes fade/blink + allows Enter)
    # -------------------------
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_input(
            "Ask FinBot about crypto trends or prices:", key="pending_user_input"
        )
        submitted = st.form_submit_button("Send")

    # Handle submission
    if submitted:
        if not user_input.strip():
            warning_box.warning("⚠️ Please enter a question related to cryptocurrency.")
        else:
            warning_box.empty()  # Clear any previous warning

            # Save user message
            # st.session_state.chat_history.append(("You", user_input))

            # Backend call
            try:
                res = requests.post(f"{BACKEND_URL}/chat", json={"message": user_input})
                res.raise_for_status()
                reply = res.json().get("reply", "No response")
            except Exception as e:
                reply = f"Error: {e}"

            # Save FinBot reply
            st.session_state.chat_history.append(
                {"question": user_input, "answer": reply}
            )

    st.markdown("---")

    # Display messages with newest on top
    for chat in reversed(st.session_state.chat_history):
        st.markdown(f"**>> You:** {chat['question']}")
        st.markdown(f"**🤖 FinBot:** {chat['answer']}")
        st.markdown("---")
