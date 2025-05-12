# main.py
import json
import config
from llm_handler import generate_plan_from_instruction
from browser_actions import BrowserAgent

def check_api_keys():
    if config.LLM_PROVIDER == "gemini" and not config.GOOGLE_API_KEY:
        print("ERROR: GOOGLE_API_KEY is not set in your .env file or environment variables.")
        print("Please get a key from Google AI Studio and set it.")
        return False
    if config.LLM_PROVIDER == "groq" and not config.GROQ_API_KEY:
        print("ERROR: GROQ_API_KEY is not set in your .env file or environment variables.")
        print("Please get a key from Groq Console and set it.")
        return False
    return True

def main():
    print("Welcome to the Advanced AI Web Automation Agent!")
    print(f"Using LLM Provider: {config.LLM_PROVIDER.upper()}")
    print(f"LLM Model (Gemini): {config.GEMINI_MODEL_NAME}")
    print(f"LLM Model (Groq): {config.GROQ_MODEL_NAME}")
    print("---")

    if not check_api_keys():
        return

    browser_agent = None
    try:
        browser_agent = BrowserAgent()
        previous_actions_history = [] # For potential context in future LLM calls

        while True:
            instruction = input("\nEnter your instruction (or type 'exit' to quit, 'clear' to reset history):\n> ")
            if not instruction.strip():
                continue
            if instruction.lower() == 'exit':
                break
            if instruction.lower() == 'clear':
                previous_actions_history = []
                browser_agent.extracted_data = {} # Clear extracted data as well
                print("History and extracted data cleared.")
                continue

            print("\n🤖 Thinking... Asking LLM to generate a plan...")
            # For more advanced scenarios, you could pass previous_actions_history and error_context
            plan = generate_plan_from_instruction(instruction)

            print("\n📄 Received Plan from LLM:")
            if not plan or not isinstance(plan, list) or not plan[0].get("action"):
                print("Invalid or empty plan received from LLM. Please try rephrasing.")
                continue

            print(json.dumps(plan, indent=2))

            if plan[0].get("action") == "error":
                print(f"Cannot execute plan due to LLM error: {plan[0].get('message')}")
                continue
            
            if len(plan) > config.MAX_STEPS_PER_PLAN:
                print(f"Warning: Plan exceeds maximum configured steps ({config.MAX_STEPS_PER_PLAN}).")
                confirm_long_plan = input("Continue with this long plan? (yes/no): ").lower()
                if confirm_long_plan not in ['yes', 'y']:
                    print("Plan aborted by user due to length.")
                    continue


            confirm = input("Do you want to execute this plan? (yes/no): ").lower()
            if confirm == 'yes' or confirm == 'y':
                print("\n🚀 Executing plan...")
                success, error_message = browser_agent.execute_plan(plan, instruction)
                if success:
                    print("✅ Plan executed successfully.")
                    previous_actions_history.extend(plan) # Add successful plan to history
                else:
                    print(f"❌ Plan execution failed. Error: {error_message}")
                    # Advanced: Offer to retry, or send error to LLM for re-planning
                    # For now, we just report. If an error occurred, the partially executed
                    # plan might still be added to history, or you might choose not to.
                    # For simplicity, we add it to show what was attempted.
                    previous_actions_history.extend(plan)


                # print("\n🔄 Current extracted data:", browser_agent.extracted_data)
                # print(f"📜 Actions history length: {len(previous_actions_history)}")
                input("Execution finished. Press Enter to continue...")
            else:
                print("Plan aborted by user.")

    except Exception as e:
        print(f"\nAn critical error occurred in the main loop: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if browser_agent:
            browser_agent.close_browser()
        print("\nWeb Automation Agent shut down. Goodbye! 👋")

if __name__ == "__main__":
    main()