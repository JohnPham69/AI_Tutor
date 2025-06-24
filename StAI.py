# To run this code you need to install the following dependencies:
# pip install google-genai

import requests
import json # Added for parsing JSON
from google import genai
from google.genai import types
DEFAULT_MODEL_NAME = "gemini-2.5-flash"
DEFAULT_MODEL_FLASH_LATEST = "gemini-2.5-flash"
def analyze_user_intent(user_input_text, user_api, user_model=None):
    """
    Analyzes the user's input to determine if they want to stop or continue.
    Returns "STOP", "CONTINUE", or "ERROR" if analysis fails.
    """
    try:
        client = genai.Client(api_key=user_api) # type: ignore
        model_to_use = user_model if user_model else DEFAULT_MODEL_FLASH_LATEST

        prompt = f"""Phân tích tin nhắn của người dùng sau đây để xác định ý định chính của họ.
Nếu người dùng rõ ràng hoặc ngầm chỉ ra rằng họ muốn dừng hoạt động, bài kiểm tra hoặc cuộc trò chuyện hiện tại, hãy phản hồi bằng một từ duy nhất: STOP
Nếu người dùng muốn tiếp tục, đặt câu hỏi, cung cấp câu trả lời, yêu cầu giải thích, yêu cầu tóm tắt hoặc nếu ý định không rõ ràng, hãy phản hồi bằng một từ duy nhất: CONTINUE
Nếu người dùng yêu cầu bắt đầu hoặc tiếp tục bài kiểm tra, hãy phản hồi bằng một từ duy nhất: START_QUIZ

Tin nhắn của người dùng: "{user_input_text}"

Phản hồi của bạn chỉ nên là một từ: STOP, CONTINUE, hoặc START_QUIZ."""

        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]
        
        # Configuration for a more deterministic response
        generate_content_config = types.GenerateContentConfig(
            temperature=0.35, 
            # top_p=0.95, # top_p is not available for gemini-1.5-flash
            response_mime_type="text/plain",
        )

        # Modified to use the streaming approach, mirroring the pattern from afterStepOne
        # as per the request to resolve the AttributeError. (Note: Original comment, AttributeError might have been resolved differently or was context-specific)
        ans = ""
        for chunk in client.models.generate_content_stream(
            model=model_to_use,
            contents=contents,
            config=generate_content_config,  # Pass the GenerateContentConfig object
        ):
            ans += chunk.text
        intent_result = ans.strip().upper()
        return intent_result if intent_result in ["STOP", "CONTINUE", "START_QUIZ"] else "CONTINUE" # Default to CONTINUE if unexpected
    except Exception as e:
        print(f"Error in analyze_user_intent: {e}")
        return "ERROR" # Indicate an error occurred during analysis

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
            temperature=0.35,
            response_mime_type="text/plain",
        )
        ans = "".join(chunk.text for chunk in client.models.generate_content_stream(
            model=model_to_use, contents=contents, config=generate_content_config
        ))
        detected_lang = ans.strip().lower()
        return detected_lang if len(detected_lang) == 2 and detected_lang.isalpha() else "vi" # Default to Vietnamese
    except Exception as e:
        print(f"Error in detect_language: {e}")
        return "vi" # Default to Vietnamese on error

    
def afterStepOne(plan_text, user_api, user_model=None):
    client = genai.Client( # type: ignore
        api_key=user_api,  # Replace with your actual API key or environment variable
    )
    model_to_use = user_model if user_model else DEFAULT_MODEL_FLASH_LATEST

    # Construct the prompt/content for after step one
    prompt_for_after_step_one = """
Đoạn văn bản đầu vào chứa phản hồi của AI cho người dùng và một câu hỏi ôn tập.
Nhiệm vụ của bạn là:
1. Giữ nguyên phần phản hồi ở đầu đoạn văn bản (nếu có). KHÔNG thay đổi nội dung của phần phản hồi này.
2. Xem xét phần CÂU HỎI ở cuối đoạn văn bản. Đánh giá xem đó có phải là một câu hỏi tốt, rõ ràng, và phù hợp không.
3. Nếu câu hỏi tốt, hãy giữ nguyên nó.
4. Nếu câu hỏi chưa tốt (ví dụ: không rõ ràng, quá khó, quá dễ, không liên quan chặt chẽ đến ngữ cảnh bài học tiềm năng), hãy chỉnh sửa hoặc thay thế bằng một câu hỏi tốt hơn.
5. Trả về kết quả là sự kết hợp của [Phần phản hồi gốc (nếu có)] + [Câu hỏi (giữ nguyên hoặc đã cải thiện)].

Ví dụ:
- Đầu vào: "Đúng rồi! Câu trả lời rất hay. Câu hỏi tiếp theo: Mặt trời màu gì?"
- Nếu "Mặt trời màu gì?" là câu hỏi tốt, bạn trả về: "Đúng rồi! Câu trả lời rất hay. Câu hỏi tiếp theo: Mặt trời màu gì?"
- Nếu "Mặt trời màu gì?" cần cải thiện, bạn có thể trả về: "Đúng rồi! Câu trả lời rất hay. Câu hỏi tiếp theo: Hãy mô tả các lớp chính của Mặt Trời?"

Toàn bộ đầu ra của bạn phải có giọng điệu thân thiện, dí dỏm.
KHÔNG thêm bất kỳ lời giải thích nào về quá trình làm việc của bạn. Chỉ trả về chuỗi văn bản cuối cùng.
"""
    # Combine the instruction prompt with the text to be evaluated
    full_prompt_for_step_two = f"{prompt_for_after_step_one}\n\nHere is the text to evaluate:\n{plan_text}"
    contents = [
        types.Content(role="user", parts=[types.Part.from_text(text=full_prompt_for_step_two)]) # type: ignore
    ]

    generate_content_config = types.GenerateContentConfig(
        temperature=0.35,
        top_p=0.95,
        response_mime_type="text/plain",
    )
    ans=""
    for chunk in client.models.generate_content_stream(
        model=model_to_use,
        contents=contents,
        config=generate_content_config,
    ):
        ans += chunk.text
    return ans.replace("\n", "\n\n")


def genRes(text_input, chat_history, user_api, user_model=None, selected_subject_name=None, selected_lesson_data_list=None, uploaded_file_text: str = None):
    try:
        if not user_api:
            return "API key not configured, please set it in the Config page."

        active_model_name = user_model if user_model and user_model.strip() else DEFAULT_MODEL_NAME
        original_user_text_input = text_input # Save for language detection before modification

        # 1. Analyze user intent first
        intent_analysis_result = analyze_user_intent(original_user_text_input, user_api, active_model_name)

        if intent_analysis_result == "STOP":
            # Check if it's a simple stop command or a stop with a new query
            simple_stop_phrases = ["stop", "stop.", "please stop", "enough", "thats enough", "that's enough"]
            normalized_text_input = text_input.strip().lower()
            is_simple_stop = False
            if normalized_text_input in simple_stop_phrases:
                is_simple_stop = True
            elif "stop" in normalized_text_input and len(normalized_text_input.split()) <= 3: # Heuristic for short stop commands
                is_simple_stop = True

            if is_simple_stop:
                return "Ok, what do you want to talk about?"
            else:
                # User wants to stop the quiz and ask something else.
                # The text_input (and chat_history) contains the new query.
                client = genai.Client(api_key=user_api) # type: ignore
                # Use active_model_name for consistency, or a specific one if desired for general QA

                contents_for_general_qa = []
                if chat_history: # chat_history includes the current user message
                    for message in chat_history:
                        role = "model" if message["role"] == "assistant" else message["role"]
                        if role in ["user", "model"]:
                            contents_for_general_qa.append(
                                types.Content(role=role, parts=[types.Part.from_text(text=message["content"])]) # type: ignore
                            )
                
                generate_content_config_general = types.GenerateContentConfig(
                    temperature=0.35, top_p=0.95, response_mime_type="text/plain"
                )
                response_str = "".join(chunk.text for chunk in client.models.generate_content_stream(
                    model=active_model_name, contents=contents_for_general_qa, config=generate_content_config_general
                ))
                return response_str # Potentially add .replace("\n", "\n\n") if desired
        elif intent_analysis_result == "ERROR":
            # You might want to log this error or handle it more gracefully
            return "Sorry, I had a little trouble understanding that. Could you please rephrase?"

        # Fetch lesson material for multiple lessons
        lesson_material_fetched_parts = []
        lesson_ids_for_prompt_display = []

        if selected_lesson_data_list and isinstance(selected_lesson_data_list, list):
            for lesson_data in selected_lesson_data_list:
                if not lesson_data or not isinstance(lesson_data, dict) or not lesson_data.get('url'):
                    print(f"Warning: Invalid lesson_data entry in genRes: {lesson_data}")
                    continue
                
                lesson_url = lesson_data['url']
                # Use .get with a fallback for id and name, though they should exist from Tester.py
                lesson_id = lesson_data.get('id', 'UnknownID') 
                lesson_name = lesson_data.get('name', f'Lesson {lesson_id}')

                try:
                    lesson_response = requests.get(lesson_url)
                    lesson_response.raise_for_status() # Will raise an HTTPError for bad responses (4XX or 5XX)
                    lesson_content = lesson_response.text
                    # Using lesson_name and lesson_id for more descriptive context part
                    lesson_material_fetched_parts.append(f"Content for Lesson '{lesson_name}' (ID {lesson_id}):\n{lesson_content}")
                    lesson_ids_for_prompt_display.append(f"{lesson_name} (ID {lesson_id})")
                except requests.exceptions.RequestException as req_err:
                    print(f"Warning: Failed to fetch lesson content from {lesson_url} (ID {lesson_id}, Name: {lesson_name}) in genRes: {req_err}")
                except Exception as e:
                    # Catch any other unexpected errors during the fetch/processing of a single lesson's content
                    print(f"Warning: An unexpected error occurred while fetching/processing content for lesson ID {lesson_id} (Name: {lesson_name}, URL: {lesson_url}) in genRes: {e}")

        lesson_material_combined_content = ""
        if lesson_material_fetched_parts:
            lesson_material_combined_content = "\n\n--- SEPARATOR BETWEEN LESSONS ---\n\n".join(lesson_material_fetched_parts)


        # Define the prompt content first
        step_1_prompt_vi = """
            Bạn là một AI Gia Sư Thông Thái, chuyên về môn học và bài học được cung cấp.
            Vai trò của bạn là tương tác với người dùng dựa trên nội dung bài học.

            ƯU TIÊN HÀNH ĐỘNG:
            1.  NẾU người dùng đặt câu hỏi trực tiếp (ví dụ: "Cái gì là X?", "Giải thích Y?"), HÃY TRẢ LỜI câu hỏi đó một cách chi tiết, dựa trên tài liệu bài học được cung cấp. Sau khi trả lời, hãy hỏi xem người dùng có muốn tiếp tục với một câu hỏi ôn tập từ bài học không.
            2.  NẾU người dùng yêu cầu tóm tắt hoặc giải thích một phần nào đó của bài học, HÃY CUNG CẤP thông tin đó. Sau đó, hỏi xem người dùng có muốn tiếp tục với một câu hỏi ôn tập không.
            3.  NẾU người dùng yêu cầu bắt đầu bài kiểm tra hoặc đặt câu hỏi (ví dụ: "Hỏi đi", "Bắt đầu kiểm tra"), HÃY ĐẶT một câu hỏi trắc nghiệm dựa TRÊN NỘI DUNG BÀI HỌC ĐÃ CUNG CẤP.
            4.  NẾU người dùng trả lời một câu hỏi bạn đã đặt trước đó:
                a.  Đánh giá câu trả lời.
                b.  Cung cấp phản hồi:
                    *   Nếu đúng: Ghi nhận ("Chính xác!", "Đúng rồi!").
                    *   Nếu sai hoặc chưa đầy đủ:
                        i.  Nêu rõ câu trả lời đúng.
                        ii. Giải thích TẠI SAO câu trả lời của người dùng sai/chưa đủ (nếu họ đã trả lời).
                        iii.Giải thích CHI TIẾT TẠI SAO câu trả lời đúng là đúng, dựa vào kiến thức từ bài học. Giải thích phải rõ ràng, cụ thể, không chung chung.
                        iv. Bạn PHẢI làm phong phú giải thích bằng cách tích hợp thông tin từ ít nhất một nguồn đáng tin cậy bên ngoài bổ sung NẾU CÓ THỂ và có liên quan. Trích dẫn rõ ràng nguồn bên ngoài này (ví dụ: "Để đọc thêm, bạn có thể tham khảo [Tên trang web/URL]" hoặc "Nguồn: [Tên sách/Bài báo của Tác giả]"). Nếu không tìm được nguồn ngoài phù hợp hoặc không cần thiết, hãy tập trung giải thích thật kỹ bằng kiến thức từ bài học.
                c.  Sau khi phản hồi, HÃY ĐẶT một câu hỏi ôn tập MỚI từ bài học.

            QUAN TRỌNG:
            -   TẤT CẢ các câu hỏi bạn đặt PHẢI BÁM SÁT và DỰA TRỰC TIẾP VÀO NỘI DUNG BÀI HỌC đã được cung cấp trong ngữ cảnh. Không hỏi những câu ngoài lề hoặc kiến thức phổ thông không có trong bài.
            -   Khi giải thích, hãy tích hợp thông tin từ bài học một cách tự nhiên. Không nói "theo tài liệu bài học..." mà hãy trình bày như đó là kiến thức của bạn.
            -   Mỗi lần chỉ đặt một câu hỏi.
            -   Câu hỏi có thể đa dạng (trắc nghiệm, điền khuyết, tự luận ngắn) nhưng phải kiểm tra hiểu biết về bài học.
            -   Nếu không có tài liệu bài học nào được cung cấp trong ngữ cảnh hiện tại, hãy thông báo cho người dùng rằng bạn cần tài liệu để tiếp tục hoặc chỉ có thể trả lời các câu hỏi chung chung (nếu được phép).

            Định dạng phản hồi của bạn khi người dùng trả lời câu hỏi:
            [Phản hồi về câu trả lời của người dùng]. [Câu hỏi mới từ bài học]?

            Nếu người dùng đặt câu hỏi hoặc yêu cầu, định dạng sẽ là:
            [Câu trả lời/Giải thích/Tóm tắt cho yêu cầu của người dùng]. Bạn có muốn tôi hỏi một câu về bài học không? (Hoặc một câu hỏi phù hợp khác để tiếp tục).
            """
        # Determine the language of the user's input to select the correct prompt
        detected_lang_code = detect_language(original_user_text_input, user_api, active_model_name)
        active_step_1_prompt = step_1_prompt_vi # Assuming Vietnamese for now

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
            api_key=user_api,  # Replace with your actual API key or environment variable
        )
        
        contents_for_step1 = []

        # Convert chat history (excluding the current user prompt which is now part of current_user_message_for_step1)
        if chat_history:
            relevant_history = chat_history[-20:-1] # Get up to 19 previous messages
            for message in relevant_history: 
                role = message["role"]
                if role == "assistant":
                    role = "model"  # Convert OpenAI-style role to Gemini-compatible
                elif role == "user":
                    pass  # OK
                else:
                    # Skip unsupported roles like 'system' or anything unknown
                    # Potentially log this if it's unexpected
                    print(f"Skipping message with unsupported role: {role}")
                    continue
                if message.get("content"): # Ensure content is not empty
                    contents_for_step1.append(
                        types.Content(role=role, parts=[types.Part.from_text(text=message["content"])]) # type: ignore
                    )
        # Add the fully constructed current user message (contexts + query + instructions)
        contents_for_step1.append(types.Content(role="user", parts=[types.Part.from_text(text=current_user_message_for_step1)])) # type: ignore

        generate_content_config = types.GenerateContentConfig(
            temperature=0.35,
            # top_p=0.95, # top_p is not available for gemini-1.5-flash
            response_mime_type="text/plain", # Changed from application/json as the prompt now expects direct text output
        )
        
        step_one_output_text = ""
        # First LLM call to get the response based on step_1_prompt_vi
        for chunk in client.models.generate_content_stream(
            model=active_model_name,
            contents=contents_for_step1,
            config=generate_content_config,
        ):
            step_one_output_text += chunk.text
        
        
        # Pass the output of the first LLM call to afterStepOne for potential refinement
        intermediate_result = afterStepOne(step_one_output_text, user_api, active_model_name)
        return intermediate_result

    except Exception as e:
        print(f"Error in genRes: {e}")
        return "An error occurred while processing your request."
