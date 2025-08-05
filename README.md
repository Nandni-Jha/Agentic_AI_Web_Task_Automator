# AI Web Automation Agent

This project is an advanced AI-powered web automation agent that uses LLMs (Gemini or Groq) to convert natural language instructions into browser automation steps using Selenium.

## Features
- Converts user instructions into step-by-step browser automation plans using LLMs
- Supports Chrome and Firefox browsers (Selenium)
- Can navigate, type, click, extract text, scroll, and interact with web pages
- Supports famous site shortcuts (e.g., "Google", "YouTube")
- Extracts data and allows for user interaction if needed

## Requirements
- Python 3.8+
- Chrome or Firefox browser installed
- WebDriver for your browser (chromedriver/geckodriver) in PATH or specify path in `config.py`

## Installation
1. Clone the repository:
   ```sh
   git clone <your-repo-url>
   cd web_automation
   ```
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
3. Set up your `.env` file with the required API keys:
   ```env
   GOOGLE_API_KEY=your_google_api_key
   GROQ_API_KEY=your_groq_api_key
   ```

## Usage
Run the main program:
```sh
python main.py
```

Follow the prompts to enter your instructions. The agent will generate and execute a browser automation plan.

## Configuration
- Edit `config.py` to set your LLM provider, model names, and Selenium driver type/path.
- Famous sites are mapped in `common_sites.py`.

## Notes
- For Gemini, you need a Google API key (get from Google AI Studio).
- For Groq, you need a Groq API key (get from Groq Console).
- WebDriver must be installed and accessible (see Selenium docs).

## License
MIT License
