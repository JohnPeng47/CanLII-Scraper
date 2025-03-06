import logging
import os
from pathlib import Path
from selenium.webdriver.common.by import By
from concurrent.futures import ThreadPoolExecutor
import time

from scraper import BrowserManager, IPRotateArgs
from config import INSTANCE_ID, ENI_ID, ENI_PRIVATE_IP

def process_case(case_url, court_dir, browser: BrowserManager):
    # Extract case ID from URL for tracking
    case_id = case_url.split("/")[-1].split(".")[0]
    case_file = court_dir / case_id
    
    # Skip if already downloaded
    if case_file.exists():
        logging.info(f"Skipping already downloaded case: {case_id}")
        return
    
    # Get the case page
    success, soup, error = browser.requests_get(case_url)
    if not success:
        logging.error(f"Failed to load case page {case_id}: {error}")
        return
    
    # Extract the content
    parag_divs = soup.select("div.paragWrapper")
    texts = []
    
    for div in parag_divs:
        text = div.get_text().strip()
        if text:
            texts.append(text)
    
    # Save the content
    content = "\n".join(texts)
    
    # Skip if no content
    if not content.strip():
        logging.warning(f"No content found for case {case_id}")
        return
    
    # Write to file
    with open(case_file, "w", encoding="utf-8") as f:
        f.write(content)
        
    logging.info(f"Successfully saved case {case_id}")

# Main script for scraping law cases using the BrowserManager
def scrape_law_cases():
    # Setup directories
    case_root = Path("cases")
    if not case_root.exists():
        os.makedirs(case_root)
    
    # Initialize the browser manager
    browser = BrowserManager(
        request_delay=(4, 10), 
        max_retries=3,
        rotation_config=IPRotateArgs(
            instance_id=INSTANCE_ID,
            eni_id=ENI_ID,
            region="us-east-2",
            rotation_limit=3
        )
    )
    
    _, driver,_ = browser.selenium_get("https://api.ipify.org")
    html = driver.page_source
    public_ip = driver.find_element("tag name", "pre").text
    print(f"Request sent through public IP: {public_ip}")
    print(f"HTML content: {html}")

    _, soup, _ = browser.requests_get("https://api.ipify.org")
    print(soup.prettify())


    # try:
    #     # Get the listing page
    #     TEMPLATE_URL = "https://www.canlii.org/en/on/{court}/nav/date/{date}/"
    #     list_urls = [
    #         # ("onca", 1994),
    #         # ("onsc", 2003),
    #         ("onsc", 2024)
    #         # ("onscdc", 2003),
    #         # ("onscsm", 2014),
    #         # ("oncj", 2005)
    #     ]
    #     for court, begin_year in list_urls:
    #         for year in range(begin_year, 2026):
    #             url = TEMPLATE_URL.format(court=court, date=str(year))
    #             success, driver, error = browser.selenium_get(url, css_selector="#filterableList")
    #             court_dir = case_root / court
    #             if not court_dir.exists():
    #                 os.makedirs(court_dir)

    #             if not success:
    #                 logging.error(f"Date does not exist: {error}")
    #                 continue
                
    #             # Find all case links
    #             links = driver.find_elements(By.CSS_SELECTOR, "#filterableList a")
    #             case_urls = []
                
    #             for link in links:
    #                 href = link.get_attribute("href")
    #                 if href and "/doc/" in href:
    #                     case_urls.append(href)
                
    #             logging.info(f"Found {len(case_urls)} case links")
                
    #             # Process cases using thread pool
    #             with ThreadPoolExecutor(max_workers=5) as executor:
    #                 futures = []
    #                 for case_url in case_urls:
    #                     # Wait if IP rotation is happening
    #                     while browser.ip_rotation_happening():
    #                         print("Waiting for ip_rotation ...")
    #                         time.sleep(2.5)
                            
    #                     # Submit task to thread pool
    #                     future = executor.submit(process_case, case_url, court_dir, browser)
    #                     futures.append(future)
                    
    #                 # Wait for all tasks to complete
    #                 for future in futures:
    #                     future.result()

    # except Exception as e:
    #     logging.error(f"Unexpected error: {str(e)}", exc_info=True)
    # finally:
    #     browser.close()

    #     # stats = browser.get_requests_stats()
    #     # print(stats)

    #     # Report on failed requests
    #     if browser.failed_requests:
    #         logging.warning(f"Total failed requests: {len(browser.failed_requests)}")
    #         logging.info(f"See logs/failed_requests.log for details")


if __name__ == "__main__":
    scrape_law_cases()