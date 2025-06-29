# d:\NCKH_2025\QuizGenerator.py
from google import genai
from google.genai import types
import json
import requests # Để lấy tài liệu bài học

# Hàm phụ trợ để lấy tài liệu bài học (tương tự như trong StAI.py)
# Điều này có thể được tái cấu trúc thành một module tiện ích chung sau này
def _fetch_lesson_content(subject_name, lesson_id_str):
    """
    Lấy nội dung bài học từ một URL JSON chính và sau đó từ link .md cụ thể.
    Trả về nội dung bài học dưới dạng chuỗi hoặc chuỗi rỗng nếu có lỗi.
    """
    if not subject_name or not lesson_id_str:
        return ""
    try:
        main_json_url = "https://raw.githubusercontent.com/JohnPham69/Quiz_Maker_AI/refs/heads/main/lessons/GTSL.json"
        response = requests.get(main_json_url)
        response.raise_for_status()
        subjects_data = response.json()

        subject_found_data = None
        # Iterate through the correct structure: grade -> textbook_set -> subjects
        for grade_entry in subjects_data.get("grade", []):
            for textbook_set_entry in grade_entry.get("textbook_set", []):
                for subj_entry in textbook_set_entry.get("subjects", []):
                    if subj_entry.get("name") == subject_name:
                        subject_found_data = subj_entry
                        break # Found subject
                if subject_found_data:
                    break # Stop searching textbook_sets
            if subject_found_data:
                break # Stop searching grades

        if subject_found_data:
            # The rest of the logic to find the lesson by ID and fetch its .md content
            lesson_id_int = int(lesson_id_str)
            lesson_info_found = None
            for lesson_info in subject_found_data.get("link", []):
                if lesson_info.get("ID") == lesson_id_int:
                    lesson_info_found = lesson_info
                    break
            
            if lesson_info_found:
                lesson_link_url = lesson_info_found.get("link")
                if lesson_link_url:
                    lesson_response = requests.get(lesson_link_url)
                    lesson_response.raise_for_status()
                    fetched_content = lesson_response.text
                    print("DEBUG: Fetched MD Content START-------------------------------------")
                    print(fetched_content)
                    print("DEBUG: Fetched MD Content END---------------------------------------")
                    return fetched_content
        return ""
    except requests.exceptions.RequestException as req_err:
        print(f"Lỗi khi lấy dữ liệu bài học (QuizGenerator): {req_err}")
        return ""
    except (json.JSONDecodeError, ValueError) as parse_err:
        print(f"Lỗi xử lý dữ liệu bài học (QuizGenerator): {parse_err}")
        return ""
    except Exception as e:
        print(f"Lỗi không mong muốn khi lấy nội dung bài học (QuizGenerator): {e}")
        return ""

def generate_quiz_data(num_questions: int, user_api: str, subject_name: str = None, lesson_id_str: str = None):
    """
    Tạo ra N câu hỏi quiz cùng đáp án, dựa trên chủ đề và bài học (nếu có).
    Trả về một list các dictionary, mỗi dict chứa "question" và "answer".
    Format JSON: [{"question": "...", "answer": "..."}, ...]
    """
    if not user_api:
        print("Lỗi: API key không được cung cấp cho generate_quiz_data.")
        return None

    try:
        client = genai.Client(api_key=user_api) # type: ignore
        model_name = "gemini-2.5-flash" # Chuẩn hóa tên model

        lesson_material = ""
        if subject_name and lesson_id_str:
            lesson_material = _fetch_lesson_content(subject_name, lesson_id_str)

        prompt_text = f"""
            Bạn là một trợ lý AI chuyên tạo câu hỏi trắc nghiệm chất lượng cao.
            Nhiệm vụ của bạn là tạo ra chính xác {num_questions} câu hỏi.
            {'Dựa trên tài liệu bài học sau đây:\n---BEGIN LESSON MATERIAL---\n' + lesson_material + '\n---END LESSON MATERIAL---\n' if lesson_material else f'Chủ đề chung là "{subject_name if subject_name else "kiến thức phổ thông"}".'}

            Đối với mỗi câu hỏi, hãy cung cấp một câu trả lời chính xác và ngắn gọn.
            Bạn PHẢI trả về kết quả dưới dạng một mảng JSON hợp lệ. Mỗi phần tử trong mảng là một đối tượng JSON với hai khóa: "question" (string) và "answer" (string).
            Không thêm bất kỳ văn bản, giải thích, hay định dạng markdown nào khác ngoài mảng JSON.

            Ví dụ định dạng JSON cho 2 câu hỏi:
            [
                {{
                    "question": "Ví dụ câu hỏi 1 là gì?",
                    "answer": "Đây là ví dụ câu trả lời 1."
                }},
                {{
                    "question": "Ví dụ câu hỏi 2 là gì?",
                    "answer": "Đây là ví dụ câu trả lời 2."
                }}
            ]

            Hãy tạo {num_questions} câu hỏi và câu trả lời ngay bây giờ.
            """
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt_text)])]
        
        config = types.GenerateContentConfig( # Đổi tên để nhất quán
            temperature=0.7, # Tăng một chút để có sự đa dạng hơn trong câu hỏi
            response_mime_type="application/json", # Yêu cầu AI trả về JSON trực tiếp
        )

        ans = ""
        for chunk in client.models.generate_content_stream(
            model=model_name,
            contents=contents,
            config=config,
        ):
            ans += chunk.text
        
        quiz_data_list = json.loads(ans)
        
        if isinstance(quiz_data_list, list) and all(isinstance(item, dict) and "question" in item and "answer" in item for item in quiz_data_list):
            return quiz_data_list[:num_questions] # Đảm bảo trả về đúng số lượng yêu cầu
        else:
            print("Lỗi: AI không trả về định dạng JSON như mong đợi.")
            return None

    except json.JSONDecodeError as json_err:
        print(f"Lỗi giải mã JSON từ AI: {json_err}")
        print(f"Phản hồi nhận được từ AI: {ans if 'ans' in locals() else 'Không có phản hồi'}")
        return None
    except Exception as e:
        print(f"Lỗi trong generate_quiz_data: {e}")
        return None

def evaluate_user_answer_clarity(user_answer: str, correct_answer: str, question_context: str, user_api: str):
    """
    Đánh giá câu trả lời của người dùng so với đáp án đúng, xem xét sự khác biệt về từ ngữ.
    Trả về "CORRECT", "INCORRECT", hoặc "ERROR" nếu có lỗi.
    """
    if not user_api:
        print("Lỗi: API key không được cung cấp cho evaluate_user_answer_clarity.")
        return "ERROR"
    try:
        client = genai.Client(api_key=user_api) # type: ignore
        model_name = "gemini-2.5-flash"

        prompt_text = f"""
            Bạn là một chuyên gia AI trong việc đánh giá câu trả lời, có khả năng hiểu ngữ nghĩa.
            Nhiệm vụ của bạn là so sánh "Câu trả lời của người dùng" với "Câu trả lời đúng" trong bối cảnh của "Câu hỏi" được đưa ra.
            Hãy xác định xem "Câu trả lời của người dùng" có về cơ bản là đúng hay không, ngay cả khi cách diễn đạt, từ đồng nghĩa, hoặc cấu trúc câu có chút khác biệt so với "Câu trả lời đúng".

            Ví dụ:
            Câu hỏi: "Thủ đô của Pháp là gì?"
            Câu trả lời đúng: "Paris"
            Câu trả lời của người dùng: "Là Paris đó bạn" -> Kết quả nên là CORRECT
            Câu trả lời của người dùng: "Paris chính là thủ đô" -> Kết quả nên là CORRECT
            Câu trả lời của người dùng: "Berlin" -> Kết quả nên là INCORRECT

            Chỉ trả lời bằng một từ duy nhất: "CORRECT" nếu câu trả lời của người dùng về cơ bản là đúng, hoặc "INCORRECT" nếu không.
            Không cung cấp bất kỳ giải thích nào, chỉ một từ duy nhất.

            Câu hỏi: "{question_context}"
            Câu trả lời đúng: "{correct_answer}"
            Câu trả lời của người dùng: "{user_answer}"

            Đánh giá của bạn (CORRECT hoặc INCORRECT):
            """
        contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt_text)])]
        
        config = types.GenerateContentConfig( # Đổi tên để nhất quán
            temperature=0.1, # Cần sự nhất quán cao
            response_mime_type="text/plain",
        )
        
        ans_stream = ""
        for chunk in client.models.generate_content_stream(
            model=model_name,
            contents=contents,
            config=config,
        ):
            ans_stream += chunk.text
        evaluation_text = ans_stream.strip().upper()

        if evaluation_text in ["CORRECT", "INCORRECT"]:
            return evaluation_text
        else:
            print(f"Phản hồi không mong đợi từ AI khi đánh giá: {evaluation_text}")
            # Nếu AI không chắc chắn, mặc định là INCORRECT để an toàn
            return "INCORRECT" 
            
    except Exception as e:
        print(f"Lỗi trong evaluate_user_answer_clarity: {e}")
        return "ERROR"
