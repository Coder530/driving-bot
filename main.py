# You will need chrome installed and the correct chromedriver for it for this to work (read GitHub page for more)
# To improve reliability, please install buster (read GitHub page for more)

import undetected_chromedriver as uc

import time
from datetime import datetime, timedelta
from datetime import time as time1
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchWindowException, WebDriverException, TimeoutException
from configparser import ConfigParser
import requests
import ast
import json
import os
import traceback
import random
from captcha_solver import CaptchaSolver

# ==================================================================================================
#  Please update details in config.ini
# ==================================================================================================

current_path = str(os.path.dirname(os.path.realpath(__file__)))
config = ConfigParser()
config.read(os.path.join(current_path, 'config.ini'))

def parse_config() -> dict:
    def build_dict(**kwargs) -> dict:
        preference = {
            "licence-id": 0,
            "user-id": 0,
            "licence": kwargs.get('licence'),
            "booking": kwargs.get('booking'),
            "current-test": {
                "date": kwargs.get('current_test_date'),
                "center": kwargs.get('current_test_centre'),
                "error": kwargs.get('current_test_error')
            },
            "disabled-dates": ast.literal_eval(kwargs.get('disabled_dates', '[]')),
            "center": ast.literal_eval(kwargs.get('centre', '[]')),
            "before-date": kwargs.get('before_date'),
            "after-date": kwargs.get('after_date')
        }
        return preference

    key_dict = {}
    for section in config.sections():
        for key, val in config.items(section):
            key_dict[key] = config.get(section, key)
    return build_dict(**key_dict)

# ==================================================================================================
#  You do not need to change anything below this line
# ==================================================================================================

auto_book_test = config.get("preferences", "auto_book_test")
formatted_current_test_date = config.get("preferences", "formatted_current_test_date")

busterEnabled = True
busterPath = os.path.join(current_path, "buster-chrome.zip")

dvsa_queue_url = "https://queue.driverpracticaltest.dvsa.gov.uk/?c=dvsatars&e=ibsredirectprod0915&t=https%3A%2F%2Fdriverpracticaltest.dvsa.gov.uk%2Flogin&cid=en-GB"

if not os.path.exists('./error_screenshots'):
    os.makedirs('./error_screenshots')

def is_time_between(begin_time, end_time, check_time=None):
    check_time = check_time or datetime.now().time()
    return begin_time <= check_time <= end_time if begin_time < end_time else check_time >= begin_time or check_time <= end_time

def input_text_box(box_id, text, currentDriver):
    box = WebDriverWait(currentDriver, 10).until(EC.presence_of_element_located((By.ID, box_id)))
    for character in text:
        box.send_keys(character)
        time.sleep(random.randint(1, 5) / 100)
    time.sleep(random.uniform(0.1, 0.4))

def random_sleep(weight, max_time):
    print(f"Sleeping for {weight} seconds...")
    time.sleep(weight)
    ran_sleep_time = random.randint(0, int(max_time * 100)) / 100
    print(f"Sleeping for another {ran_sleep_time} seconds...")
    time.sleep(ran_sleep_time)

def wait_for_internet_connection():
    while True:
        try:
            requests.get("https://www.google.com/", timeout=5)
            print("Connected to internet.")
            return
        except requests.ConnectionError:
            print("No internet connection. Retrying in 5 seconds...")
            time.sleep(5)

def enter_credentials(driver, licenceInfo):
    input_text_box("driving-licence-number", str(licenceInfo["licence"]), driver)
    input_text_box("application-reference-number", str(licenceInfo["booking"]), driver)
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "booking-login"))).click()
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "test-centre-change")))

def scan_for_preferred_tests(before_date, after_date, unavailable_dates, test_date, formatted_test_date, currentDriver):
    if before_date:
        minDate = datetime.strptime(before_date, "%Y-%m-%d")
    elif "Yes" in test_date:
        minDate = datetime.strptime("2050-12-12", "%Y-%m-%d")
    else:
        minDate = datetime.strptime(test_date, "%A %d %B %Y %I:%M%p") - timedelta(days=1)

    maxDate = datetime.strptime(after_date, "%Y-%m-%d") if after_date != "None" else datetime.strptime("2000-01-01", "%Y-%m-%d")

    available_calendar = currentDriver.find_element(By.CLASS_NAME, "BookingCalendar-datesBody")
    available_days = available_calendar.find_elements(By.XPATH, ".//td[contains(@class, 'BookingCalendar-date--available')]")

    for day in available_days:
        day_a = day.find_element(By.TAG_NAME, "a")
        data_date_str = day_a.get_attribute("data-date")
        data_date = datetime.strptime(data_date_str, "%Y-%m-%d")
        if data_date_str not in unavailable_dates and data_date < minDate and data_date > maxDate and data_date.weekday() < 5 and data_date_str != formatted_test_date:
            return True, data_date_str, day_a
    return False, None, None


def launch_driver(licence_id):
    print(f"Relaunching driver for licence {licence_id}")
    chrome_options = uc.ChromeOptions()
    # Let undetected_chromedriver handle the stealth options.
    # We will only configure the user profile and image loading.
    chrome_options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})

    use_buster = config.getboolean("preferences", "use_buster", fallback=True)
    if use_buster and busterEnabled and os.path.exists(busterPath):
        print("Buster extension enabled.")
        chrome_options.add_extension(busterPath)

    user_data_dir = os.path.join(current_path, "chrome_profile")
    if not os.path.exists(user_data_dir):
        os.makedirs(user_data_dir)
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")

    use_headless = config.getboolean("preferences", "use_headless", fallback=False)
    driver = uc.Chrome(options=chrome_options, use_subprocess=True, headless=use_headless, version_main=126)
    time.sleep(random.randint(2, 4))
    return driver


def main():
    print(f"Time: {datetime.now()}")
    print("="*100)
    print("START OF SCRIPT")
    print("="*100)

    wait_for_internet_connection()

    activeDrivers = {}
    runningLoop = True

    try:
        while runningLoop:
            print("\n" + "-"*100)
            print(f"Main loop attempt: {datetime.now()}")

            if not is_time_between(time1(6, 5), time1(23, 35)):
                print("Site offline, sleeping for 15 minutes...")
                time.sleep(900)
                continue

            licenceInfo = parse_config()
            driver = activeDrivers.get(licenceInfo['licence-id'])

            try:
                if not driver:
                    driver = launch_driver(licenceInfo['licence-id'])
                    activeDrivers[licenceInfo['licence-id']] = driver

                    print("Warming up browser...")
                    driver.get("https://www.google.com/")
                    time.sleep(random.uniform(2, 5))

                    print("Launching queue...")
                    driver.get(dvsa_queue_url)
                    WebDriverWait(driver, 300).until_not(EC.url_contains("queue.driverpracticaltest.dvsa.gov.uk"))
                    print("Queue complete!")
                    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "driving-licence-number"))) # Wait for login page to load

                    # Handle Incapsula/Imperva bot detection
                    for i in range(3): # Try up to 3 times
                        if "Pardon Our Interruption" in driver.page_source or "Request unsuccessful. Incapsula incident ID" in driver.page_source:
                            print(f"Firewall detected. Waiting and re-navigating (attempt {i+1}/3)...")
                            time.sleep(random.uniform(15, 25))
                            driver.get(dvsa_queue_url)
                            WebDriverWait(driver, 300).until_not(EC.url_contains("queue.driverpracticaltest.dvsa.gov.uk"))
                        else:
                            break # Exit loop if the page is clear

                    enter_credentials(driver, licenceInfo)

                    if "loginError=true" in driver.current_url:
                        print("Incorrect Licence/Booking Ref. Stopping script.")
                        runningLoop = False
                        continue
                    else:
                        print("Login successful.")

                # Navigate to the test change page
                if "find-test-centre" not in driver.current_url:
                    WebDriverWait(driver,10).until(EC.element_to_be_clickable((By.ID, "test-centre-change"))).click()

                WebDriverWait(driver,10).until(EC.element_to_be_clickable((By.ID, "test-centres-input"))).clear()
                input_text_box("test-centres-input", str(licenceInfo["center"][0]), driver)
                WebDriverWait(driver,10).until(EC.element_to_be_clickable((By.ID, "test-centres-submit"))).click()

                results_container = WebDriverWait(driver,10).until(EC.presence_of_element_located((By.CLASS_NAME, "test-centre-results")))
                test_center = results_container.find_element(By.XPATH, ".//a")
                test_center.click()
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "BookingCalendar-datesBody")))

                if "There are no tests available" in driver.page_source:
                    print("No tests available at this time.")
                else:
                    print("Tests available, checking for preferred dates...")
                    found, last_date, last_date_element = scan_for_preferred_tests(
                        licenceInfo["before-date"], licenceInfo["after-date"], licenceInfo["disabled-dates"],
                        licenceInfo["current-test"]["date"], formatted_current_test_date, driver
                    )
                    if found:
                        print(f"Preferred test found on {last_date}!")
                        last_date_element.click()
                        time_container = WebDriverWait(driver,10).until(EC.presence_of_element_located((By.ID, f"date-{last_date}")))
                        time_item = int(time_container.find_element(By.XPATH, ".//label").get_attribute('for').replace("slot-", "")) / 1000
                        test_time = datetime.fromtimestamp(time_item).strftime("%H:%M")
                        print(f"Test time: {test_time}")

                        if auto_book_test == "True":
                            print("Attempting to book test...")
                            time_container.find_element(By.XPATH, ".//label").click()
                            time_container.click()
                            WebDriverWait(driver,10).until(EC.element_to_be_clickable((By.ID, "slot-chosen-submit"))).click()
                            WebDriverWait(driver,10).until(EC.element_to_be_clickable((By.ID, "slot-warning-continue"))).click()
                            WebDriverWait(driver,10).until(EC.element_to_be_clickable((By.ID, "i-am-candidate"))).click()
                            WebDriverWait(driver,10).until(EC.element_to_be_clickable((By.ID, "confirm-changes"))).click()
                            print("Test booked successfully!")
                            runningLoop = False # Exit after booking
                        else:
                            print("Auto booking is disabled. Test found but not booked.")
                    else:
                        print("No suitable tests found in the preferred date range.")

                random_sleep(20, 30)

            except (NoSuchWindowException, WebDriverException, TimeoutException) as e:
                print(f"Browser/Network error occurred: {e}")
                if licenceInfo['licence-id'] in activeDrivers:
                    try:
                        activeDrivers[licenceInfo['licence-id']].quit()
                    except: pass
                    del activeDrivers[licenceInfo['licence-id']]
                print("Driver closed. Will restart in the next loop.")

            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                print(traceback.format_exc())
                if driver:
                    try:
                        filename = f"./error_screenshots/error_{datetime.now():%Y-%m-%d_%H-%M-%S}.png"
                        driver.get_screenshot_as_file(filename)
                        print(f"Screenshot saved to {filename}")
                    except:
                        print("Could not save error screenshot.")
                runningLoop = False # Stop loop on critical error

    except KeyboardInterrupt:
        print("\nScript interrupted by user.")
    finally:
        print("="*100)
        print("END OF SCRIPT. Cleaning up...")
        for driver_id, driver_instance in activeDrivers.items():
            try:
                driver_instance.quit()
                print(f"Quit driver for licence ID {driver_id}")
            except:
                print(f"Failed to quit driver for licence ID {driver_id}")
        print("="*100)

if __name__ == "__main__":
    main()