import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables from .env file
load_dotenv()

# Initialize the Google Gemini client
google_api_key_loaded = False
gemini_model = None
try:
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if google_api_key:
        genai.configure(api_key=google_api_key)
        
        # List available models to see which ones are supported
        try:
            models = genai.list_models()
            print("Available models:")
            gemini_models = [m for m in models if "gemini" in m.name.lower()]
            for model in gemini_models:
                print(f"- {model.name}")
            
            # Use gemini-1.5-pro or fallback to gemini-pro if available
            model_name = "gemini-1.5-pro" if any("gemini-1.5-pro" in m.name for m in gemini_models) else "gemini-pro"
            gemini_model = genai.GenerativeModel(model_name)
            google_api_key_loaded = True
            print(f"Google Gemini client configured and model initialized ({model_name}).")
        except Exception as e:
            print(f"Error listing models: {e}")
            # Fallback to default model name
            model_name = "gemini-pro"
            gemini_model = genai.GenerativeModel(model_name)
            google_api_key_loaded = True
            print(f"Google Gemini client configured with fallback model ({model_name}).")
    else:
        print("Error: GOOGLE_API_KEY not found in .env file or environment variables.")
        print("Please ensure your .env file is set up correctly with GOOGLE_API_KEY=\"your_key\"")

except Exception as e:
    print(f"Error initializing Google Gemini client: {e}")
    print("Please ensure your GOOGLE_API_KEY is correctly set in your .env file and is valid.")

def get_ai_response(question: str, sheet_data: list, model_name=None): # model_name param kept for backward compatibility
    """
    Gets a response from Google Gemini API based on the question and sheet data.

    Args:
        question (str): The user's question in Spanish.
        sheet_data (list): The data from the Google Sheet (list of lists).
        model_name (str): Not used anymore, the model is initialized globally.

    Returns:
        str: The AI's response in Spanish, or an error message.
    """
    if not google_api_key_loaded or gemini_model is None:
        return "Error: El cliente de Google Gemini no está inicializado correctamente. Verifica la clave API."

    try:
        data_context = "Datos de la encuesta:\n"
        if sheet_data:
            # Include header row
            if sheet_data[0]: # Check if header row is not empty
                 data_context += ", ".join(map(str, sheet_data[0])) + "\n" 
            # Include up to 5 data rows for MVP to keep the prompt concise
            for row in sheet_data[1:6]: # Start from the second row (actual data)
                if row: # Check if row is not empty
                    data_context += ", ".join(map(str, row)) + "\n"
        else:
            data_context += "No hay datos disponibles de la encuesta.\n"
        data_context += "\n---\n"
        
        # Construct the prompt for Gemini
        full_prompt = (
            "Eres un asistente de IA que ayuda a analizar datos de encuestas sobre el bienestar de personas mayores. "
            "Responde a las preguntas basándote ÚNICAMENTE en los datos de la encuesta proporcionados. "
            "Si la respuesta no se encuentra en los datos, indica que no tienes suficiente información basada en los datos proporcionados. "
            "Responde en ESPAÑOL.\n\n"
            f"{data_context}"
            f"Pregunta del usuario: {question}"
        )

        print(f"\n--- Sending to Google Gemini (model: {gemini_model.model_name}) --- ")
        print(f"Full Prompt (partial data context): {full_prompt[:600]}...") # Print a snippet
        print("------------------------------------")

        # Generate content with updated configuration
        generation_config = {
            "temperature": 0.2,  # Lower temperature for more deterministic responses
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 1024,
        }
        
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]
        
        response = gemini_model.generate_content(
            full_prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
        # Extract text from response
        if hasattr(response, 'text'):
            response_text = response.text
        else:
            # Fallback for different response structure
            response_text = ""
            if hasattr(response, 'parts'):
                for part in response.parts:
                    if hasattr(part, 'text'):
                        response_text += part.text
            elif hasattr(response, 'candidates') and response.candidates:
                for candidate in response.candidates:
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        for part in candidate.content.parts:
                            if hasattr(part, 'text'):
                                response_text += part.text

        print("\n--- Received from Google Gemini --- ")
        print(response_text)
        print("---------------------------------")
        return response_text

    except Exception as e:
        print(f"Error communicating with Google Gemini: {e}")
        # Attempt to get more specific error details if available
        error_details = ""
        if hasattr(e, 'message'): # For google.api_core.exceptions
            error_details = e.message
        elif hasattr(e, 'args') and e.args: # General exception arguments
            error_details = str(e.args[0])
        return f"Error al comunicar con Google Gemini: {str(e)} ({error_details})"

# Example usage (for testing this script directly)
if __name__ == '__main__':
    if not google_api_key_loaded:
        print("Google Gemini client not initialized. Exiting example.")
    else:
        print("Testing AI Processor with Google Gemini...")
        sample_sheet_data = [
            ['Timestamp', 'Estado de ánimo', 'Contacto social', 'Servicios municipales'],
            ['2023-10-26', 'Contento', 'Sí, con familia', 'No los usó'],
            ['2023-10-27', 'Triste', 'No', 'Problemas con cita previa'],
            ['2023-10-28', 'Normal', 'Amigos', 'Todo bien'],
            [], # Empty row test
            ['2023-10-29', 'Feliz', 'Familia y amigos', 'No necesita']
        ]
        sample_question_spanish = "¿Cuál es el estado de ánimo general reportado y qué problemas hubo con servicios municipales?"
        
        print(f"\nTest Question (Spanish): {sample_question_spanish}")
        ai_answer = get_ai_response(sample_question_spanish, sample_sheet_data)
        print(f"\nTest AI Answer (Spanish):\n{ai_answer}")

        sample_question_no_info = "¿Cuántas citas médicas se cancelaron?"
        print(f"\nTest Question No Info (Spanish): {sample_question_no_info}")
        ai_answer_no_info = get_ai_response(sample_question_no_info, sample_sheet_data)
        print(f"\nTest AI Answer No Info (Spanish):\n{ai_answer_no_info}")

        # Test with empty sheet data
        print(f"\nTest Question with Empty Data (Spanish): {sample_question_spanish}")
        ai_answer_empty_data = get_ai_response(sample_question_spanish, [])
        print(f"\nTest AI Answer with Empty Data (Spanish):\n{ai_answer_empty_data}") 