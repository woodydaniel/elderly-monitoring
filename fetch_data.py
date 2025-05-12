import gspread
import json
import sys
import os

SCOPE = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]
CREDENTIALS_FILE = 'credentials/credentials.json'
SPREADSHEET_ID = '1p5KpYbewyBt6mHVp8Jxgkq9t0Y4tPyLtSaEa4BU_-n4'
OUTPUT_FILE = 'temp_sheet_data.json'

def fetch_and_save_data():
    """
    Accesses the Google Sheet, fetches all data, and saves it to a JSON file.
    Prints success or error messages to stdout/stderr.
    Exits with 0 on success, 1 on failure.
    """
    gc = None
    try:
        gcp_credentials_json_str = os.getenv("GCP_CREDENTIALS_JSON")
        if gcp_credentials_json_str:
            # print("fetch_data.py: Attempting to load credentials from GCP_CREDENTIALS_JSON env var...")
            try:
                credentials_dict = json.loads(gcp_credentials_json_str)
                gc = gspread.service_account_from_dict(credentials_dict, scopes=SCOPE)
                # print("fetch_data.py: Successfully loaded credentials from env var.")
            except json.JSONDecodeError:
                sys.stderr.write("fetch_data.py: Error: GCP_CREDENTIALS_JSON environment variable is not valid JSON.\n")
                sys.exit(1)
            except Exception as e_env_load: # Catch other potential errors from service_account_from_dict
                sys.stderr.write(f"fetch_data.py: Error loading credentials from env var: {e_env_load}\n")
                sys.exit(1)
        else:
            # print(f"fetch_data.py: GCP_CREDENTIALS_JSON env var not found. Falling back to file: {CREDENTIALS_FILE}")
            gc = gspread.service_account(filename=CREDENTIALS_FILE, scopes=SCOPE)
            # print("fetch_data.py: Successfully loaded credentials from file.")

        # print(f"fetch_data.py: Attempting to open spreadsheet by ID: {SPREADSHEET_ID}...")
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        # print("fetch_data.py: Successfully opened spreadsheet by ID.")
        
        # print("fetch_data.py: Attempting to select sheet1...")
        worksheet = spreadsheet.sheet1
        # print("fetch_data.py: Successfully selected sheet1.")
        
        # print("fetch_data.py: Attempting worksheet.get_all_values()...")
        all_values = worksheet.get_all_values()
        # print("fetch_data.py: Successfully called worksheet.get_all_values().")
        
        if not all_values:
            # print("fetch_data.py: Warning: No data found in the sheet, or sheet is empty.")
            all_values = [] # Ensure it's an empty list for JSON

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_values, f, ensure_ascii=False, indent=4)
        # print(f"fetch_data.py: Data successfully fetched and saved to {OUTPUT_FILE}")
        sys.stdout.write(f"Data successfully fetched and saved to {OUTPUT_FILE}\n")
        sys.exit(0)
        
    except FileNotFoundError:
        sys.stderr.write(f"fetch_data.py: Error: Credentials file not found at {CREDENTIALS_FILE}\n")
        sys.exit(1)
    except gspread.exceptions.SpreadsheetNotFound:
        sys.stderr.write(f"fetch_data.py: Error: Spreadsheet with ID '{SPREADSHEET_ID}' not found or permission issue.\n")
        sys.exit(1)
    except Exception as e:
        sys.stderr.write(f"fetch_data.py: An unexpected error occurred: {e}\n")
        sys.exit(1)

if __name__ == '__main__':
    fetch_and_save_data() 