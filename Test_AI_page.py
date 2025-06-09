import streamlit as st
from StAI import genRes
from streamlit_cookies_controller import CookieController

# Make a cookie controller
controller = CookieController()

# Custom CSS
st.markdown("""
    <style>
        /* Sticky Title under navbar */
        .sticky-title {
            position: fixed;
            top: 6.5vh;
            left: 0;
            width: 100%;
            background-color: white;
            font-size: 1.5rem;
            font-weight: bold;
            z-index: 1001;
            border-bottom: 1px solid #ddd;
            text-align: center;
        }
        </style>
""", unsafe_allow_html=True)

# Title
st.markdown('<div class="sticky-title">Quiz Maker AI</div>', unsafe_allow_html=True)

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
    user_api = controller.get('user_api')  # Get the API key from the cookie

    # Get selected subject and lesson from session_state (set by Tester.py's sidebar)
    selected_subject_from_tester = st.session_state.get('sb_subject_tester')
    selected_lesson_from_tester = st.session_state.get('sb_lesson_tester')

    # Generate and display assistant response
    with st.chat_message("assistant"):
        with st.spinner("AI is thinking..."):                
            ai_response = genRes(
                prompt, 
                st.session_state.messages, 
                user_api, 
                selected_subject_from_tester, # Pass selected subject
                selected_lesson_from_tester   # Pass selected lesson
            )
            # Ensure ai_response is not None before attempting to markdown.
            # genRes is expected to return a string, even for errors.
            if ai_response is not None:
                st.markdown(ai_response)
            else:
                st.markdown("Error: No response from AI.")
    # Add assistant response to chat history
    if ai_response is not None:
        st.session_state.messages.append({"role": "assistant", "content": ai_response})