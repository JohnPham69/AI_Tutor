# To run this code you need to install the following dependencies:
# pip install google-genai

import requests
from google import genai
from google.genai import types
from app_utils import get_cookie_controller # Import the singleton controller

controller = get_cookie_controller() # Use the cached singleton instance
try:
    controller.refresh()
except Exception as e:
    pass # who the fuck cares about the error, as long as it doesn't poses a threat.


DEFAULT_MODEL_NAME = "gemini-2.5-flash"
DEFAULT_MODEL_FLASH_LATEST = "gemini-2.5-flash"

def trans(text, user_api, user_model=None):
    """
    Translate the given text to English using Gemini.
    """
    try:
        client = genai.Client(api_key=user_api) # type: ignore
        model_to_use = user_model if user_model else DEFAULT_MODEL_FLASH_LATEST

        prompt = f"""

        Văn bản: "{text}"

        Bắt buộc phải dịch ra tiếng anh. Kết quả phải là tiếng Anh hoàn chỉnh, không có từ lóng hoặc ngôn ngữ địa phương."""

        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
        generate_content_config = types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="text/plain",
        )
        ans = "".join(chunk.text for chunk in client.models.generate_content_stream(
            model=model_to_use, contents=contents, config=generate_content_config
        ))
        return ans.strip()
    except Exception as e:
        print(f"Error in translation: {e}")
        return "Error in translation"

def genRes(text_input, chat_history, user_api, user_model=None, selected_grade=None, selected_subject_name=None, selected_lesson_data_list=None, uploaded_file_text: str = None, translator=None):
    try:
        if not user_api:
            user_api = controller.get('user_api')
            #return translator("API key not configured, please set it in the Config page.") if translator else "API key not configured, please set it in the Config page."
        
        
        
        active_model_name = user_model if user_model and user_model.strip() else DEFAULT_MODEL_NAME
        original_user_text_input = text_input

        # Ensure uploaded_file_text is a string, not None
        uploaded_file_text = uploaded_file_text or ""

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

        # Định nghĩa lại prompt cho StLearn
        step_1_prompt_vi = """
            Bạn là một AI Trợ Lý Học Tập, chuyên trả lời các câu hỏi của người dùng dựa trên nội dung bài học được cung cấp.

            QUY TẮC:
            - Chỉ trả lời dựa trên tài liệu bài học đã cung cấp. Nếu người dùng hỏi ngoài lề, hãy lịch sự từ chối và nhắc rằng bạn chỉ hỗ trợ các chủ đề trong bài học.
            - KHÔNG đặt câu hỏi mới cho người dùng.
            - Sau khi trả lời, hãy gợi ý nhẹ nhàng các hành động tiếp theo cho người dùng dưới dạng các câu hỏi follow-up.
            - Câu hỏi follow-up phải được đặt ở điểm nhìn của người dùng, 
            Ví dụ: Nếu câu follow-up là: Bạn có cần tôi tóm tắt lại bài học không?
            Thì đây là câu hỏi đang ở điểm nhìn của AI. 
            Chỉnh lại câu hỏi trở thành: Tóm tắt lại bài học.

            Định dạng trả lời:
            <phần trả lời chính>
            ///Follow_up///
            - câu hỏi 1
            - câu hỏi 2
            - câu hỏi 3

            Lưu ý: Chỉ sử dụng đúng định dạng trên, không trả về bất kỳ thông tin nào khác.
        """
        # Detect language of the user input
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

        # Sau khi nhận kết quả từ model
        step_one_output_text = ""
        for chunk in client.models.generate_content_stream(
            model=active_model_name,
            contents=contents_for_step1,
            config=generate_content_config,
        ):
            step_one_output_text += chunk.text

        # Xử lý kết quả: chỉ lấy phần trước ///Follow_up///
        return step_one_output_text

    except Exception as e:
        print(f"Error in genRes: {e}")
        return translator("An error occurred while processing your request.") if translator else "An error occurred while processing your request."

