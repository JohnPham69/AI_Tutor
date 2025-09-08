import streamlit as st
from Prac_AI import generate_quiz_data, evaluate_user_answer_clarity
import streamlit.components.v1 as components
from random import randint
import time
import json
import requests
import os
from app_translations import get_translator  # Import translator
from app_utils import get_cookie_controller  # Import the singleton controller
from StResult import AddNewResult
#
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
        "quiz_step": QUIZ_STATE_CONFIG,
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

_ = get_translator()  # Initialize translator for this page
controller = get_cookie_controller()  # Use the cached singleton instance
st.title(_("Practice Quiz Title"))

# --- Reset function ---
def reset_quiz_state(set_step_to_initial=True):
    if set_step_to_initial:
        st.session_state.quiz_step = QUIZ_STATE_INITIAL
    else:
        st.session_state.quiz_step = QUIZ_STATE_CONFIG
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

    # Get sidebar selections from session state
    selected_grade_number = st.session_state.get('sb_grade_tester')
    selected_textbook_set_name = st.session_state.get('sb_textbook_set_tester')
    selected_subject_name = st.session_state.get("sb_subject_tester")
    raw_selected_lesson_ids_list = st.session_state.get("sb_lesson_tester", [])

    # Use lesson content from session_state instead of refetching
    lesson_text = None
    if "lesson_contents" in st.session_state and st.session_state.lesson_contents:
        # Combine all lesson contents into one string
        lesson_text = "\n\n".join(st.session_state.lesson_contents)

    # Show info or warning based on selections
    if not selected_subject_name and not raw_selected_lesson_ids_list:
        st.info(_("No subject or lesson selected from the sidebar. The quiz will cover general knowledge topics."))
    elif not raw_selected_lesson_ids_list and selected_subject_name:
        st.info(_("No specific lesson selected from the sidebar for subject '{subject_name}'. The quiz will cover general topics for this subject.").format(subject_name=selected_subject_name))

    st.session_state.selected_subject_name = selected_subject_name
    
    
    # Always show quiz settings
    num_q = st.number_input(_("Number of Questions Prompt"), 1, 20, value=5, step=1)
    num_time = st.number_input(_("Time Limit Prompt (minutes)"), 1, 30, value=10, step=1)
    type_of_question = st.selectbox(_("Type of Question Prompt"),
                                    options=[_("Mixed"), _("Multiple Choice"), _("Long / Short Answer")],
                                    index=0)

    # Calculate time per question
    st.session_state.time_for_each = num_time * 60 / num_q
    st.markdown(_("Time Per Question Info").format(time_per_question=st.session_state.time_for_each))

    # Button to create quiz
    if st.button(_("Create Quiz and Start Button")):
        user_api_key = st.session_state.get('user_api')
        if not user_api_key:
            st.error(_("API key not configured, please set it in the Config page."))
        else:
            with st.spinner(_("Creating Quiz Spinner")):
                lesson_text = None
                if "lesson_contents" in st.session_state and st.session_state.lesson_contents:
                    lesson_text = "\n\n".join(st.session_state.lesson_contents)
                
                # Later in the quiz generation call:
                data = generate_quiz_data(
                    num_questions=num_q,
                    user_api=user_api_key,
                    subject_name=selected_subject_name,
                    lesson_id_str=raw_selected_lesson_ids_list[0] if raw_selected_lesson_ids_list else None,
                    question_type=type_of_question,
                    lesson_text=lesson_text,  # ✅ now supported
                )
                

            # Validate data and proceed
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
    total_questions_in_quiz = st.session_state.num_questions_to_ask
    data = st.session_state.generated_quiz_data

    if not data or idx >= total_questions_in_quiz or idx >= len(data):
        st.balloons()
        st.success(_("Quiz Completed Message"))

        num_correct_in_quiz = sum(1 for i in range(total_questions_in_quiz) if st.session_state.feedback.get(i, {}).get("status") == FEEDBACK_STATUS_CORRECT)
        st.markdown(_("Result Info").format(correct=num_correct_in_quiz, total=total_questions_in_quiz))

        # Save results
        nick = st.session_state.get('user_nickname')
        school = st.session_state.get('user_school')
        class_name = st.session_state.get('user_class')
        student_id = st.session_state.get('user_id')
        subject_fin = (
            st.session_state.get('selected_subject_name')
            or st.session_state.get('user_sub')  # ← this is synced from Tester.py cookies
        )

        can_save = all([nick, school, class_name, student_id, subject_fin])

        if not can_save:
            st.warning(_("Save your own results!"))
            st.caption(_("Please fill in your Nickname, School, Class, and Student ID in the sidebar to save results."))

        col1, col2 = st.columns(2)
        with col1:
            if st.button(_("Add to Leaderboards"), disabled=not can_save):
                save_successful = AddNewResult(nick, school, class_name, student_id, total_questions_in_quiz, num_correct_in_quiz, subject_fin)
                if save_successful:
                    st.success(_("Results saved."))
                    reset_quiz_state()
                    st.rerun()
        with col2:
            if st.button(_("Go Back Button")):
                reset_quiz_state()
                st.rerun()

    else:
        if st.session_state.quiz_step == QUIZ_STATE_QUESTIONING:
            time_remaining_text = _("Time Remaining Label")
            st.markdown(_("Question Number Info").format(current_idx_plus_1=idx + 1, total_questions=total_questions_in_quiz))
            current = data[idx]
            st.markdown(f"**{current['question']}**")

            answer = st.text_area(_("Your Answer Label"), key=f"answer_{idx}", value=st.session_state.user_answers.get(idx, ""))

            timeout = int(st.session_state.time_for_each)
            components.html(f"""
                <p>{time_remaining_text} <span id="myButton" >{_("Timer")}</span></p>
                <script>
                    let countdown = {timeout};
                    const button = document.getElementById('myButton');
                    const interval = setInterval(() => {{
                        countdown--;
                        button.textContent = countdown;
                        if (countdown <= 0) {{
                            clearInterval(interval);
                        }}
                    }}, 1000);
                </script>
            """, height=80)

            col1, col2 = st.columns([0.82, 0.18])
            with col1:
                if st.button(_("Check Answer Button"), key=f"check_{idx}"):
                    st.session_state.user_answers[idx] = answer
                    key = st.session_state.get("user_api")
                    if not key:
                        st.error(_("API Key Missing In-Quiz Error"))
                    with st.spinner(_("Grading Spinner")):
                        result = evaluate_user_answer_clarity(answer, current['answer'], current['question'], key)
                    if result == FEEDBACK_STATUS_CORRECT.upper():
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

            refresher(timeout + 1)

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
                if st.button(_("Exit Quiz Button"), key=f"exit_{idx}_fb"):
                    reset_quiz_state()
                    st.rerun()





