import logging
import os
from pathlib import Path
from selenium.webdriver.common.by import By
import threading
import time

from typing import Dict
from scraper import BrowserManager, IPRotateArgs
from config import INSTANCE_ID, ENI_ID, ENI_PRIVATE_IP
from enum import Enum

# TODO: 
class CaseProcessResult(Enum):
    ALREADY_EXISTS = "already_exists"
    SUCCESS = "success" 
    RATE_LIMITED = "rate_limited"
    NO_CONTENT = "no_content"

def process_case(case_url, case_file, browser: BrowserManager, results: Dict):
    # Get the case page
    success, soup, status_code = browser.requests_get(case_url)
    if not success:
        if status_code == 429:
            results[case_url] = CaseProcessResult.RATE_LIMITED
            return
        results[case_url] = CaseProcessResult.RATE_LIMITED
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
    
    if not content.strip():
        results[case_url] = CaseProcessResult.NO_CONTENT
        return
    
    # Write to file
    with open(case_file, "w", encoding="utf-8") as f:
        f.write(content)
        
    results[case_url] = CaseProcessResult.SUCCESS

def write_missing_cases(missing_cases, output_file):
    # Read existing missing cases if file exists
    existing_cases = set()
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            existing_cases = set(line.strip() for line in f)
    
    # Only write new missing cases
    new_cases = set(missing_cases) - existing_cases
    if new_cases:
        with open(output_file, "a", encoding="utf-8") as f:
            for case in new_cases:
                f.write(f"{case}\n")

def write_failed_cases(failed_cases, output_file):
    # Read existing missing cases if file exists
    existing_cases = set()
    if os.path.exists(output_file):
        with open(output_file, "r", encoding="utf-8") as f:
            existing_cases = set(line.strip() for line in f)
    
    # Only write new missing cases
    new_cases = set(failed_cases) - existing_cases
    if new_cases:
        with open(output_file, "a", encoding="utf-8") as f:
            for case in new_cases:
                f.write(f"{case}\n")

def filter_non_existing_cases(case_urls, court_dir):
    non_existing_cases = []
    for case_url in case_urls:
        case_id = case_url.split("/")[-1].split(".")[0]
        case_file = court_dir / case_id
        
        if not case_file.exists():
            non_existing_cases.append(case_url)
        else:
            print(f"Skipping existing case: {case_id}")
            
    return non_existing_cases

def click_element_with_js(driver, element):
    """Click an element using JavaScript to bypass overlays"""
    try:
        driver.execute_script("arguments[0].click();", element)
        return True
    except Exception as e:
        print(f"Error clicking with JavaScript: {e}")
        return False

# Main script for scraping law cases using the BrowserManager
def scrape_law_cases():
    missing_cases = []
    failed_cases = []

    # Setup directories
    case_root = Path("cases")
    if not case_root.exists():
        os.makedirs(case_root)
    
    # Initialize the browser manager
    browser = BrowserManager(
        request_delay=(1, 3), 
        max_retries=3,
        window_size=10,
        fail_rate=1,
        rotation_config=IPRotateArgs(
            instance_id=INSTANCE_ID,
            eni_id=ENI_ID,
            region="us-east-2",
            rotation_limit=3
        )
    )

    try:
        # Get the listing page
        TEMPLATE_URL = "https://www.canlii.org/en/on/{court}/nav/date/{date}/"
        list_urls = [
            # ("onca", 1994),
            # ("onsc", 2003),
            ("onsc", 2024)
            # ("onscdc", 2003),
            # ("onscsm", 2014),
            # ("oncj", 2005)
        ]
        for court, begin_year in list_urls:
            for year in range(begin_year, 2026):
                failed_cases = []

                url = TEMPLATE_URL.format(court=court, date=str(year))

                # continuously getting more results from page
                show_more, driver, status_code = browser.selenium_get(url, css_selector=".link.showMoreResults")
                while show_more:
                    element = driver.find_element(By.CSS_SELECTOR, ".link.showMoreResults")
                    click_element_with_js(driver, element)
                    time.sleep(2)
                    links = driver.find_elements(By.CSS_SELECTOR, "#filterableList a")
                    show_more, driver, status_code = browser.selenium_get(url, css_selector=".link.showMoreResults")
                    print("LINKS FOUND: ", len(links))

                success, driver, status_code = browser.selenium_get(url, css_selector="#filterableList")
                if status_code == 429:
                    browser.rotate_ip()
                    success, driver, status_code = browser.selenium_get(url, css_selector="#filterableList")
                    if status_code == 429:
                        raise Exception("Rate limited after IP rotation, WTF????")
                
                court_dir = case_root / court
                if not court_dir.exists():
                    os.makedirs(court_dir)

                if not success:
                    logging.error(f"Date does not exist")
                    continue
                
                # Find all case links
                links = driver.find_elements(By.CSS_SELECTOR, "#filterableList a")
                case_urls = []
                
                for link in links:
                    href = link.get_attribute("href")
                    if href and "/doc/" in href:
                        case_urls.append(href)
                
                logging.info(f"Found {len(case_urls)} case links")
                
                # Process cases using thread pool
                remaining_urls = filter_non_existing_cases(case_urls, court_dir)
                batch_size = 5
                results = []  # Store all results here
                
                while remaining_urls:
                    threads = []
                    # Take next batch of URLs
                    batch_urls = remaining_urls[:batch_size]
                    remaining_urls = remaining_urls[batch_size:]
                    result_container = {}

                    # Create and start threads for this batch
                    for i, case_url in enumerate(batch_urls):                        
                        print(f"Running {i}/{len(case_urls)}")
                        case_id = case_url.split("/")[-1].split(".")[0]
                        case_file = court_dir / case_id

                        # Create thread with target function that will update the result
                        thread = threading.Thread(
                            target=process_case,
                            args=(case_url, case_file, browser, result_container)
                        )
                        thread.start()
                        threads.append(thread)
                    
                    # Wait for all threads in this batch to complete
                    for thread in threads:
                        thread.join()
                    
                    # Now process the results after all threads have joined
                    should_rotate = []
                    for case_url, case_result in result_container.items():
                        success = True
                        if case_result == CaseProcessResult.RATE_LIMITED:
                            failed_cases.append(case_url)
                            success = False
                        elif case_result == CaseProcessResult.NO_CONTENT:
                            missing_cases.append(case_url)
                        elif case_result == CaseProcessResult.SUCCESS:
                            results.append(case_result)

                        should_rotate.append(browser._update_window_and_check_if_rotate(success))

                    if any(should_rotate):
                        browser.rotate_ip()
                        # reprocess this batch
                        remaining_urls = batch_urls + remaining_urls
                        failed_cases = [u for u in failed_cases if u not in batch_urls]
                        missing_cases = [u for u in missing_cases if u not in batch_urls]

                print(f"Failed cases: {failed_cases}")
                write_failed_cases(failed_cases, court_dir / "failed_cases.txt")

    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}", exc_info=True)
    finally:
        browser.close()  

        missing_cases_file = case_root / "missing_cases.txt"
        write_missing_cases(missing_cases, missing_cases_file)

        # Report on failed requests
        if browser.failed_requests:
            logging.warning(f"Total failed requests: {len(browser.failed_requests)}")
            logging.info(f"See logs/failed_requests.log for details")

if __name__ == "__main__":
    scrape_law_cases()