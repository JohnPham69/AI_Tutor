import streamlit as st
from Prac_AI import generate_quiz_data, evaluate_user_answer_clarity
import streamlit.components.v1 as components
from random import randint
import time
import os
from app_translations import get_translator # Import translator
from app_utils import get_cookie_controller # Import the singleton controller
from StResult import AddNewResult

# --- Constants ---
QUIZ_STATE_INITIAL = "initial"
QUIZ_STATE_CONFIG = "config"
QUIZ_STATE_QUESTIONING = "questioning"
QUIZ_STATE_GRADING_FEEDBACK = "grading_feedback"
FEEDBACK_STATUS_CORRECT = "correct"
FEEDBACK_STATUS_INCORRECT = "incorrect"
FEEDBACK_STATUS_ERROR = "error"

# --- Session state init ---
def ensure_session():
    default_values = {
        "quiz_step": QUIZ_STATE_INITIAL,
        "num_questions_to_ask": 0,
        "current_question_idx": 0,
        "user_answers": {},
        "feedback": {},
        "generated_quiz_data": [],
        "quiz_error_message": None,
        "time_for_each": 60,
    }
    for key, val in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = val

ensure_session()
_ = get_translator() # Initialize translator for this page
controller = get_cookie_controller() # Use the cached singleton instance
st.title(_("Practice Quiz Title"))


# --- Reset function ---
def reset_quiz_state(set_step_to_initial=True):
    if set_step_to_initial:
        st.session_state.quiz_step = QUIZ_STATE_INITIAL
    st.session_state.num_questions_to_ask = 0
    st.session_state.current_question_idx = 0
    st.session_state.user_answers = {}
    st.session_state.feedback = {}
    st.session_state.generated_quiz_data = []
    st.session_state.quiz_error_message = None
    st.session_state.time_for_each = 60

# --- Refresher function ---
def refresher(seconds):
    while True:
        time.sleep(seconds)
        mainDir = os.path.dirname(__file__)
        filePath = os.path.join(mainDir, 'dummy.py')
        with open(filePath, 'w') as f:
            f.write(f'# {randint(0, 10000)}')
            # The following line will raise NameError due to `idx` and `current` not being in scope.
            # It is translated assuming these variables would be correctly scoped in a fixed version.
            st.session_state.feedback[idx] = {"message": _("Incorrect Feedback Message").format(correct_answer=current['answer']), "status": FEEDBACK_STATUS_INCORRECT}
            st.session_state.quiz_step = QUIZ_STATE_GRADING_FEEDBACK
            st.rerun()
timeout = 0

# --- INITIAL STATE ---
if st.session_state.quiz_step == QUIZ_STATE_INITIAL:

    st.session_state.quiz_step = QUIZ_STATE_CONFIG
    st.rerun()

# --- CONFIG STATE ---
elif st.session_state.quiz_step == QUIZ_STATE_CONFIG:
    st.markdown(_("Configure Your Quiz"))
    # Get current selections from session state (set by Tester.py sidebar widgets)
    selected_grade_number = st.session_state.get('sb_grade_tester')
    selected_textbook_set_name = st.session_state.get('sb_textbook_set_tester')
    selected_subject_name = st.session_state.get("sb_subject_tester") # This is a string (subject name)
    # sb_lesson_tester from session_state is a list of selected lesson IDs (strings)
    raw_selected_lesson_ids_list = st.session_state.get("sb_lesson_tester", [])

    selected_lesson_id_for_quiz = None
    lesson_content_url_for_quiz = None

    if raw_selected_lesson_ids_list: # A lesson ID is selected from the multiselect
        selected_lesson_id_for_quiz = raw_selected_lesson_ids_list[0] # Use the first selected lesson ID for the quiz
        
        # Directly look up the URL using the full subject_lesson_data and current selections
        # This avoids relying on selected_lesson_contexts which might be stale due to st.navigation
        subject_data_from_session = st.session_state.get('subject_lesson_data_for_pages')
        if subject_data_from_session and selected_grade_number and \
           selected_textbook_set_name and selected_subject_name and selected_lesson_id_for_quiz:
            
            current_grade_info = next((g for g in subject_data_from_session.get("grade", []) if g.get("number") == selected_grade_number), None)
            if current_grade_info:
                current_textbook_set_info = next((ts for ts in current_grade_info.get("textbook_set", []) if ts.get("name") == selected_textbook_set_name), None)
                if current_textbook_set_info:
                    current_subject_info = next((s for s in current_textbook_set_info.get("subjects", []) if s.get("name") == selected_subject_name), None)
                    if current_subject_info:
                        lesson_detail_found = next(
                            (l_info for l_info in current_subject_info.get("link", []) if str(l_info.get("ID")) == selected_lesson_id_for_quiz),
                            None
                        )
                        if lesson_detail_found and lesson_detail_found.get("link"):
                            lesson_content_url_for_quiz = lesson_detail_found.get("link")

    # Inform user if subject/lesson is not selected for the quiz
    if not selected_subject_name and not selected_lesson_id_for_quiz:
        st.info(_("No subject or lesson selected from the sidebar. The quiz will cover general knowledge topics."))
    elif selected_lesson_id_for_quiz and not lesson_content_url_for_quiz:
        st.warning(_("A lesson (ID: {lesson_id}) was selected, but its content URL could not be found. The quiz may cover general topics for subject '{subject_name}'. Please check sidebar selections and data integrity.").format(lesson_id=selected_lesson_id_for_quiz, subject_name=selected_subject_name if selected_subject_name else _("N/A")))
    elif not selected_lesson_id_for_quiz: # Subject is selected, but no specific lesson
        st.info(_("No specific lesson selected from the sidebar for subject '{subject_name}'. The quiz will cover general topics for this subject.").format(subject_name=selected_subject_name))
    elif not selected_subject_name: # Lesson selected but somehow no subject (should be rare with sidebar logic)
        st.warning(_("A lesson is selected, but the subject is missing. Please check sidebar selections. The quiz may cover general knowledge topics."))
    num_q = st.number_input(_("Number of Questions Prompt"), 1, 20, value=5, step=1)
    num_time = st.number_input(_("Time Limit Prompt (minutes)"), 1, 30, value=10, step=1)
    type_of_question = st.selectbox(_("Type of Question Prompt"),
                                    options=[ _("Mixed"), _("Multiple Choice"), _("Long / Short Answer")],
                                    index=0)
    st.session_state.time_for_each = num_time * 60 / num_q
    st.markdown(_("Time Per Question Info").format(time_per_question=st.session_state.time_for_each))

    if st.button(_("Create Quiz and Start Button")):
        user_api_key = st.session_state.get('user_api')
        if not user_api_key:
            st.error(_("API key not configured, please set it in the Config page."))
        else:
            with st.spinner(_("Creating Quiz Spinner")):
                # Pass subject_name and the direct lesson_content_url
                data = generate_quiz_data(
                    num_questions=num_q, 
                    user_api=user_api_key, 
                    subject_name=selected_subject_name, 
                    lesson_id_str=selected_lesson_id_for_quiz, # Pass lesson_id_str
                    question_type=type_of_question,
                )
                st.session_state['selected_subject_name'] = selected_subject_name # Store in cookies for AI page
            if data and len(data) == num_q:
                st.session_state.generated_quiz_data = data
                st.session_state.num_questions_to_ask = num_q
                st.session_state.quiz_step = QUIZ_STATE_QUESTIONING
                st.rerun()
            else:
                st.error(_("Not Enough Questions Error"))
                st.session_state.generated_quiz_data = []

# --- QUESTIONING or FEEDBACK ---
elif st.session_state.quiz_step in [QUIZ_STATE_QUESTIONING, QUIZ_STATE_GRADING_FEEDBACK]:
    idx = st.session_state.current_question_idx
    total_questions_in_quiz = st.session_state.num_questions_to_ask # Renamed for clarity
    data = st.session_state.generated_quiz_data

    if not data or idx >= total_questions_in_quiz or idx >= len(data): # Quiz completed
        st.balloons()
        st.success(_("Quiz Completed Message"))
        
        num_correct_in_quiz = sum(1 for i in range(total_questions_in_quiz) if st.session_state.feedback.get(i, {}).get("status") == FEEDBACK_STATUS_CORRECT)
        st.markdown(_("Result Info").format(correct=num_correct_in_quiz, total=total_questions_in_quiz))
        
        # --- Logic to save results to the leaderboard ---
        
        # Get user info from cookies to see if we can save
        nick = st.session_state.get('user_nickname')
        school = st.session_state.get('user_school')
        class_name = st.session_state.get('user_class')
        student_id = st.session_state.get('user_id')
        subject_fin = st.session_state.get('selected_subject_name')

        # Check if all required user info is present before enabling the save button
        can_save = all([nick, school, class_name, student_id, subject_fin])
        
        if not can_save:
            st.warning(_("Save your own results!")) # Reusing a key that prompts user to save
            st.caption(_("Please fill in your Nickname, School, Class, and Student ID in the sidebar to save results."))

        col1, col2 = st.columns(2)
        with col1:
            # The "Add to Leaderboards" button now directly saves the result.
            if st.button(_("Add to Leaderboards"), disabled=not can_save):
                # Pass the results of the current quiz only. AddNewResult handles accumulation.
                save_successful = AddNewResult(nick, school, class_name, student_id, total_questions_in_quiz, num_correct_in_quiz, subject_fin)
                if save_successful:
                    st.success(_("Results saved."))
                    reset_quiz_state()
                    st.rerun()
                # AddNewResult shows its own error on failure.
        with col2:
            if st.button(_("Go Back Button")):
                reset_quiz_state()
                st.rerun()
    else:
        if st.session_state.quiz_step == QUIZ_STATE_QUESTIONING:
            # --- Countdown UI with HTML ---
            time_remaining_text = _("Time Remaining Label")
            # --- Display current question ---
            st.markdown(_("Question Number Info").format(current_idx_plus_1=idx + 1, total_questions=total_questions_in_quiz))
            current = data[idx]
            st.markdown(f"**{current['question']}**")

            answer = st.text_area(_("Your Answer Label"), key=f"answer_{idx}", value=st.session_state.user_answers.get(idx, ""))

            timeout = int(st.session_state.time_for_each)
            components.html(f"""
                <p>{time_remaining_text} <span id="myButton" >{_("Timer")}</span></p>
                
                <script>
                    // Countdown timer function
                    let countdown = {timeout}; // Set initial countdown value
                    const button = document.getElementById('myButton');
            
                    const interval = setInterval(() => {{
                    countdown--;
                    button.textContent = countdown;
            
                    if (countdown <= 0) {{
                        clearInterval(interval); // Stop the timer
                    }}
                    }}, 1000); // Update every second
                </script>
            """, height=80)
            
            col1, col2 = st.columns([0.82, 0.18])
            with col1:
                if st.button(_("Check Answer Button"), key=f"check_{idx}"):
                    st.session_state.user_answers[idx] = answer
                    key = st.session_state.get("user_api")
                    if not key:
                        st.error(_("API Key Missing In-Quiz Error"))
                        reset_quiz_state()
                        st.rerun()
                    with st.spinner(_("Grading Spinner")):
                        result = evaluate_user_answer_clarity(answer, current['answer'], current['question'], key)
                    if result == FEEDBACK_STATUS_CORRECT.upper(): # evaluate_user_answer_clarity returns "CORRECT" or "INCORRECT"
                        st.session_state.feedback[idx] = {"message": _("Correct Feedback Message"), "status": FEEDBACK_STATUS_CORRECT}
                    elif result == FEEDBACK_STATUS_INCORRECT.upper():
                        st.session_state.feedback[idx] = {"message": _("Incorrect Feedback Message").format(correct_answer=current['answer']), "status": FEEDBACK_STATUS_INCORRECT}
                    else:
                        st.session_state.feedback[idx] = {"message": _("Error Grading Feedback Message").format(correct_answer=current['answer']), "status": FEEDBACK_STATUS_ERROR}
                    st.session_state.quiz_step = QUIZ_STATE_GRADING_FEEDBACK
                    st.rerun()

            with col2:
                if st.button(_("Exit Quiz Button"), key=f"exit_{idx}_q"):
                    reset_quiz_state()
                    st.rerun()
            
            # Start the refresher thread
            refresher(timeout + 1)  # Start the refresher thread
                
            
        elif st.session_state.quiz_step == QUIZ_STATE_GRADING_FEEDBACK:
            feedback = st.session_state.feedback.get(idx, {})
            if feedback.get("status") == FEEDBACK_STATUS_CORRECT:
                st.success(feedback.get("message"))
            else:
                st.error(feedback.get("message"))

            col1, col2 = st.columns([0.82, 0.18])
            with col1:
                if st.button(_("Continue Button"), key=f"next_{idx}"):
                    st.session_state.current_question_idx += 1
                    st.session_state.quiz_step = QUIZ_STATE_QUESTIONING
                    st.rerun()
            with col2:
                if st.button(_("Exit Quiz Button"), key=f"exit_{idx}_fb"): # Consider a different key if it causes conflict, or reuse if intended
                    reset_quiz_state()
                    st.rerun()
        
