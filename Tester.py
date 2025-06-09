import streamlit as st
from streamlit_cookies_controller import CookieController
import requests # Added for fetching JSON
import json     # Added for parsing JSON

# Make a cookie controller
controller = CookieController()

chat_page = st.Page("./Test_AI_page.py", title = "Tutor AI", default = True)
practice = st.Page("./Test_practice_page.py", title="Practice / Quiz")

# Function to load subject/lesson data (can be a utility if used elsewhere)
@st.cache_data(ttl=3600) # Cache data for an hour
def load_subject_lesson_data():
    try:
        main_json_url = "https://raw.githubusercontent.com/JohnPham69/Quiz_Maker_AI/refs/heads/main/Grade11_test.json"
        response = requests.get(main_json_url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.sidebar.error(f"Failed to load lesson data: {e}")
        return {"subjects": []} # Return default structure on error

subject_lesson_data = load_subject_lesson_data()
with st.sidebar:
    # API key for chat
    st.subheader('Config')
    api_key_input = st.text_input(
            "API Key",
            placeholder="Enter your API key",
            label_visibility="collapsed",
            type="password",  # Use 'password' type for sensitive input
        )
    save_button = st.button("Save")
    if save_button:
        if api_key_input:
            controller.set('user_api', api_key_input)  # Save the API key in a cookie
            st.success("API key saved successfully!")
        else:
            st.warning("Please enter an API key.")

    # Chat Context Selection
    st.subheader("Chat Context")
    
    subject_list = subject_lesson_data.get("subjects", [])
    subject_names = [s["name"] for s in subject_list]
    if not subject_names: # Fallback
        subject_names = ["Geography", "History", "Biology"]

    # Initialize session state for selectbox keys if they don't exist
    if 'sb_subject_tester' not in st.session_state:
        st.session_state.sb_subject_tester = subject_names[0] if subject_names else None

    st.selectbox(
        "Subject?", 
        subject_names,
        key='sb_subject_tester' # Value stored in st.session_state.sb_subject_tester
    )

    lesson_ids = []
    selected_subject_val_tester = st.session_state.get('sb_subject_tester')
    if selected_subject_val_tester and subject_list:
        for subj_data in subject_list:
            if subj_data["name"] == selected_subject_val_tester:
                lesson_ids = [str(l["ID"]) for l in subj_data.get("link", [])]
                break
    if not lesson_ids: # Fallback
        lesson_ids = ["1", "2"]

    if 'sb_lesson_tester' not in st.session_state or st.session_state.get('sb_lesson_tester') not in lesson_ids:
        st.session_state.sb_lesson_tester = lesson_ids[0] if lesson_ids else None

    st.selectbox(
        "Lesson?", 
        lesson_ids,
        key='sb_lesson_tester' # Value stored in st.session_state.sb_lesson_tester
    )


pg = st.navigation([chat_page, practice])
pg.run()