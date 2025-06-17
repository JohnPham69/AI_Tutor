import streamlit as st
from streamlit_cookies_controller import CookieController
from Prac_AI import generate_quiz_data, evaluate_user_answer_clarity
import streamlit.components.v1 as components
from random import randint
import time
import os
from app_translations import get_translator # Import translator

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
controller = CookieController()
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
    st.markdown(_("Start New Practice Session"))
    if st.session_state.quiz_error_message:
        st.error(st.session_state.quiz_error_message)
        st.session_state.quiz_error_message = None

    if st.button(_("Start Quiz Button")):
        st.session_state.quiz_step = QUIZ_STATE_CONFIG
        st.rerun()
    st.caption(_("Based on Sidebar Selection"))

# --- CONFIG STATE ---
elif st.session_state.quiz_step == QUIZ_STATE_CONFIG:
    st.markdown(_("Configure Your Quiz"))
    selected_subject = st.session_state.get("sb_subject_tester") # This is a string (subject name)
    # sb_lesson_tester from session_state is a list of selected lesson IDs (strings)
    raw_selected_lesson_ids_list = st.session_state.get("sb_lesson_tester", [])

    selected_lesson_for_quiz = None
    if raw_selected_lesson_ids_list: # Check if the list of selected lessons is not empty
        selected_lesson_for_quiz = raw_selected_lesson_ids_list[0] # Use the first selected lesson for the quiz

    num_q = st.number_input(_("Number of Questions Prompt"), 1, 20, value=5, step=1)
    num_time = st.number_input(_("Time Limit Prompt (minutes)"), 1, 30, value=10, step=1)

    st.session_state.time_for_each = num_time * 60 / num_q
    st.markdown(_("Time Per Question Info").format(time_per_question=st.session_state.time_for_each))

    if st.button(_("Create Quiz and Start Button")):
        user_api_key = controller.get("user_api")
        if not user_api_key:
            st.error(_("API Key Missing Error Config"))
        else:
            with st.spinner(_("Creating Quiz Spinner")):
                data = generate_quiz_data(num_q, user_api_key, selected_subject, selected_lesson_for_quiz)
            if data and len(data) == num_q:
                st.session_state.generated_quiz_data = data
                st.session_state.num_questions_to_ask = num_q
                st.session_state.quiz_step = QUIZ_STATE_QUESTIONING
                st.rerun()
            else:
                st.error(_("Not Enough Questions Error"))
                st.session_state.generated_quiz_data = []

    if st.button(_("Go Back Button")):
        reset_quiz_state()
        st.rerun()

# --- QUESTIONING or FEEDBACK ---
elif st.session_state.quiz_step in [QUIZ_STATE_QUESTIONING, QUIZ_STATE_GRADING_FEEDBACK]:
    idx = st.session_state.current_question_idx
    total = st.session_state.num_questions_to_ask
    data = st.session_state.generated_quiz_data

    if not data or idx >= total or idx >= len(data):
        st.balloons()
        st.success(_("Quiz Completed Message"))
        correct = sum(1 for i in range(total) if st.session_state.feedback.get(i, {}).get("status") == FEEDBACK_STATUS_CORRECT)
        st.markdown(_("Result Info").format(correct=correct, total=total))
        if st.button(_("Do Another Quiz Button")):
            reset_quiz_state()
            st.rerun()
    else:
        if st.session_state.quiz_step == QUIZ_STATE_QUESTIONING:
            # --- Countdown UI with HTML ---
            time_remaining_text = _("Time Remaining Label")
            # --- Display current question ---
            st.markdown(_("Question Number Info").format(current_idx_plus_1=idx + 1, total_questions=total))
            current = data[idx]
            st.markdown(f"**{current['question']}**")

            answer = st.text_area(_("Your Answer Label"), key=f"answer_{idx}", value=st.session_state.user_answers.get(idx, ""))

            timeout = int(st.session_state.time_for_each)
            components.html(f"""
                <p>{time_remaining_text} <span id="myButton" >Timer</span></p>
                
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
                    key = controller.get("user_api")
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
        
