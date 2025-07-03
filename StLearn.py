# To run this code you need to install the following dependencies:
# pip install google-genai

import requests
from google import genai
from google.genai import types

DEFAULT_MODEL_NAME = "gemini-2.5-flash"
DEFAULT_MODEL_FLASH_LATEST = "gemini-2.5-flash"

def detect_language(text_to_detect, user_api, user_model=None):
    """
    Detects the primary language of the input text.
    Returns a two-letter ISO 639-1 language code (e.g., "en", "vi").
    Defaults to "en" on error or if the language is unclear.
    """
    try:
        client = genai.Client(api_key=user_api) # type: ignore
        model_to_use = user_model if user_model else DEFAULT_MODEL_FLASH_LATEST

        prompt = f"""Phát hiện ngôn ngữ chính của văn bản sau.
        Chỉ phản hồi bằng mã ngôn ngữ ISO 639-1 gồm hai chữ cái (ví dụ: "en" cho tiếng Anh, "vi" cho tiếng Việt).
        Nếu ngôn ngữ không rõ ràng, quá ngắn hoặc hỗn hợp, hãy mặc định là "vi".

        Văn bản: "{text_to_detect}"

        Phản hồi của bạn chỉ phải là mã ngôn ngữ gồm hai chữ cái."""

        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
        generate_content_config = types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="text/plain",
        )
        ans = "".join(chunk.text for chunk in client.models.generate_content_stream(
            model=model_to_use, contents=contents, config=generate_content_config
        ))
        detected_lang = ans.strip().lower()
        return detected_lang if len(detected_lang) == 2 and detected_lang.isalpha() else "vi"
    except Exception as e:
        print(f"Error in detect_language: {e}")
        return "vi"

def genRes(text_input, chat_history, user_api, user_model=None, selected_grade=None, selected_subject_name=None, selected_lesson_data_list=None, uploaded_file_text: str = None, translator=None):
    try:
        if not user_api:
            return translator("API key not configured, please set it in the Config page.") if translator else "API key not configured, please set it in the Config page."
        active_model_name = user_model if user_model and user_model.strip() else DEFAULT_MODEL_NAME
        original_user_text_input = text_input

        # Fetch lesson material for multiple lessons
        lesson_material_fetched_parts = []
        lesson_ids_for_prompt_display = []

        if selected_lesson_data_list and isinstance(selected_lesson_data_list, list):
            for lesson_data in selected_lesson_data_list:
                if not lesson_data or not isinstance(lesson_data, dict) or not lesson_data.get('url'):
                    print(f"Warning: Invalid lesson_data entry in genRes: {lesson_data}")
                    continue

                lesson_url = lesson_data['url']
                lesson_id = lesson_data.get('id', 'UnknownID')
                lesson_name = lesson_data.get('name', f'Lesson {lesson_id}')

                try:
                    lesson_response = requests.get(lesson_url)
                    lesson_response.raise_for_status()
                    lesson_content = lesson_response.text
                    lesson_material_fetched_parts.append(f"Content for Lesson '{lesson_name}' (ID {lesson_id}):\n{lesson_content}")
                    lesson_ids_for_prompt_display.append(f"{lesson_name} (ID {lesson_id})")
                except requests.exceptions.RequestException as req_err:
                    print(f"Warning: Failed to fetch lesson content from {lesson_url} (ID {lesson_id}, Name: {lesson_name}) in genRes: {req_err}")
                except Exception as e:
                    print(f"Warning: An unexpected error occurred while fetching/processing content for lesson ID {lesson_id} (Name: {lesson_name}, URL: {lesson_url}) in genRes: {e}")

        lesson_material_combined_content = ""
        if lesson_material_fetched_parts:
            lesson_material_combined_content = "\n\n--- SEPARATOR BETWEEN LESSONS ---\n\n".join(lesson_material_fetched_parts)

        # Define the prompt content for StLearn
        step_1_prompt_vi = f"""
            Bạn là một AI Trợ Lý Học Tập, chuyên trả lời các câu hỏi của người dùng dựa trên nội dung bài học được cung cấp.

            QUY TẮC:
            - Bạn CHỈ trả lời các câu hỏi dựa trên tài liệu bài học đã được cung cấp. Nếu người dùng hỏi ngoài lề, hãy lịch sự từ chối và nhắc rằng bạn chỉ hỗ trợ các chủ đề trong bài học.
            - KHÔNG đặt câu hỏi mới về bài học cho người dùng.
            - Sau khi trả lời, hãy gợi ý nhẹ nhàng cho người dùng các hành động tiếp theo, ví dụ: "Bạn có muốn tôi tóm tắt nội dung bài học không?", "Bạn muốn tìm hiểu phần nào khác trong bài học?", hoặc "Bạn cần giải thích thêm về điểm nào không?".
            - Nếu không có tài liệu bài học nào được cung cấp, hãy thông báo cho người dùng rằng bạn cần tài liệu để trả lời.

            Định dạng phản hồi:
            [Trả lời câu hỏi của người dùng dựa trên bài học]. [Gợi ý các hành động tiếp theo].
            """
        # Detect language of the user input
        detected_lang_code = detect_language(original_user_text_input, user_api, active_model_name)
        active_step_1_prompt = step_1_prompt_vi

        # Construct the full prompt for the LLM, combining contexts and user query
        prompt_elements = []
        if uploaded_file_text:
            prompt_elements.append(
                f"CONTEXT FROM UPLOADED FILE(S):\n"
                f"------------------------------------\n"
                f"{uploaded_file_text}\n"
                f"------------------------------------"
            )

        if lesson_material_combined_content:
            lessons_display_str = ", ".join(lesson_ids_for_prompt_display) if lesson_ids_for_prompt_display else "N/A"
            prompt_elements.append(
                f"CONTEXT FROM LESSON MATERIAL ({selected_subject_name} - Lessons: {lessons_display_str}):\n"
                f"------------------------------------\n"
                f"{lesson_material_combined_content}\n"
                f"------------------------------------"
            )
        prompt_elements.append(f"USER QUERY: {original_user_text_input}")
        prompt_elements.append(f"INSTRUCTIONS:\n{active_step_1_prompt}")

        current_user_message_for_step1 = "\n\n".join(prompt_elements)

        client = genai.Client( # type: ignore
            api_key=user_api,
        )

        contents_for_step1 = []

        # Convert chat history (excluding the current user prompt which is now part of current_user_message_for_step1)
        if chat_history:
            relevant_history = chat_history[-20:-1]
            for message in relevant_history:
                role = message["role"]
                if role == "assistant":
                    role = "model"
                elif role == "user":
                    pass
                else:
                    print(f"Skipping message with unsupported role: {role}")
                    continue
                if message.get("content"):
                    contents_for_step1.append(
                        types.Content(role=role, parts=[types.Part.from_text(text=message["content"])]) # type: ignore
                    )
        contents_for_step1.append(types.Content(role="user", parts=[types.Part.from_text(text=current_user_message_for_step1)])) # type: ignore

        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            response_mime_type="text/plain",
        )

        step_one_output_text = ""
        for chunk in client.models.generate_content_stream(
            model=active_model_name,
            contents=contents_for_step1,
            config=generate_content_config,
        ):
            step_one_output_text += chunk.text

        return step_one_output_text

    except Exception as e:
        print(f"Error in genRes: {e}")
        return translator("An error occurred while processing your request.") if translator else "An error occurred while processing your request."