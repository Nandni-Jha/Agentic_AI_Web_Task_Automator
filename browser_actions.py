# browser_actions.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException, StaleElementReferenceException
import time
from typing import List, Dict, Union, Any,Optional

import config # For SELENIUM_DRIVER_TYPE and SELENIUM_DRIVER_PATH

class BrowserAgent:
    def __init__(self):
        self.driver: Optional[webdriver.Remote] = None # Type hint for driver
        self.extracted_data: Dict[str, Any] = {} # To store data from extract_text actions
        self._initialize_driver()

    def _initialize_driver(self):
        driver_type = config.SELENIUM_DRIVER_TYPE.lower()
        # driver_path = getattr(config, 'SELENIUM_DRIVER_PATH', None) # Get path if defined

        try:
            if driver_type == "chrome":
                options = webdriver.ChromeOptions()
                # options.add_argument("--headless") # Uncomment for headless Browse
                options.add_argument("--start-maximized")
                options.add_argument("--disable-gpu")
                options.add_argument("--no-sandbox") # Often needed in containerized environments
                options.add_argument("--disable-dev-shm-usage") # Overcome limited resource problems
                # if driver_path:
                #    service = webdriver.ChromeService(executable_path=driver_path)
                #    self.driver = webdriver.Chrome(service=service, options=options)
                # else:
                self.driver = webdriver.Chrome(options=options)
            elif driver_type == "firefox":
                options = webdriver.FirefoxOptions()
                # options.add_argument("--headless")
                # if driver_path:
                #    service = webdriver.FirefoxService(executable_path=driver_path)
                #    self.driver = webdriver.Firefox(service=service, options=options)
                # else:
                self.driver = webdriver.Firefox(options=options)
            else:
                raise ValueError(f"Unsupported driver type: {config.SELENIUM_DRIVER_TYPE}")
            
            self.driver.implicitly_wait(5) # Default implicit wait
            print(f"{config.SELENIUM_DRIVER_TYPE} browser initialized.")
        except Exception as e:
            print(f"Error initializing WebDriver for {config.SELENIUM_DRIVER_TYPE}: {e}")
            print("Ensure WebDriver is installed and in PATH, or SELENIUM_DRIVER_PATH is correctly set in config.py.")
            raise

    def _get_by_strategy(self, selector_type: str) -> By:
        strategies = {
            "css": By.CSS_SELECTOR,
            "xpath": By.XPATH,
            "id": By.ID,
            "name": By.NAME,
            "link_text": By.LINK_TEXT,
            "partial_link_text": By.PARTIAL_LINK_TEXT,
            "tag_name": By.TAG_NAME,
        }
        strategy = strategies.get(selector_type.lower())
        if not strategy:
            raise ValueError(f"Unsupported selector type: {selector_type}")
        return strategy

    def _find_element(self, selector_type: str, selector_value: str, timeout: int = 10):
        by_strategy = self._get_by_strategy(selector_type)
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by_strategy, selector_value))
        )

    def _find_clickable_element(self, selector_type: str, selector_value: str, timeout: int = 10):
        by_strategy = self._get_by_strategy(selector_type)
        return WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((by_strategy, selector_value))
        )

    def navigate(self, url: str) -> bool:
        print(f"Navigating to: {url}")
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 15).until(lambda d: d.execute_script('return document.readyState') == 'complete')
            return True
        except TimeoutException:
            print(f"Timeout while navigating to {url}. Page might not have fully loaded.")
            return False # Indicate partial success or allow retry
        except Exception as e:
            print(f"Error navigating to {url}: {e}")
            return False

    def type_text(self, selector_type: str, selector_value: str, text: str, enter_after: bool = False) -> bool:
        action_str = f"Typing '{text}' into element ('{selector_type}'='{selector_value}')"
        print(action_str)
        try:
            element = self._find_element(selector_type, selector_value)
            # Ensure element is interactable (e.g. not hidden, enabled)
            if not element.is_displayed() or not element.is_enabled():
                print(f"Warning: Element for typing is not displayed or enabled.")
                # Attempt to scroll to it
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(0.5) # Give time for scroll
                if not element.is_displayed() or not element.is_enabled(): # Check again
                    raise ElementNotInteractableException("Element still not interactable after scroll")

            element.clear()
            element.send_keys(text)
            if enter_after:
                element.send_keys(Keys.RETURN)
            return True
        except (TimeoutException, NoSuchElementException):
            print(f"Error: Element not found for typing - {action_str}")
            return False
        except ElementNotInteractableException as e:
            print(f"Error: Element not interactable for typing - {action_str}. Details: {e}")
            return False
        except Exception as e:
            print(f"Error during type: {e} - {action_str}")
            return False

    def click_element(self, selector_type: str, selector_value: str) -> bool:
        action_str = f"Clicking element ('{selector_type}'='{selector_value}')"
        print(action_str)
        try:
            element = self._find_clickable_element(selector_type, selector_value)
            # Attempt to scroll into view if direct click fails or for robustness
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                time.sleep(0.5) # Wait for scroll to settle
            except Exception:
                pass # If scroll fails, try clicking anyway

            element.click()
            return True
        except (TimeoutException, NoSuchElementException):
            print(f"Error: Element not found or not clickable - {action_str}")
            return False
        except ElementNotInteractableException as e:
            print(f"Error: Element not interactable for click - {action_str}. Trying JS click. Details: {e}")
            # Fallback to JavaScript click if standard click fails
            try:
                element_to_js_click = self._find_element(selector_type, selector_value) # Re-find without clickability check
                self.driver.execute_script("arguments[0].click();", element_to_js_click)
                return True
            except Exception as js_e:
                print(f"Error: JavaScript click also failed for - {action_str}. Details: {js_e}")
                return False
        except StaleElementReferenceException:
            print(f"Error: Stale element reference for - {action_str}. Element might have changed. Consider re-finding.")
            return False # Could trigger a re-plan with LLM
        except Exception as e:
            print(f"Error during click: {e} - {action_str}")
            return False

    def wait(self, seconds: int) -> bool:
        print(f"Waiting for {seconds} seconds...")
        time.sleep(seconds)
        return True

    def extract_text(self, selector_type: str, selector_value: str, variable_name: str) -> bool:
        action_str = f"Extracting text from ('{selector_type}'='{selector_value}') into var '{variable_name}'"
        print(action_str)
        try:
            element = self._find_element(selector_type, selector_value)
            text_content = element.text or element.get_attribute("value") or element.get_attribute("innerText")
            self.extracted_data[variable_name] = text_content.strip() if text_content else ""
            print(f"Extracted to '{variable_name}': '{self.extracted_data[variable_name][:100]}...'") # Preview
            return True
        except (TimeoutException, NoSuchElementException):
            print(f"Error: Element not found for text extraction - {action_str}")
            self.extracted_data[variable_name] = None
            return False
        except Exception as e:
            print(f"Error during text extraction: {e} - {action_str}")
            self.extracted_data[variable_name] = None
            return False

    def scroll_window(self, direction: str = "down", pixels: int = 0) -> bool: # Pixels optional
        print(f"Scrolling window {direction}" + (f" by {pixels} pixels" if direction in ["up", "down"] and pixels else ""))
        try:
            if direction.lower() == "down":
                self.driver.execute_script(f"window.scrollBy(0, {pixels if pixels else 'window.innerHeight'});")
            elif direction.lower() == "up":
                self.driver.execute_script(f"window.scrollBy(0, -{pixels if pixels else 'window.innerHeight'});")
            elif direction.lower() == "to_bottom":
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            elif direction.lower() == "to_top":
                self.driver.execute_script("window.scrollTo(0, 0);")
            else:
                print(f"Invalid scroll direction: {direction}")
                return False
            time.sleep(0.5) # Allow scroll to complete
            return True
        except Exception as e:
            print(f"Error during scroll: {e}")
            return False

    def ask_user(self, question: str) -> str:
        print(f"Agent asks: {question}")
        return input("Your response: ")

    def close_browser(self):
        if self.driver:
            print("Closing browser...")
            try:
                self.driver.quit()
            except Exception as e:
                print(f"Error during browser quit: {e}")
            finally:
                self.driver = None

    def execute_plan(self, plan: List[Dict[str, Any]], current_instruction: str) -> (bool, Optional[str]):
        """ Executes a plan of actions. Returns (overall_success, error_message_if_any) """
        if not self.driver:
            print("Browser not initialized. Cannot execute plan.")
            return False, "Browser not initialized."

        executed_successfully = True
        error_message_for_llm = None

        for i, step in enumerate(plan):
            action = step.get("action")
            print(f"\nExecuting Step {i+1}/{len(plan)}: {action} with params {step}")
            step_success = False
            try:
                if action == "navigate":
                    url = step.get("url")
                    if not url: raise ValueError("'url' missing for navigate action.")
                    step_success = self.navigate(url)
                elif action == "type":
                    step_success = self.type_text(step["selector_type"], step["selector_value"], step["text"], step.get("enter_after", False))
                elif action == "click":
                    step_success = self.click_element(step["selector_type"], step["selector_value"])
                elif action == "wait":
                    step_success = self.wait(int(step["seconds"]))
                elif action == "extract_text":
                    step_success = self.extract_text(step["selector_type"], step["selector_value"], step["variable_name"])
                elif action == "scroll":
                    step_success = self.scroll_window(step.get("direction", "down"), int(step.get("pixels", 0)))
                elif action == "ask_user":
                    user_response = self.ask_user(step["question"])
                    # This response might need to be fed back to the LLM for a new plan
                    # For now, we'll just store it and consider the step successful if asked.
                    self.extracted_data[f"user_response_to_{i+1}"] = user_response
                    print(f"User responded: {user_response}")
                    step_success = True # Or potentially break and re-plan with this info.
                    # For a more advanced agent, an "ask_user" action might imply the current plan stops,
                    # and a new plan is generated using the user's answer.
                    # For simplicity here, we'll continue if there are more steps, assuming they don't depend on the answer.
                elif action == "error": # Error reported by LLM in the plan itself
                    print(f"Error in plan from LLM: {step.get('message')}")
                    executed_successfully = False
                    error_message_for_llm = step.get('message')
                    break # Stop execution
                else:
                    print(f"Unknown action: {action}")
                    executed_successfully = False
                    error_message_for_llm = f"Unknown action '{action}' in plan."
                    break

                if not step_success:
                    executed_successfully = False
                    error_message_for_llm = f"Action '{action}' failed. Params: {step}."
                    print(f"Step failed: {error_message_for_llm}")
                    # Advanced: Could try to take a screenshot here.
                    # self.driver.save_screenshot(f"error_step_{i+1}.png")
                    break # Stop on first failure for now

                time.sleep(1) # Small delay between actions for observation and page stability

            except KeyError as e:
                print(f"Execution Error: Missing parameter for action '{action}': {e}")
                executed_successfully = False
                error_message_for_llm = f"Missing parameter for action '{action}': {e}."
                break
            except ValueError as e: # E.g. bad selector type, non-integer for wait
                print(f"Execution Error: Invalid parameter value for action '{action}': {e}")
                executed_successfully = False
                error_message_for_llm = f"Invalid parameter for action '{action}': {e}."
                break
            except Exception as e:
                print(f"Execution Error: An unexpected error occurred during action '{action}': {e}")
                executed_successfully = False
                error_message_for_llm = f"Unexpected error during action '{action}': {e}."
                break
        
        if executed_successfully:
            print("\nPlan execution finished successfully.")
        else:
            print(f"\nPlan execution failed or was interrupted. Error: {error_message_for_llm}")
        
        print("Current extracted data:", self.extracted_data)
        return executed_successfully, error_message_for_llm

if __name__ == '__main__':
    agent = None
    try:
        agent = BrowserAgent()
        # Example: Manually testing a navigation and type
        manual_plan = [
            {"action": "navigate", "url": "https://www.google.com"},
            {"action": "type", "selector_type": "name", "selector_value": "q", "text": "Groq API Llama3", "enter_after": True},
            {"action": "wait", "seconds": 2},
            {"action": "extract_text", "selector_type": "xpath", "selector_value": "(//h3)[1]", "variable_name": "first_result_title"},
            {"action": "scroll", "direction": "down", "pixels": 300}
        ]
        print("Executing manual test plan...")
        success, error = agent.execute_plan(manual_plan, "Manual Test Plan")
        if success:
            print(f"Manual plan successful. First result title: {agent.extracted_data.get('first_result_title')}")
        else:
            print(f"Manual plan failed. Error: {error}")

        input("Press Enter to close browser...")
    except Exception as e:
        print(f"Main execution error: {e}")
    finally:
        if agent:
            agent.close_browser()