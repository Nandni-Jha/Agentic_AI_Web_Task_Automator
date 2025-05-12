# llm_handler.py
import google.generativeai as genai
from groq import Groq
import json
import time
from typing import Optional, List, Dict, Any
from typing import Union
import os

import config
import common_sites 
from common_sites import get_url_for_site

# --- Configure LLM Providers ---
if config.LLM_PROVIDER == "gemini":
    if not config.GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY not found in .env file. Please add it.")
    genai.configure(api_key=config.GOOGLE_API_KEY)
    gemini_model = genai.GenerativeModel(config.GEMINI_MODEL_NAME)
    print(f"Using Gemini model: {config.GEMINI_MODEL_NAME}")
elif config.LLM_PROVIDER == "groq":
    if not config.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not found in .env file. Please add it.")
    groq_client = Groq(api_key=config.GROQ_API_KEY)
    print(f"Using Groq with Llama model: {config.GROQ_MODEL_NAME}")
else:
    raise ValueError(f"Unsupported LLM_PROVIDER: {config.LLM_PROVIDER}. Choose 'gemini' or 'groq'.")


def get_system_prompt() -> str:
    """
    Returns the system prompt for the LLM to guide its behavior.
    """
    # ISO 8601 format for current date - LLMs might not use it directly, but good practice for context
    current_date_iso = time.strftime("%Y-%m-%d")

    prompt = f"""
    You are an expert web automation assistant. Your task is to convert a user's natural language instruction
    into a precise, step-by-step JSON plan for browser automation. Today's date is {current_date_iso}.

    The plan should be a JSON list of action objects. Each action object must have an "action" key and
    other keys specific to that action.

    Supported Actions and their JSON structure:
    1.  "navigate": {{
            "action": "navigate",
            "url": "<full_URL_string>"
        }}
        - If the user mentions a famous website (e.g., "Google", "YouTube", "Wikipedia", "GitHub"),
          use its canonical URL. You have access to a list of common sites.
          Example: "Go to Google" -> "url": "https://www.google.com"

    2.  "type": {{
            "action": "type",
            "selector_type": "<css|xpath|id|name|link_text|partial_link_text|tag_name>",
            "selector_value": "<selector_string>",
            "text": "<text_to_type_string>",
            "enter_after": <true|false> (optional, defaults to false. If true, press Enter key after typing)
        }}
        - Choose the most robust selector_type and selector_value possible.
        - For search bars, "enter_after" should often be true.

    3.  "click": {{
            "action": "click",
            "selector_type": "<css|xpath|id|name|link_text|partial_link_text|tag_name>",
            "selector_value": "<selector_string>"
        }}

    4.  "wait": {{
            "action": "wait",
            "seconds": <integer_seconds_to_wait>
        }}
        - Use this for explicit waits if necessary, e.g., after a page load or dynamic content update.

    5.  "extract_text": {{
            "action": "extract_text",
            "selector_type": "<css|xpath|id|name|tag_name>",
            "selector_value": "<selector_string>",
            "variable_name": "<string_name_to_store_extracted_text>"
        }}
        - The extracted text will be stored and can potentially be used in later steps or shown to the user.

    6.  "scroll": {{
            "action": "scroll",
            "direction": "<down|up|to_bottom|to_top>",
            "pixels": <integer_pixels_to_scroll> (only if direction is 'up' or 'down')
        }}

    7.  "ask_user": {{
            "action": "ask_user",
            "question": "<string_question_for_the_user>"
        }}
        - Use this if the instruction is ambiguous or requires user input to proceed.

    Output ONLY the JSON plan as a single JSON list. Do NOT include any other text, greetings, or explanations outside the JSON structure.
    Be concise and accurate. Ensure the JSON is valid.
    Limit the number of steps to a reasonable amount, typically less than {config.MAX_STEPS_PER_PLAN}. If the task is too complex, break it down or use "ask_user".

    Consider the following common site mappings if a direct URL isn't given:
    {json.dumps(common_sites.FAMOUS_SITES, indent=2)}

    If the user instruction is too vague, impossible, or potentially harmful, respond with:
    [{{"action": "error", "message": "Instruction is unclear or cannot be safely executed."}}]
    """
    return prompt

def generate_plan_from_instruction(instruction: str, previous_actions: Optional[List[Dict]] = None, error_context: Optional[str] = None) -> List[Dict[str, Union[str, int, bool]]]:
    """
    Uses the configured LLM to convert a natural language instruction into a structured plan.
    Can take previous actions and error context for more advanced re-planning (future enhancement).
    """
    full_prompt = f"{get_system_prompt()}\n\nUser Instruction: \"{instruction}\""
    if previous_actions: # For potential future re-planning
        full_prompt += f"\n\nPrevious Actions History (for context, if relevant for re-planning):\n{json.dumps(previous_actions, indent=2)}"
    if error_context: # For potential future re-planning
        full_prompt += f"\n\nError Context from previous attempt: {error_context}"
    full_prompt += "\n\nJSON Plan:"

    raw_llm_output = None
    for attempt in range(config.MAX_RETRIES_LLM):
        try:
            if config.LLM_PROVIDER == "gemini":
                response = gemini_model.generate_content(full_prompt)
                # Check for safety ratings or blocks if using Gemini
                if not response.candidates or not response.candidates[0].content.parts:
                     # Handle cases where the response might be blocked due to safety settings
                    if response.prompt_feedback and response.prompt_feedback.block_reason:
                        print(f"Gemini API: Content blocked due to {response.prompt_feedback.block_reason}")
                        return [{"action": "error", "message": f"LLM generation blocked: {response.prompt_feedback.block_reason}"}]
                    else: # Other empty response case
                        print("Gemini API: Received an empty response.")
                        return [{"action": "error", "message": "LLM generation failed (empty response)."}]
                raw_llm_output = response.text
            elif config.LLM_PROVIDER == "groq":
                chat_completion = groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": get_system_prompt()}, # Groq prefers system prompt separately
                        {"role": "user", "content": f"User Instruction: \"{instruction}\"\nJSON Plan:"}
                    ],
                    model=config.GROQ_MODEL_NAME,
                    temperature=0.2, # Lower temperature for more deterministic plan generation
                    max_tokens=1024,
                    top_p=1,
                    stop=None, # Let the model decide when to stop, or use "]}" if it helps
                    # response_format={"type": "json_object"}, # If supported and helps
                )
                raw_llm_output = chat_completion.choices[0].message.content

            if not raw_llm_output:
                raise ValueError("LLM returned empty content.")

            # Clean the output: LLMs sometimes add markdown ```json ... ```
            cleaned_output = raw_llm_output.strip()
            if cleaned_output.startswith("```json"):
                cleaned_output = cleaned_output[7:]
            if cleaned_output.endswith("```"):
                cleaned_output = cleaned_output[:-3]
            cleaned_output = cleaned_output.strip()
            
            # Attempt to parse the JSON
            plan = json.loads(cleaned_output)
            if not isinstance(plan, list):
                raise ValueError("LLM output is not a JSON list.")
            # Validate basic structure of each step (presence of 'action' key)
            for step in plan:
                if not isinstance(step, dict) or "action" not in step:
                    raise ValueError("Invalid step structure in LLM output: missing 'action' key.")
            return plan

        except json.JSONDecodeError as e:
            print(f"LLM Error: Failed to parse JSON output (Attempt {attempt + 1}/{config.MAX_RETRIES_LLM}). Error: {e}")
            print(f"LLM Raw Output:\n---\n{raw_llm_output}\n---")
            if attempt == config.MAX_RETRIES_LLM - 1:
                return [{"action": "error", "message": "Failed to parse LLM JSON output after multiple retries."}]
            time.sleep(1) # Wait before retrying
        except Exception as e:
            print(f"LLM Error: An unexpected error occurred (Attempt {attempt + 1}/{config.MAX_RETRIES_LLM}). Error: {e}")
            if attempt == config.MAX_RETRIES_LLM - 1:
                return [{"action": "error", "message": f"An unexpected error occurred with the LLM: {e}"}]
            time.sleep(1)

    return [{"action": "error", "message": "LLM failed to generate a valid plan."}]


if __name__ == '__main__':
    # Test the LLM plan generation
    # Ensure your .env file is populated with API keys
    if not config.GOOGLE_API_KEY and config.LLM_PROVIDER == "gemini":
        print("Skipping Gemini test: GOOGLE_API_KEY not set.")
    elif not config.GROQ_API_KEY and config.LLM_PROVIDER == "groq":
        print("Skipping Groq test: GROQ_API_KEY not set.")
    else:
        print(f"Testing with LLM Provider: {config.LLM_PROVIDER}")
        # Test instruction 1
        instruction1 = "Go to Google, search for 'best AI tools 2025', and click the first result. Then wait 3 seconds."
        print(f"\nInstruction 1: {instruction1}")
        plan1 = generate_plan_from_instruction(instruction1)
        print("Generated Plan 1:")
        print(json.dumps(plan1, indent=2))

        # Test instruction 2
        instruction2 = "Navigate to Wikipedia and search for 'Large Language Models'. Then extract the first paragraph text and scroll down a bit."
        print(f"\nInstruction 2: {instruction2}")
        plan2 = generate_plan_from_instruction(instruction2)
        print("Generated Plan 2:")
        print(json.dumps(plan2, indent=2))

        # Test instruction 3 (famous site)
        instruction3 = "Open GitHub and look for 'selenium python examples'."
        print(f"\nInstruction 3: {instruction3}")
        plan3 = generate_plan_from_instruction(instruction3)
        print("Generated Plan 3:")
        print(json.dumps(plan3, indent=2))

        # Test instruction 4 (potentially ambiguous)
        instruction4 = "Book a flight."
        print(f"\nInstruction 4: {instruction4}")
        plan4 = generate_plan_from_instruction(instruction4)
        print("Generated Plan 4:")
        print(json.dumps(plan4, indent=2))