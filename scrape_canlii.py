import logging
import os
from pathlib import Path
from selenium.webdriver.common.by import By
from scraper import BrowserManager

# Main script for scraping law cases using the BrowserManager
def scrape_law_cases():
    # Setup directories
    cases_dir = Path("cases")
    if not cases_dir.exists():
        os.makedirs(cases_dir)
    
    # Initialize the browser manager
    browser = BrowserManager(request_delay=(4, 10), max_retries=3)
    
    try:
        # Get the listing page
        list_url = "https://www.canlii.org/en/on/onsc/nav/date/2025/"
        success, driver, error = browser.selenium_get(list_url, css_selector="#filterableList")
        
        if not success:
            logging.error(f"Failed to load listing page: {error}")
            return
        
        # Find all case links
        links = driver.find_elements(By.CSS_SELECTOR, "#filterableList a")
        case_urls = []
        
        for link in links:
            href = link.get_attribute("href")
            if href and "/doc/" in href:
                case_urls.append(href)
        
        logging.info(f"Found {len(case_urls)} case links")
        
        # Process each case
        for case_url in case_urls:
            # Extract case ID from URL for tracking
            case_id = case_url.split("/")[-1].split(".")[0]
            case_file = cases_dir / case_id
            
            # Skip if already downloaded
            if case_file.exists():
                logging.info(f"Skipping already downloaded case: {case_id}")
                continue
            
            # Get the case page
            success, driver, error = browser.selenium_get(case_url, css_selector="div.paragWrapper")
            
            if not success:
                logging.error(f"Failed to load case page {case_id}: {error}")
                continue
            
            # Extract the content
            parag_divs = driver.find_elements(By.CSS_SELECTOR, "div.paragWrapper")
            texts = []
            
            for div in parag_divs:
                text = div.text.strip()
                if text:
                    texts.append(text)
            
            # Save the content
            content = "\n".join(texts)
            
            # Skip if no content
            if not content.strip():
                logging.warning(f"No content found for case {case_id}")
                continue
            
            # Write to file
            with open(case_file, "w", encoding="utf-8") as f:
                f.write(content)
                
            logging.info(f"Successfully saved case {case_id}")
            
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}", exc_info=True)
    finally:
        browser.close()
        
        # Report on failed requests
        if browser.failed_requests:
            logging.warning(f"Total failed requests: {len(browser.failed_requests)}")
            logging.info(f"See logs/failed_requests.log for details")


if __name__ == "__main__":
    scrape_law_cases()