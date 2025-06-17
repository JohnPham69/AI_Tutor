import streamlit as st
from streamlit_cookies_controller import CookieController
import requests # Added for fetching JSON
import json # Added for parsing JSON
from markitdown import MarkItDown # For converting files to text
import tempfile # For temporary files
import os
from st_clickable_images import clickable_images
from app_translations import get_translator, init_session_language # Import from new translations module

# Make a cookie controller
controller = CookieController()

# Initialize language settings (call once)
init_session_language()
_ = get_translator() # Get the translator instance

# NO_LESSON_OPTION_TEXT was previously defined here but is not used in this file.
# If it were needed for a selectbox option in this file, it would be:
# NO_LESSON_OPTION_TEXT = _("No lesson")

chat_page = st.Page("./Test_AI_page.py", title = _("Tutor AI"), default = True)
practice = st.Page("./Test_practice_page.py", title=_("Practice / Quiz"))
leaderboard_page = st.Page("./Test_leader_page.py", title=_("Leaderboard")) # New page for leaderboard

# Function to load subject/lesson data (can be a utility if used elsewhere)
@st.cache_data(ttl=3600) # Cache data for an hour
def load_subject_lesson_data():
    try:
        main_json_url = "https://raw.githubusercontent.com/JohnPham69/Quiz_Maker_AI/refs/heads/main/Grade11_test.json"
        response = requests.get(main_json_url)
        response.raise_for_status()
        return response.json()
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        st.sidebar.error(f"{_('Failed to load lesson data: ')}{e}")
        return {"subjects": []} # Return default structure on error

def set_language_and_trigger_rerun_flag(new_lang_code):
    """Sets the language and flags that a rerun is needed if the language changes."""
    if st.session_state.lang != new_lang_code:
        st.session_state.lang = new_lang_code
        st.session_state.changeLang = True # Set the flag indicating a language change occurred

subject_lesson_data = load_subject_lesson_data()
with st.sidebar:
    # API key
    st.subheader(_('Config'))

    nickname = st.text_input(
        ("Nickname"),
        placeholder=_("Enter your nickname here"),
        label_visibility="collapsed",
    )

    school = st.text_input(
        ("School"),
        placeholder=_("Enter your school name here"),
        label_visibility="collapsed",
    )

    studyClass = st.text_input(
        ("Class"),
        placeholder=_("Enter your class here"),
        label_visibility="collapsed",
    )

    StudentID = st.text_input(
        ("Student ID"),
        placeholder=_("Enter your Student ID here"),
        label_visibility="collapsed",
    )

    api_key_input = st.text_input(
            _("API Key"),
            placeholder=_("Enter your API key here"),
            label_visibility="collapsed",
            type="password",  # Use 'password' type for sensitive input
        )

    model_input = st.text_input(
        ("Model"),
        placeholder=_("Enter your model name here"),
        label_visibility="collapsed",
        )
    
    save_button = st.button(_("Save"))
    if save_button:
        if api_key_input: # Model input is optional, API key is essential
            st.success(_("Information saved successfully!"))
            controller.set('user_api', api_key_input)  # Save the API key in a cookie
            controller.set('user_model', model_input)
            controller.set('user_nickname', nickname)
            controller.set('user_school', school)
            controller.set('user_class', studyClass)
            controller.set('user_id', StudentID)
        else: # Only API key is strictly required for this part
            st.warning(_("Please enter your API key!!!"))


    # Chat Context Selection
    st.subheader(_("Adjust Context"))
    st.write(_("Select the language you desire."))
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
                img_style={"margin": "5px", "height": "24px", "width": "24px"},
            )
            if vi == 0:
                set_language_and_trigger_rerun_flag('vi')
            elif vi == 1:
                set_language_and_trigger_rerun_flag('en')


    # --- Grade Selection ---
    grade_data = subject_lesson_data.get("grade", [])
    grade_numbers = sorted(list(set(g["number"] for g in grade_data if "number" in g)))

    if 'sb_grade_tester' not in st.session_state:
        st.session_state.sb_grade_tester = grade_numbers[0] if grade_numbers else None

    selected_grade_number = st.selectbox(
        _("Grade?"),
        grade_numbers,
        key='sb_grade_tester'
    )

    # --- Textbook Set Selection ---
    textbook_set_names = []
    current_grade_info = next((g for g in grade_data if g.get("number") == selected_grade_number), None)
    if current_grade_info:
        textbook_set_names = [ts["name"] for ts in current_grade_info.get("textbook_set", []) if "name" in ts]

    if 'sb_textbook_set_tester' not in st.session_state:
        st.session_state.sb_textbook_set_tester = textbook_set_names[0] if textbook_set_names else None
    
    # If grade changes, reset textbook_set and subsequent selections if current textbook_set is not valid
    if selected_grade_number and st.session_state.sb_textbook_set_tester not in textbook_set_names:
        st.session_state.sb_textbook_set_tester = textbook_set_names[0] if textbook_set_names else None
        # Also reset subject and lessons as they depend on textbook_set
        st.session_state.sb_subject_tester = None
        st.session_state.sb_lesson_tester = []


    selected_textbook_set_name = st.selectbox(
        _("Textbook Set?"),
        textbook_set_names,
        key='sb_textbook_set_tester',
        disabled=not bool(textbook_set_names)
    )

    # --- Subject Selection (dependent on Grade and Textbook Set) ---
    subject_names = []
    current_textbook_set_info = None
    if current_grade_info and selected_textbook_set_name:
        current_textbook_set_info = next((ts for ts in current_grade_info.get("textbook_set", []) if ts.get("name") == selected_textbook_set_name), None)
        if current_textbook_set_info:
            subject_names = [s["name"] for s in current_textbook_set_info.get("subjects", []) if "name" in s]

    if 'sb_subject_tester' not in st.session_state:
        st.session_state.sb_subject_tester = subject_names[0] if subject_names else None    
    
    # If textbook_set changes, reset subject and lessons if current subject is not valid
    if selected_textbook_set_name and st.session_state.sb_subject_tester not in subject_names:
        st.session_state.sb_subject_tester = subject_names[0] if subject_names else None
        st.session_state.sb_lesson_tester = []

    selected_subject_name = st.selectbox(
        _("Subject?"),
        subject_names,
        key='sb_subject_tester',
        disabled=not bool(subject_names)
    )

    # --- Lesson Selection (dependent on Grade, Textbook Set, and Subject) ---
    actual_lesson_ids_for_multiselect = []
    current_subject_info = None
    if current_textbook_set_info and selected_subject_name:
        current_subject_info = next((s for s in current_textbook_set_info.get("subjects", []) if s.get("name") == selected_subject_name), None)
        if current_subject_info:
            actual_lesson_ids_for_multiselect = [str(l["ID"]) for l in current_subject_info.get("link", []) if "ID" in l]

    # Initialize or update session state for lesson multiselect
    if 'sb_lesson_tester' not in st.session_state or not isinstance(st.session_state.sb_lesson_tester, list):
        st.session_state.sb_lesson_tester = []

    # If subject changes, filter/reset lesson selection
    current_selection_from_state = st.session_state.get('sb_lesson_tester', [])
    valid_selection_for_current_subject = [
        lesson_id for lesson_id in current_selection_from_state if lesson_id in actual_lesson_ids_for_multiselect
    ]
    # Only update if the selection actually needs to change to avoid unnecessary reruns if the list of options changed but selection is still valid
    if st.session_state.sb_lesson_tester != valid_selection_for_current_subject:
        st.session_state.sb_lesson_tester = valid_selection_for_current_subject

    st.multiselect(
        _("Lesson(s)?"),
        options=actual_lesson_ids_for_multiselect,
        key='sb_lesson_tester', # Will store a list of selected lesson IDs
        placeholder=_("Choose lesson(s)") if actual_lesson_ids_for_multiselect else _("No lessons available"),
        disabled=not bool(actual_lesson_ids_for_multiselect)
    )

    # File Uploader for Context
    st.subheader(_("Upload Files for Context"))
    if 'uploaded_file_content' not in st.session_state:
        st.session_state.uploaded_file_content = ""
    if 'last_uploaded_file_names' not in st.session_state: # To detect changes in selection
        st.session_state.last_uploaded_file_names = []

    uploaded_files_new = st.file_uploader(
        _("Select file (e.g., .txt, .pptx, .pdf, .docx)"),
        accept_multiple_files=False,
        type=['txt', 'pptx', 'pdf', 'docx'], # MarkItDown will attempt to handle various types
        key="file_uploader_widget"
    )

    if uploaded_files_new:        
        processed_contents_current_upload = []

        # Since accept_multiple_files=False, uploaded_files_new is a single file object
        st.write(f"{_('Processing: ')}{uploaded_files_new.name} ({uploaded_files_new.size} bytes)")
        try:
            file_bytes = uploaded_files_new.getvalue()
            file_extension = os.path.splitext(uploaded_files_new.name)[1].lower()

            # Initialize MarkItDown instance based on file type
            if file_extension == ".pdf":
                # For PDF, user might want to use Document Intelligence.
                # This requires an endpoint: md_converter = MarkItDown(docintel_endpoint="<YOUR_AZURE_DOCINTEL_ENDPOINT>")
                # Using default MarkItDown() for PDF if no endpoint is specified.
                md_converter = MarkItDown()
            elif file_extension in [".xlsx", ".xls"]:
                md_converter = MarkItDown(enable_plugins=False) # As per your example
            else:
                md_converter = MarkItDown() # General case for other file types

            # MarkItDown works with file paths. Create a temporary file.
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension, mode='wb') as tmp_file:
                tmp_file.write(file_bytes)
                temp_file_path = tmp_file.name
            
            try:
                result = md_converter.convert(temp_file_path)
                processed_contents_current_upload.append(result.text_content)
            except Exception as e:
                st.error(f"{_('MarkItDown error for ')}{uploaded_files_new.name}: {e}")
            finally:
                os.unlink(temp_file_path) # Ensure temporary file is deleted

        except Exception as e:
            st.error(f"{_('Error reading/preparing ')}{uploaded_files_new.name}: {e}")
        
        if processed_contents_current_upload:
            st.session_state.uploaded_file_content = "\n\n--- Uploaded File Content Separator ---\n\n".join(processed_contents_current_upload)
            st.success(_("File processed and saved.")) # Adjusted message for single file
        else:
            st.session_state.uploaded_file_content = ""
            if uploaded_files_new: # Check if a file was uploaded but processing failed
                st.warning(_("Could not retrieve file data."))
        st.session_state.last_uploaded_file_names = [uploaded_files_new.name] if uploaded_files_new else []
    elif not uploaded_files_new and st.session_state.last_uploaded_file_names: # Files were cleared
        st.session_state.uploaded_file_content = ""
        st.session_state.last_uploaded_file_names = []
        st.info(_("No file uploaded."))

# Perform rerun if a language change was flagged
# This is done after all sidebar interactions for the current pass are complete
if st.session_state.get('changeLang', False):
    st.session_state.changeLang = False # Reset the flag
    st.rerun()

pg = st.navigation([chat_page, practice, leaderboard_page]) # Added leaderboard_page to navigation
pg.run()