from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.driver_cache import DriverCacheManager

import requests
import bs4
import os
from pathlib import Path

DRIVER_ROOT = Path("driver")
if not DRIVER_ROOT.exists():
    os.makedirs(DRIVER_ROOT)

RAW_CASES_DIR = Path("cases")
if not RAW_CASES_DIR.exists():
    os.makedirs(RAW_CASES_DIR)

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

def parse_case(case_url: str):
    # Get the page content using requests
    response = requests.get(case_url)
    
    # Get page source and create BeautifulSoup object
    soup = bs4.BeautifulSoup(response.text, "html.parser")
    
    # Find all divs with class paragWrapper
    parag_divs = soup.find_all("div", class_="paragWrapper")
    
    # Extract text from each div
    texts = []
    for div in parag_divs:
        texts.append(div.get_text())
        
    return "\n".join(texts)

driver = get_chrome_driver()

# URL of the page to scrape
url = "https://www.canlii.org/en/on/onsc/nav/date/2025/"

# Navigate to the page
driver.get(url)

# Find all links within the specified table
links = driver.find_elements(By.CSS_SELECTOR, "#filterableList a")

# Print href attributes for each link
for link in links:
    case_url = link.get_attribute("href")
    case = parse_case(case_url)
    
    filename = case_url.split("/")[-1].split(".")[0]
    with open(f"{RAW_CASES_DIR}/{filename}", "w") as f:
        f.write(case)
    
# Clean up
driver.quit()