from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.driver_cache import DriverCacheManager

import os

DRIVER_ROOT = "driver"

def get_chrome_driver(root_dir = DRIVER_ROOT):
    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode (optional)

    driver_cache = DriverCacheManager(root_dir=root_dir)
    driver_path = ChromeDriverManager(cache_manager=driver_cache).install()
    
    # Initialize the driver with existing or new driver
    service = Service(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    return driver

driver = get_chrome_driver()

# URL of the page to scrape
url = "https://www.canlii.org/en/on/onsc/nav/date/2025/"

# Navigate to the page
driver.get(url)

# Find all links within the specified table
links = driver.find_elements(By.CSS_SELECTOR, "#filterableList a")

# Print href attributes for each link
for link in links:
    print(link.get_attribute("href"))

# Clean up
driver.quit()