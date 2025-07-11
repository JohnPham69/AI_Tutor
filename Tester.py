import os

import streamlit as st
from streamlit.components.v1 import html

import requests # Added for fetching JSON
import json # Added for parsing JSON
import os
from st_clickable_images import clickable_images
from app_translations import get_translator, init_session_language # Import from new translations module
import streamlit.components.v1 as components
from app_utils import get_cookie_controller
from streamlit_cookies_manager import CookieManager

# This should be on top of your script
cookies = CookieManager()
if not cookies.ready():
    # Wait for the component to load and send us current cookies.
    st.spinner()
    st.stop()

controller = get_cookie_controller()
# Initialize language settings (call once)
init_session_language()
_ = get_translator() # Get the translator instance

# NO_LESSON_OPTION_TEXT was previously defined here but is not used in this file.
# If it were needed for a selectbox option in this file, it would be:
# NO_LESSON_OPTION_TEXT = _("No lesson")

chat_page = st.Page("./aitutor.py", title = _("Tutor AI"))
practice = st.Page("./practice.py", title=_("Practice"))
leaderboard_page = st.Page("./leaderboard.py", title=_("Leaderboard")) # New page for leaderboard
learning_page = st.Page("./learn.py", title=_("Learning with AI"), default = True) # New page for learning

# Function to load subject/lesson data (can be a utility if used elsewhere)
@st.cache_data(ttl=3600) # Cache data for an hour
def load_subject_lesson_data():
    try:
        main_json_url = "https://raw.githubusercontent.com/JohnPham69/Quiz_Maker_AI/refs/heads/main/lessons/GTSL.json"
        response = requests.get(main_json_url)
        response.raise_for_status()
        return response.json()
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        st.sidebar.error(f"{_('Failed to load lesson data: ')}{e}")
        return {"grade": []} # Return default structure with "grade" key on error

# Function to fetch and display lesson content (moved from AI_page.py)
def fetch_and_display_lessons():
    # Ensure messages list exists in session_state, initialize if not.
    # This is important because this function is now in Tester.py and might be called
    # before AI_page.py initializes st.session_state.messages.
    if "messages" not in st.session_state:
        st.session_state.messages = []

    selected_lesson_details = st.session_state.get('selected_lesson_contexts', [])
    if not selected_lesson_details:
        st.session_state.messages.append({"role": "assistant", "content": _("No lessons selected from the sidebar.")})
    else:
        combined_lesson_content = []
        for lesson_detail in selected_lesson_details:
            lesson_id = lesson_detail.get('id', 'UnknownID')
            lesson_name = lesson_detail.get('name', f'Lesson {lesson_id}')
            lesson_url = lesson_detail.get('url')

            if lesson_url:
                try:
                    response = requests.get(lesson_url)
                    response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                    content = response.text
                    combined_lesson_content.append(f"{content}")
                except requests.exceptions.RequestException as e:
                    combined_lesson_content.append(f"### {_('Failed to fetch content for Lesson')} '{lesson_name}' (ID {lesson_id})\n\n{_('Error')}: {e}")
            else:
                 combined_lesson_content.append(f"### {_('Missing URL for Lesson')} '{lesson_name}' (ID {lesson_id})")

        if combined_lesson_content:
            full_content_message = "\n\n---\n\n".join(combined_lesson_content)
            st.session_state.messages.append({"role": "assistant", "content": full_content_message})
        else:
            st.session_state.messages.append({"role": "assistant", "content": _("Could not retrieve content for any selected lesson.")})
    st.rerun()

def set_language_and_trigger_rerun_flag(new_lang_code):
    # Ensure 'lang' is initialized before comparing
    st.session_state.lang = st.session_state.get('lang', 'vi') # Default to 'vi' if not set
    if st.session_state.lang != new_lang_code:
        st.session_state.lang = new_lang_code
        st.session_state.changeLang = True # Set the flag indicating a language change occurred

subject_lesson_data = load_subject_lesson_data()
st.session_state.subject_lesson_data_for_pages = subject_lesson_data # Store for other pages to access

def ChangeWidgetFontSize(wgt_txt, wch_font_size = '12px'):
    htmlstr = """<script>var elements = window.parent.document.querySelectorAll('*'), i;
                    for (i = 0; i < elements.length; ++i) { if (elements[i].innerText == |wgt_txt|) 
                        { elements[i].style.fontSize='""" + wch_font_size + """';} } </script>  """

    htmlstr = htmlstr.replace('|wgt_txt|', "'" + wgt_txt + "'")
    components.html(f"{htmlstr}", height=0, width=0)


PAGES = {
    "Tutor AI": chat_page,
    "Practice / Quiz": practice,
    "Leaderboard": leaderboard_page,
    "Learning": learning_page, # New page for learning
    # Add more pages here as needed
}

pg_selection = st.navigation(list(PAGES.values()), position="hidden") # Convert .values() to a list
#if pg_selection: # Check if a page was selected (pg_selection is the Page object)
#    pg_selection.run()

with st.sidebar:
    # To here, feel free to expand in between
    #Start Logo
    st.write("")
    st.logo(
        image = "https://github.com/JohnPham69/AI_Tutor/blob/be788c9e48670e9a01f0173ee5a3d171482523e6/img/logo.png?raw=true",
        size = "large", # Adjusted size for sidebar,
        link = "https://github.com/JohnPham69/AI_Tutor/blob/be788c9e48670e9a01f0173ee5a3d171482523e6/img/logo.png?raw=true",
        icon_image= "https://github.com/JohnPham69/AI_Tutor/blob/main/img/aitutors_logo.png?raw=true",
    )
    
    # Inject custom CSS to make the logo bigger
    st.html("""
    <style>
        [alt=Logo] {
            margin-top: 100px !important;
            height: 100px; /* Set logo height to approximately 100px */
        }        
    </style>
    """)
    # End Logo
    st.write("")
    st.write("")
    # Container for languages
    with st.container():
        # Adjusted columns for language buttons
        col1, _unused_col = st.columns([0.7, 0.3]) # Use 2 columns for buttons, rest for spacing if needed
        with col1:
            vi = clickable_images(
                [
                    "https://github.com/JohnPham69/Quiz_Maker_AI/blob/main/img/Vietnam-Flag.png?raw=true",  # Vietnamese flag
                    "https://github.com/JohnPham69/Quiz_Maker_AI/blob/main/img/United-Kingdom-Flag.png?raw=true",  # UK flag
                ],
                div_style={"display": "flex", "justify-content": "left", "flex-wrap": "wrap"},
                img_style={"margin": "5px", "height": "30px", "width": "30px"},
            )
            if vi == 0:
                set_language_and_trigger_rerun_flag('vi')
            elif vi == 1:
                set_language_and_trigger_rerun_flag('en')
    with st.expander(r"$\textsf{\large " + ("📚\t") +  _("Adjust Context") + "}$"): #Can change Large into Huge and footnotesize
        # --- Callbacks and flags for sidebar selectboxes to manage cascading updates ---
        def grade_changed_callback():
            st.session_state.user_interacted_grade = True

        def textbook_set_changed_callback():
            st.session_state.user_interacted_textbook_set = True

        def subject_changed_callback():
            st.session_state.user_interacted_subject = True

        # Initialize interaction flags if they don't exist
        if 'user_interacted_grade' not in st.session_state:
            st.session_state.user_interacted_grade = False
        if 'user_interacted_textbook_set' not in st.session_state:
            st.session_state.user_interacted_textbook_set = False
        if 'user_interacted_subject' not in st.session_state:
            st.session_state.user_interacted_subject = False
        if 'sb_grade_tester_initialized' not in st.session_state: # To handle first run logic
            st.session_state.sb_grade_tester_initialized = False


        # --- Grade Selection ---
        grade_data = subject_lesson_data.get("grade", [])
        grade_numbers = sorted(list(set(g["number"] for g in grade_data if "number" in g)))
        grade_label_to_value = {f"{_("Grade")} {n}": n for n in grade_numbers}
        grade_labels = list(grade_label_to_value.keys())

        if 'sb_grade_tester_label' not in st.session_state:
            st.session_state.sb_grade_tester_label = None

        selected_grade_label = st.selectbox(
            _("Grade?"),
            grade_labels,
            key='sb_grade_tester_label',
            label_visibility="collapsed",
            placeholder=_("Choose grade"),
        )
        selected_grade_number = grade_label_to_value[selected_grade_label] if selected_grade_label else None
        st.session_state.sb_grade_tester = selected_grade_number

        # --- Textbook Set Selection ---
        textbook_set_names = []
        current_grade_info = next((g for g in grade_data if g.get("number") == selected_grade_number), None)
        if current_grade_info:
            textbook_set_names = [ts["name"] for ts in current_grade_info.get("textbook_set", []) if "name" in ts]
        textbook_set_label_to_value = {_("Set") + " " + f"{name}": name for name in textbook_set_names}
        textbook_set_labels = list(textbook_set_label_to_value.keys())

        if 'sb_textbook_set_tester_label' not in st.session_state:
            st.session_state.sb_textbook_set_tester_label = None

        selected_textbook_set_label = st.selectbox(
            _("Textbook Set?"),
            textbook_set_labels,
            key='sb_textbook_set_tester_label',
            label_visibility="collapsed",
            placeholder=_("Choose textbook set"),
            disabled=not bool(textbook_set_labels),
        )
        selected_textbook_set_name = textbook_set_label_to_value[selected_textbook_set_label] if selected_textbook_set_label else None
        st.session_state.sb_textbook_set_tester = selected_textbook_set_name

        # --- Subject Selection ---
        subject_names = []
        current_textbook_set_info = None
        if current_grade_info and selected_textbook_set_name:
            current_textbook_set_info = next((ts for ts in current_grade_info.get("textbook_set", []) if ts.get("name") == selected_textbook_set_name), None)
            if current_textbook_set_info:
                subject_names = [s["name"] for s in current_textbook_set_info.get("subjects", []) if "name" in s]

        if 'sb_subject_tester' not in st.session_state:
            st.session_state.sb_subject_tester = None

        selected_subject_name = st.selectbox(
            _("Subject?"),
            subject_names,
            key='sb_subject_tester',
            label_visibility="collapsed",
            placeholder=_("No subjects available"),
            disabled=not bool(subject_names),
        )

        # --- Lesson Multiselect ---
        actual_lesson_ids_for_multiselect = []
        lesson_label_to_value = {}
        current_subject_info = None
        if current_textbook_set_info and selected_subject_name:
            current_subject_info = next((s for s in current_textbook_set_info.get("subjects", []) if s.get("name") == selected_subject_name), None)
            if current_subject_info:
                actual_lesson_ids_for_multiselect = [str(l["ID"]) for l in current_subject_info.get("link", []) if "ID" in l]
                lesson_label_to_value = {_("Lesson") + " " + f"{lesson_id}": lesson_id for lesson_id in actual_lesson_ids_for_multiselect}
        lesson_labels = list(lesson_label_to_value.keys())

        if 'sb_lesson_tester_labels' not in st.session_state:
            st.session_state.sb_lesson_tester_labels = []

        def get_lesson_ids_from_labels(labels):
            return [lesson_label_to_value[label] for label in labels if label in lesson_label_to_value]

        selected_lesson_labels = st.multiselect(
            _("Lesson(s)?"),
            options=lesson_labels,
            label_visibility="collapsed",
            key='sb_lesson_tester_labels',
            placeholder=_("Choose lesson(s)") if lesson_labels else _("No lessons available"),
            disabled=not bool(lesson_labels)
        )
        st.session_state.sb_lesson_tester = get_lesson_ids_from_labels(st.session_state.sb_lesson_tester_labels)

        # --- "Select All" Checkbox for Lessons ---
        # The value of the checkbox is determined by whether all available lessons are currently selected.
        # This makes the checkbox state reflect manual selections in the multiselect.
        all_selected = (
            len(st.session_state.get('sb_lesson_tester', [])) == len(actual_lesson_ids_for_multiselect)
            and bool(actual_lesson_ids_for_multiselect)
        )

        def on_select_all_change():
            """Callback to select or deselect all lessons by label."""
            if st.session_state.select_all_lessons_cb:
                st.session_state.sb_lesson_tester_labels = lesson_labels
            else:
                st.session_state.sb_lesson_tester_labels = []

        st.checkbox(
            _("Select all lessons"),
            value=all_selected,
            key="select_all_lessons_cb",
            on_change=on_select_all_change,
            disabled=not bool(lesson_labels)
        )

        # "View Lesson" button and its subheader, now in Tester.py's sidebar
        if st.button(_("View Lesson Button")):
            fetch_and_display_lessons()

        # Initialize or update selected_lesson_contexts based on sb_lesson_tester
        if 'selected_lesson_contexts' not in st.session_state:
            st.session_state.selected_lesson_contexts = []

        new_selected_lesson_contexts = []
        if current_subject_info and 'sb_lesson_tester' in st.session_state:
            selected_ids_from_multiselect = st.session_state.sb_lesson_tester # List of selected ID strings
            all_lessons_for_current_subject = current_subject_info.get("link", [])
            for lesson_id_str_selected in selected_ids_from_multiselect:
                lesson_detail_found = next(
                    (l_info for l_info in all_lessons_for_current_subject if str(l_info.get("ID")) == lesson_id_str_selected),
                    None
                )
                if lesson_detail_found and lesson_detail_found.get("link"): # Ensure 'link' (URL) exists
                    new_selected_lesson_contexts.append({
                        "id": str(lesson_detail_found.get("ID")),
                        "name": lesson_detail_found.get("name", f"Lesson {lesson_detail_found.get('ID')}"), # Fallback name
                        "url": lesson_detail_found.get("link") # This is the .md URL
                    })
        st.session_state.selected_lesson_contexts = new_selected_lesson_contexts

    with st.expander(r"$\textsf{\large " + ("📜\t") + _("Study") + "}$", expanded=True):
        st.page_link("learn.py", label=_("Learning with AI"), icon="🐻") # New page link with icon
        st.page_link("aitutor.py", label=_("Tutor AI"), icon="🐯") # Page link with icon
        st.page_link("practice.py", label=_("Practice"), icon="🐼") # Page link with icon
        st.page_link("leaderboard.py", label=_("Leaderboard"), icon="🎓") # New page link with icon

    with st.expander(r"$\textsf{\large " + ("🔧\t") + _('Config') + "}$"): # Can change Large into Huge and footnotesize

        nickname = st.text_input(
            ("Nickname"),
            value="",
            placeholder=_("Enter your nickname here"),
            label_visibility="collapsed",
        )

        school = st.text_input(
            ("School"),
            value="",
            placeholder=_("Enter your school name here"),
            label_visibility="collapsed",
        )

        studyClass = st.text_input(
            ("Class"),
            value="",
            placeholder=_("Enter your class here"),
            label_visibility="collapsed",
        )

        StudentID = st.text_input(
            ("Student ID"),
            value="",
            placeholder=_("Enter your Student ID here"),
            label_visibility="collapsed",
        )

        api_key_input = st.text_input(
            _("API Key"),
            value="",
            placeholder=_("Enter your API key here"),
            label_visibility="collapsed",
            type="password",
            key="sidebar_api_key_input_tester"
        )

        model_input = st.text_input(
            ("Model"),
            value="",
            placeholder=_("Enter your model name here"),
            label_visibility="collapsed",
            key="sidebar_model_input_tester" # Added key
            )
        save_button = st.button(("💾\t") + _("Save"), key="sidebar_save_button_tester")
        
        
        # Session state for managing the cookie set/get flow for debugging
        if 'trigger_cookie_read_tester' not in st.session_state:
            st.session_state.trigger_cookie_read_tester = False
        if 'saved_api_key_value_for_debug_tester' not in st.session_state:
            st.session_state.saved_api_key_value_for_debug_tester = None

        if save_button:
            if api_key_input:

                cookies.set('user_api', api_key_input)
                cookies.set('user_model', model_input)
                cookies.set('user_nickname', nickname)
                cookies.set('user_school', school)
                cookies.set('user_class', studyClass)
                cookies.set('user_id', StudentID)

                # Sync to st.session_state as well
                st.session_state['user_api'] = api_key_input
                st.session_state['user_model'] = model_input
                st.session_state['user_nickname'] = nickname
                st.session_state['user_school'] = school
                st.session_state['user_class'] = studyClass
                st.session_state['user_id'] = StudentID
                st.sidebar.success(_("API key saved successfully!"))
                st.rerun()
            else:
                st.warning(_("Please enter your API key!!!"))
        
        if st.session_state.trigger_cookie_read_tester:
            st.session_state.trigger_cookie_read_tester = False # Reset flag
            st.session_state.saved_api_key_value_for_debug_tester = None
    
    # --- How to get API key (get_api button) ---
    if st.button(_("FAQ - Frequently Asked Question")):
        if st.session_state.lang == "vi":
            howto_url = "https://raw.githubusercontent.com/JohnPham69/AI_Tutor/refs/heads/main/lessons/guideline/FAQ_vi.md"
            try:
                response = requests.get(howto_url)
                response.raise_for_status()
                content = response.text
                # Ensure messages list exists
                if "messages" not in st.session_state:
                    st.session_state.messages = []
                st.session_state.messages.append({"role": "assistant", "content": content})
            except requests.exceptions.RequestException as e:
                if "messages" not in st.session_state:
                    st.session_state.messages = []
                st.session_state.messages.append({"role": "assistant", "content": f"### {_('Failed to fetch guideline')}\n\n{_('Error')}: {e}"})
            st.rerun()
        else:
            howto_url = "https://raw.githubusercontent.com/JohnPham69/AI_Tutor/refs/heads/main/lessons/guideline/FAQ_en.md"
            try:
                response = requests.get(howto_url)
                response.raise_for_status()
                content = response.text
                # Ensure messages list exists
                if "messages" not in st.session_state:
                    st.session_state.messages = []
                st.session_state.messages.append({"role": "assistant", "content": content})
            except requests.exceptions.RequestException as e:
                if "messages" not in st.session_state:
                    st.session_state.messages = []
                st.session_state.messages.append({"role": "assistant", "content": f"### {_('Failed to fetch guideline')}\n\n{_('Error')}: {e}"})
            st.rerun()
# Perform rerun if a language change was flagged
    # Donate code here
    
    
    
    if st.session_state.lang == "vi":
        st.image("https://github.com/JohnPham69/AI_Tutor/blob/20f1dbaab05539835da73852e9f4777e1744e38f/img/donate_vi.png?raw=true")
    else:
        st.image("https://github.com/JohnPham69/AI_Tutor/blob/20f1dbaab05539835da73852e9f4777e1744e38f/img/donate_en.png?raw=true")
    
    if st.session_state.lang == "vi":
        st.markdown("[![Foo](https://github.com/JohnPham69/AI_Tutor/blob/ffb33cc79817f02b6eb8ed06ae43a1c97d4dbbc3/img/DONATION__VI.png?raw=true)](https://github.com/JohnPham69/AI_Tutor)")
    else:
        st.markdown("[![Foo](https://github.com/JohnPham69/AI_Tutor/blob/ffb33cc79817f02b6eb8ed06ae43a1c97d4dbbc3/img/DONATION__EN.png?raw=true)](https://github.com/JohnPham69/AI_Tutor)")


pg_selection.run() # Run the selected page

st.session_state['user_api'] = cookies.get('user_api')

if st.session_state.get('changeLang', False):
    st.session_state.changeLang = False # Reset the flag
    st.rerun()
