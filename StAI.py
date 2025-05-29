# To run this code you need to install the following dependencies:
# pip install google-genai

import base64
from google import genai
from google.genai import types


def genRes(text_input, chat_history, user_api):
    try:
        if not user_api:
            return "API key not configured, please set it in the Config page."
        client = genai.Client(
            api_key=user_api,  # Replace with your actual API key or environment variable
        )

        model = "gemini-2.0-flash"  # Or another suitable model
        contents = []

        # Convert chat history to the format expected by the model
        for message in chat_history:
            contents.append(types.Content(role=message["role"], parts=[types.Part.from_text(text=message["content"])]))
        
        # Add the current user input
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=text_input)]))

        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            top_p=0.95,
            response_mime_type="text/plain",
        )
        ans=""
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            ans += chunk.text
        return ans

    except Exception as e:
        print(f"Error in genRes: {e}")
        return "An error occurred while processing your request."
