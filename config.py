# config.py
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# --- LLM Configuration ---
# Choose your LLM provider: "gemini" or "groq"
LLM_PROVIDER = "gemini"  # or "groq"

# Specific model names (ensure these are available on the free tier)
# For Gemini (via Google AI Studio) - check their latest free tier model, e.g., 'gemini-1.5-flash-latest'
GEMINI_MODEL_NAME = "gemini-1.5-flash-latest"

# For Llama on Groq (check Groq console for available free models, e.g., 'llama3-8b-8192')
GROQ_MODEL_NAME = "llama3-8b-8192" # Example, check Groq for current free models

# API Keys (loaded from environment variables)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# --- Selenium Configuration ---
# Ensure you have the appropriate WebDriver for your browser installed
# and its path is in your system's PATH, or specify it directly.
SELENIUM_DRIVER_TYPE = "Chrome"  # Or "Firefox", etc.
# SELENIUM_DRIVER_PATH = "/path/to/your/webdriver/chromedriver" # Optional, if not in PATH

# --- Agent Configuration ---
MAX_RETRIES_LLM = 2 # Max retries if LLM output is not parsable
MAX_STEPS_PER_PLAN = 15 # Safety limit for number of steps in a plan