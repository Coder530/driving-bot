import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class CaptchaSolver:
    """
    This class encapsulates the logic for solving a reCAPTCHA challenge.
    It is designed to work with the "Buster" browser extension, which automates
    solving audio challenges. Ensure the buster-chrome.zip extension is loaded
    by the WebDriver for this to work.
    """
    def __init__(self, driver):
        self.driver = driver
        # Locators for various elements in the reCAPTCHA widget
        self.MAIN_IFRAME = (By.ID, "main-iframe")
        self.CHECKBOX_IFRAME = (By.CSS_SELECTOR, "iframe[name*='a-'][src*='recaptcha']")
        self.CHALLENGE_IFRAME = (By.CSS_SELECTOR, "iframe[title='recaptcha challenge expires in two minutes']")
        self.CHECKBOX = (By.ID, "recaptcha-anchor")
        self.AUDIO_BUTTON = (By.ID, "recaptcha-audio-button")
        self.SOLVER_BUTTON = (By.ID, "solver-button") # This is added by the Buster extension
        self.VERIFY_BUTTON = (By.ID, "recaptcha-verify-button")
        self.SUCCESS_INDICATOR = (By.XPATH, "//*[@id='recaptcha-anchor' and @aria-checked='true']")

    def _switch_to_iframe(self, *iframe_locators):
        """Helper method to switch to a nested iframe."""
        self.driver.switch_to.default_content()
        for locator in iframe_locators:
            WebDriverWait(self.driver, 10).until(EC.frame_to_be_available_and_switch_to_it(locator))

    def solve_captcha(self, skip=False):
        if skip:
            print("Captcha solving skipped by config. Please solve manually...")
            time.sleep(60)
            return True

        try:
            # Click the "I'm not a robot" checkbox
            self._switch_to_iframe(self.MAIN_IFRAME, self.CHECKBOX_IFRAME)
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(self.CHECKBOX)).click()

            # Switch to the audio challenge
            self._switch_to_iframe(self.MAIN_IFRAME, self.CHALLENGE_IFRAME)
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(self.AUDIO_BUTTON)).click()

            # Activate the Buster extension's solver button
            self._switch_to_iframe(self.MAIN_IFRAME)
            WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(self.SOLVER_BUTTON)).click()

            # Click the "Verify" button after the extension transcribes the audio
            self._switch_to_iframe(self.MAIN_IFRAME, self.CHALLENGE_IFRAME)
            WebDriverWait(self.driver, 30).until(EC.element_to_be_clickable(self.VERIFY_BUTTON)).click()

            # Check for the success indicator (the checked checkbox)
            self._switch_to_iframe(self.MAIN_IFRAME, self.CHECKBOX_IFRAME)
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located(self.SUCCESS_INDICATOR))

            self.driver.switch_to.default_content()
            print("Captcha solved successfully.")
            return True
        except Exception as e:
            print(f"Error solving captcha automatically: {e}")
            # Fallback to manual solving if any part of the automatic process fails
            print("Please solve the captcha manually. You have 60 seconds.")
            self.driver.switch_to.default_content()
            time.sleep(60)
            return False