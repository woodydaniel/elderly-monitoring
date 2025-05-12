import streamlit as st
import subprocess
import json
import os
import sys # For sys.executable, though we might not need it if "python" in subprocess works

# Attempt to import AI processor components
try:
    from ai_processor import get_ai_response, google_api_key_loaded, gemini_model
    ai_module_loaded = True
except ImportError as e:
    ai_module_loaded = False
    ai_import_error = str(e)
    # These will be used to display an error if import fails
    get_ai_response = None
    google_api_key_loaded = False
    gemini_model = None


st.set_page_config(page_title="Data Dashboard MVP", layout="wide") # Added page config
st.title("MVP de Monitorización de Bienestar para Adultos Mayores")

DATA_FILE_PATH = 'temp_sheet_data.json'

# Initialize session state variables
if 'sheet_data' not in st.session_state:
    st.session_state.sheet_data = None
if 'error_message' not in st.session_state:
    st.session_state.error_message = None
if 'user_question' not in st.session_state:
    st.session_state.user_question = ""
if 'ai_response' not in st.session_state:
    st.session_state.ai_response = None


# --- Sidebar for AI Status ---
with st.sidebar:
    st.header("AI Status")
    if not ai_module_loaded:
        st.error(f"Failed to load AI module: {ai_import_error}")
    elif not google_api_key_loaded:
        st.error("❌ Google API Key not loaded. Check .env file.")
        st.info("Ensure GOOGLE_API_KEY is set in a .env file in the project root.")
    elif gemini_model:
        st.success(f"✅ Gemini Model Initialized ({gemini_model.model_name})")
    else:
        st.warning("AI module loaded, but Gemini model not available.")


# --- Main App Layout ---
# Remove column definitions: col1, col2 = st.columns((1,1))

# Section 1: Load Survey Data (will take full width)
st.subheader("1. Cargar Datos de Encuestas") # Translated subheader
if st.button("🔄 Cargar datos de encuestas"):
    st.session_state.sheet_data = None 
    st.session_state.error_message = None
    st.session_state.ai_response = None # Clear AI response when reloading data
    with st.spinner("Ejecutando script para cargar datos..."):
        try:
            python_executable = sys.executable # More robust way to get current venv python
            process = subprocess.run(
                [python_executable, "fetch_data.py"], 
                capture_output=True, text=True, check=False, encoding='utf-8'
            )
            if process.returncode == 0:
                st.success(f"Sheet data script success: {process.stdout.strip()}")
                if os.path.exists(DATA_FILE_PATH):
                    try:
                        with open(DATA_FILE_PATH, 'r', encoding='utf-8') as f:
                            st.session_state.sheet_data = json.load(f)
                    except json.JSONDecodeError as json_err:
                        st.session_state.error_message = f"Error decoding JSON: {json_err}"
                    except Exception as file_err:
                        st.session_state.error_message = f"Error reading data file: {file_err}"
                else:
                    st.session_state.error_message = f"Data file not found. Script stdout: {process.stdout.strip()}, stderr: {process.stderr.strip()}"
            else:
                st.session_state.error_message = f"Sheet data script failed (Code {process.returncode}):\nSTDOUT:{process.stdout.strip()}\nSTDERR:{process.stderr.strip()}"
        except FileNotFoundError:
            st.session_state.error_message = f"Error: Command '{python_executable}' or 'fetch_data.py' not found."
        except Exception as e:
            st.session_state.error_message = f"Unexpected error running script: {str(e)}"

    if st.session_state.error_message:
        st.error(st.session_state.error_message)

    if st.session_state.sheet_data:
        st.write("**Data Preview:**")
        data_to_display = st.session_state.sheet_data # Use all loaded data

        if data_to_display and isinstance(data_to_display, list) and len(data_to_display) > 0 and isinstance(data_to_display[0], list):
            num_data_rows = len(data_to_display) - 1 if len(data_to_display) > 0 else 0
            num_cols = len(data_to_display[0]) if num_data_rows >= 0 and data_to_display[0] else 0 # Handle empty data_to_display[0]
            st.caption(f"Showing all {num_data_rows} loaded data rows and {num_cols} columns. Table is scrollable.")

            try:
                html_table_string = "<table border='1' style='border-collapse: collapse;'>" # Removed width: 100%
                
                # Prepare header
                if data_to_display[0]: # Ensure header row exists
                    html_table_string += "<thead><tr>"
                    for h_item in data_to_display[0]:
                        html_table_string += f"<th style='padding: 5px; text-align: left; border: 1px solid #ddd; white-space: nowrap;'>{str(h_item)}</th>" # Added white-space: nowrap
                    html_table_string += "</tr></thead>"
                
                # Prepare data rows
                html_table_string += "<tbody>"
                for original_row in data_to_display[1:]:
                    html_table_string += "<tr>"
                    # Ensure consistent number of cells as in header
                    # Pad with empty cells if row is shorter
                    num_header_cols = len(data_to_display[0]) if data_to_display[0] else 0
                    for i in range(num_header_cols):
                        cell_value = str(original_row[i]) if i < len(original_row) else "" # Handle rows shorter than header
                        html_table_string += f"<td style='padding: 5px; border: 1px solid #ddd; white-space: nowrap;'>{cell_value}</td>" # Added white-space: nowrap
                    html_table_string += "</tr>"
                html_table_string += "</tbody></table>"
                    
                # Wrap HTML table string in a scrollable div
                scrollable_div_html = f"<div style='overflow-x: auto; width: 100%; max-height: 400px; border: 1px solid #eee; padding: 5px;'>{html_table_string}</div>"
                st.markdown(scrollable_div_html, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"Error formatting preview: {str(e)}")
                st.json(data_to_display) # Show all data if formatting fails
        elif data_to_display: # Handles cases like empty list or not list of lists after header check
            st.write("Preview data is empty or not in the expected format (list of lists).")
            st.json(data_to_display)
        # else: # No explicit message if no data and no error, button prompts action
            # if not st.session_state.error_message: st.info("Data loaded is empty.")

# Section 2: Ask AI About Data (will take full width, below Section 1)
st.subheader("2. Consultar a la IA sobre los Datos") # Translated subheader

# Use text_area for potentially longer questions, and use session state for stickiness
st.session_state.user_question = st.text_area(
    "Formule su pregunta en español:", 
    value=st.session_state.user_question,
    height=100,
    placeholder="Ej: ¿Cuál es el estado de ánimo general reportado?"
)

if st.button("🔍 Analizar con IA"):
    st.session_state.ai_response = None # Clear previous AI response
    if not ai_module_loaded:
        st.error(f"AI module not loaded. Cannot analyze. Error: {ai_import_error}")
    elif not google_api_key_loaded or not gemini_model:
        st.error("AI not initialized. Check API key and AI status in sidebar.")
    elif not st.session_state.sheet_data:
        st.warning("Por favor, cargue los datos primero.")
    elif not st.session_state.user_question.strip():
        st.warning("Por favor, formule una pregunta.")
    else:
        with st.spinner("Procesando con IA..."):
            try:
                st.session_state.ai_response = get_ai_response(
                    st.session_state.user_question, 
                    st.session_state.sheet_data
                )
            except Exception as e:
                st.session_state.ai_response = f"Error durante el análisis con IA: {str(e)}"
    
    if st.session_state.ai_response:
        st.write("**Respuesta de la IA:**")
        st.markdown(st.session_state.ai_response) # Use markdown to render AI response nicely

st.markdown("---")
st.caption(f"Streamlit {st.__version__} in `venv_clean` | Python {sys.version.split()[0]}")