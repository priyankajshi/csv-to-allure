# config.py

# --- Allure TestOps Configuration ---
# Replace with your actual Allure TestOps instance URL
ALLURE_BASE_URL = "https://nesto.testops.cloud/"

# The unique identifier of the target project in Allure TestOps
PROJECT_ID = 135 

# API Endpoint for creating a test case
TESTCASE_API_ENDPOINT = f"{ALLURE_BASE_URL}/api/rs/testcase"

# --- File Configuration ---
CSV_FILE_PATH = "sample_testcases.csv"

# --- Allure TestOps Field Mapping ---
# Map CSV header names to the keys the API expects
FIELD_MAPPING = {
    "ID": "externalId", 
    "Title": "name",
    "Priority": "priority",
    "Tags": "tags",
    "Preconditions": "description_preconditions", # Custom key for transformation
    "Steps": "description_steps" # Custom key for transformation
}

# --- Step Delimiters ---
STEP_SEPARATOR = " | " 
ACTION_EXPECTED_SEPARATOR = "; Expected: " # Used to split Action from Expected Result