import streamlit as st
from streamlit_navigation_bar import st_navbar
from StAI import genRes
from streamlit_cookies_controller import CookieController


# Draw navbar first
page = st_navbar(["Quiz Maker AI", "Practice without AI", "Config"])
controller = CookieController()
def QuizMaker():
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
    with st.container():
        col1, col2, col3 = st.columns([1,1,3])
        with col1:
            st.selectbox("Subject?", ("Geography: 2 lessons", "History: 2 lessons"), label_visibility="collapsed")
        with col2:
            st.selectbox("Lesson?", ("1", "2"), label_visibility="collapsed")
        with col3:
            # React to user input
            if prompt := st.chat_input("Type your message here"):
                # Display user message in chat message container
                with st.chat_message("user"):
                    st.markdown(prompt)
                # Add user message to chat history
                st.session_state.messages.append({"role": "user", "content": prompt})
                user_api = controller.get('user_api')  # Get the API key from the cookie
                # Generate and display assistant response
                with st.chat_message("assistant"):
                    with st.spinner("AI is thinking..."):                
                        ai_response = genRes(prompt, st.session_state.messages, user_api)
                        # Ensure ai_response is not None before attempting to markdown.
                        # genRes is expected to return a string, even for errors.
                        if ai_response is not None:
                            st.markdown(ai_response)
                        else:
                            st.markdown("Error: No response from AI.")
                # Add assistant response to chat history
                if ai_response is not None:
                    st.session_state.messages.append({"role": "assistant", "content": ai_response})

# Routing
match page:
    case "Quiz Maker AI":
        QuizMaker()
    case "Practice without AI":
        # Initialize session state variables if they don't exist
        if "active_quiz_index" not in st.session_state:
            st.session_state.active_quiz_index = None
        # This will store answers for the currently active quiz form
        if "current_quiz_answers" not in st.session_state:
            st.session_state.current_quiz_answers = []

        lorem_ipsum_short = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
        lorem_ipsum_long = (
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. "
            "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. "
            "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. "
            "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum."
        )

        if st.session_state.active_quiz_index is None:
            # Display the list of quiz boxes
            st.title("Practice Quizzes")
            num_boxes = 4
            for i in range(num_boxes):
                # Placeholder text for the expander label, newlines for readability
                expander_label = (
                    "Subject: XXX"
                    "\n\nQuestions: XX questions"
                    "\n\nStatus: Finished"
                    "\n\nScore: XX / XX"
                )
                
                with st.expander(expander_label, expanded=False):
                    st.markdown(f"---") # Visual separator
                    # Button to start the quiz, which will trigger the view change
                    if st.button(f"Start Quiz from Box {i + 1}", key=f"start_quiz_{i}"):
                        st.session_state.active_quiz_index = i
                        st.session_state.current_quiz_answers = [""] * 5  # Initialize for 5 questions
                        st.rerun()
        
        else:
            # An active quiz is selected, display only the form
            quiz_idx = st.session_state.active_quiz_index
            
            st.title(f"Quiz Attempt: {quiz_idx + 1}") # Title for the form page

            # Ensure current_quiz_answers is a list of 5 empty strings if not already
            if not isinstance(st.session_state.current_quiz_answers, list) or len(st.session_state.current_quiz_answers) != 5:
                st.session_state.current_quiz_answers = [""] * 5
            
            for q_num in range(5): # 5 questions, indexed 0-4 for answers list
                st.markdown(f"**Question {q_num + 1}:**")
                st.markdown(lorem_ipsum_long if q_num % 2 == 0 else lorem_ipsum_short)
                
                answer_value = st.session_state.current_quiz_answers[q_num]

                user_answer = st.text_area(
                    label=f"Your Answer for Question {q_num + 1}", # Label for accessibility
                    value=answer_value,
                    key=f"answer_{quiz_idx}_{q_num}", # Unique key
                    height=100,
                    label_visibility="collapsed", 
                    placeholder="Type your answer here..."
                )
                st.session_state.current_quiz_answers[q_num] = user_answer # Update session state on interaction

                if q_num < 4: # Separator after questions 1 through 4
                    st.markdown("---")
            
            # Submit button for the entire form
            if st.button("Submit", key=f"submit_quiz_form_{quiz_idx}"):
                # Process answers (st.session_state.current_quiz_answers)
                st.success(f"Quiz {quiz_idx + 1} submitted!")
                # print(f"Answers for Quiz {quiz_idx + 1}: {st.session_state.current_quiz_answers}") # For debugging
                
                # Reset to show the list of quizzes
                st.session_state.active_quiz_index = None
                st.session_state.current_quiz_answers = [] # Clear answers for the next quiz session
                st.rerun()
    case "Config":
        st.title("Configuration")
        st.write("Enter your API key below:")
        # Use a container to represent the "row", and columns within it
        with st.container():
            col1, col2 = st.columns([2, 1]) # These are the "columns"

            with col1:
                api_key_input = st.text_input(
                    "API Key",
                    placeholder="Enter your API key",
                    label_visibility="collapsed",
                    type="password",  # Use 'password' type for sensitive input
                )

            with col2:
                save_button = st.button("Save")

        # You can add logic here to handle the save_button click
        if save_button:
            if api_key_input:
                controller.set('user_api', api_key_input)  # Save the API key in a cookie
                st.success("API key saved successfully!")
            else:
                st.warning("Please enter an API key.")
