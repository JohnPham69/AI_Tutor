import streamlit as st
from StAI import genRes
from streamlit_cookies_controller import CookieController
from markitdown import MarkItDown
from app_translations import get_translator # Import the translator

# Make a cookie controller instance
# @st.cache_resource # Temporarily remove caching for debugging
def get_cookie_controller_instance_ai_page(): # Ensure a fresh instance
    if 'ai_page_cookie_controller' not in st.session_state:
        st.session_state.ai_page_cookie_controller = CookieController()
    return st.session_state.ai_page_cookie_controller

controller = get_cookie_controller_instance_ai_page()

_ = get_translator() # Initialize translator for this page, assumes session_state lang is set by Tester.py

# Initialize chat history if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize chat history if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []


# Display chat messages from history.
# These will now render in Streamlit's main flow, below the sticky title.
if not st.session_state.messages:
    st.markdown("<p style='text-align:center; color:grey;'>No messages yet. Start a conversation!</p>", unsafe_allow_html=True)
else:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


# React to user input
if prompt := st.chat_input("Type your message here"):
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Simplify: Remove 'key' argument from controller.get for this test
    user_api = controller.get('user_api')
    user_model = controller.get('user_model')

    # Get selected subject and lesson from session_state (set by Tester.py's sidebar)
    selected_subject_from_tester = st.session_state.get('sb_subject_tester')
    
    # Get the detailed lesson contexts (list of dicts with id, name, url)
    # This is populated by Tester.py
    selected_lesson_details_for_ai = st.session_state.get('selected_lesson_contexts', [])
    
    # Retrieve content from uploaded files, if any
    uploaded_content_for_prompt = st.session_state.get("uploaded_file_content", "")

    # Generate and display assistant response
    with st.chat_message("assistant"):
        with st.spinner("AI is thinking..."):
            ai_response = genRes(
                prompt,  # The user's direct chat input
                st.session_state.messages, 
                user_api,
                user_model, # Pass the user_model
                selected_subject_from_tester, # Pass selected subject
                selected_lesson_data_list=selected_lesson_details_for_ai, # Pass the detailed list
                uploaded_file_text=uploaded_content_for_prompt # Pass content from uploaded files
            )
            # Ensure ai_response is not None before attempting to markdown.
            if ai_response is not None:
                st.markdown(ai_response)
            else:
                st.markdown("Error: No response from AI.")
    # Add assistant response to chat history
    if ai_response is not None:
        st.session_state.messages.append({"role": "assistant", "content": ai_response})