import requests
import time
import random
import logging
import os
from threading import Lock
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timedelta
import socket
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.driver_cache import DriverCacheManager
import bs4

from rotate_ip import IPRotator

LOG_FILE = f"logs/scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            filename=LOG_FILE,
            encoding="utf-8"
        )
    ]
)

@dataclass
class IPRotateArgs:
    instance_id: str
    eni_id: str
    region: str = "us-east-2"
    rotation_limit: int = 3
    
@dataclass
class IPRequestStats:
    success: int
    failed: int
    total: int

class BrowserManager:
    def __init__(self, 
                 driver_path="driver", 
                 request_delay=(3, 8), 
                 max_retries=3, 
                 window_size=10, 
                 fail_rate=5,
                 rotation_config: IPRotateArgs = None,
                 interface=None):
        """
        Initialize the browser manager with customizable parameters
        
        Args:
            driver_path (str, optional): Path to chromedriver. If None, will be auto-managed
            request_delay (tuple, optional): Min and max delay between requests in seconds
            max_retries (int, optional): Maximum number of retry attempts
            window_size (int, optional): Size of the sliding window for tracking requests
            max_failures (int, optional): Maximum number of failures allowed in the window
        """
        self.driver_path = Path(driver_path)
        if not self.driver_path.exists():
            os.makedirs(self.driver_path)

        self.request_delay = request_delay
        self.max_retries = max_retries
        
        # window count for failure determination
        self.curr_window = 0
        self.window_size = window_size
        self.request_history = []
        self.fail_rate = 5

        # Request tracking parameters
        self.total_requests = 0
        self.total_failures = 0
        self.total_successes = 0

        self.lock = Lock()

        # rotation
        self._is_rotating_ip = False
        self.ip_windows = []
        if rotation_config:
            self.ip_rotator = IPRotator(
                instance_id=rotation_config.instance_id,
                eni_id=rotation_config.eni_id,
                region=rotation_config.region,
                log_file=LOG_FILE
            )
            # ip-reassignment happen on the boundaries of windows
        else:
            self.ip_rotator = None

        # initialize selenium and requests sessions to send traffic through our inteface
        self.interface = interface
        self.driver = None
        self.session = None
        self.initialize_selenium_driver()
        self.initialize_requests_session()

        # Setup directory for failed requests log
        self.log_dir = Path("logs")
        if not self.log_dir.exists():
            os.makedirs(self.log_dir)
        
        # Failed requests buffer
        self.failed_requests = []
        
        # Initialize logger
        self.logger = logging.getLogger("BrowserManager")
    
    def initialize_selenium_driver(self):
        """Initialize and return a Selenium Chrome WebDriver"""
        if self.driver is not None:
            try:
                self.driver.quit()
            except:
                pass
        
        # Setup Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode (optional)
        if self.interface:
            chrome_options.add_argument(f"--host-resolver-rules=MAP * {self.interface} , EXCLUDE localhost")

        driver_cache = DriverCacheManager(root_dir=Path("driver"))
        driver_path = ChromeDriverManager(cache_manager=driver_cache).install()
        
        # Initialize the driver with existing or new driver
        service = Service(executable_path=driver_path)
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

    def initialize_requests_session(self):
        """Initialize and return a requests Session with retry configuration"""
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            })

            if self.interface:
                # Create an adapter with a source_address
                original_socket = socket.socket
                def patched_socket(*args, **kwargs):
                    s = original_socket(*args, **kwargs)
                    s.bind((self.interface, 0))
                    return s
                
                # Apply the patch
                socket.socket = patched_socket
                                
    def _random_delay(self):
        """Apply a random delay between requests"""
        delay = random.uniform(self.request_delay[0], self.request_delay[1])
        time.sleep(delay)
    
    def _log_failed_request(self, url, error_message, request_type="selenium"):
        """Log a failed request to the buffer and file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "url": url,
            "error": error_message,
            "type": request_type
        }
        self.failed_requests.append(log_entry)
        
        # Write to file
        with open(self.log_dir / "failed_requests.log", "a") as f:
            f.write(f"{timestamp} | {request_type} | {url} | {error_message}\n")
    
    def _update_request_history(self, success):
        """Update request history and check failure threshold"""
        with self.lock:
            self.request_history.append(success)
            
            # Update totals
            self.total_requests += 1
            if success:
                self.total_successes += 1
            else:
                self.total_failures += 1
            
            # Count recent failures
            window_start = len(self.request_history) - 1 - self.window_size
            recent_failures = sum(1 for fail in self.request_history[window_start:] if not success)
            self.logger.info(f"Failure rate: {recent_failures} / {self.window_size}")

            # default is if 5/10 of the last requests fail, we rotate to new IP
            if recent_failures >= self.fail_rate:
                if self.ip_rotator:
                    self.logger.info(f"Recent failures {recent_failures} exceeds {self.fail_rate}, starting IP rotation")
                    self.logger.info(f"")
                    
                    self._is_rotating_ip = True
                    self.ip_rotator.rotate_elastic_ip()
                    self._is_rotating_ip = False

                    # reset stats
                    self.total_failures = 0
                    self.total_successes = 0
                    self.total_requests = 0

                    print("Stats for IP:")
                    print("Total successes: ", self.total_successes)
                    print("Total failures: ", self.total_failures)
                    print("Total requests: ", self.total_requests)
                
                raise Exception(
                    f"Too many failures in time window: {recent_failures} failures in last "
                    f"{self.window_size} minutes. Total requests: {self.total_requests} "
                    f"(Successes: {self.total_successes}, Failures: {self.total_failures})"
                )
            
    def ip_rotation_happening(self):
        return self._is_rotating_ip

    def selenium_get(self, url, css_selector=None, timeout=2):
        """
        Fetch a URL using Selenium with retry logic
        
        Args:
            url (str): URL to fetch
            css_selector (str, optional): CSS selector to wait for
            timeout (int, optional): Timeout in seconds for element waiting
            
        Returns:
            tuple: (success (bool), driver or None, error message or None)
        """
        if self.driver is None:
            self.initialize_selenium_driver()
        
        retries = 0
        while retries < self.max_retries:
            try:
                self.logger.info(f"Fetching {url} with Selenium (attempt {retries + 1})")
                self.driver.get(url)
                
                # Wait for specific element if provided
                if css_selector:
                    WebDriverWait(self.driver, timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
                    )
                                
                # Apply delay before returning
                self._random_delay()
                self._update_request_history(True)  # Track successful request
                return True, self.driver, None
                
            except (TimeoutException, WebDriverException, NoSuchElementException) as e:
                retries += 1
                error_message = f"{type(e).__name__}: {str(e)}"
                self.logger.warning(f"Selenium attempt {retries} failed: {error_message}")

                res = requests.get(url)
                if res.status_code == 429:
                    print("Rate-limit detected for Selenium, rotating IP....")
                    self.ip_rotator.rotate_elastic_ip()  
        
        # Log and track the failed request after max retries
        self._log_failed_request(url, error_message, "selenium")
        self._update_request_history(False)  # Track failed request
        return False, None, error_message
    
    def requests_get(self, url, parser='html.parser'):
        """
        Fetch a URL using requests with retry logic
        
        Args:
            url (str): URL to fetch
            parser (str, optional): BeautifulSoup parser to use
            
        Returns:
            tuple: (success (bool), soup or response, error message or None)
        """        
        retries = 0
        while retries < self.max_retries:
            try:
                self.logger.info(f"Fetching {url} with requests (attempt {retries + 1})")
                response = self.session.get(url, timeout=2)
                
                # Check for error status codes
                response.raise_for_status()
                
                # Check for common error indicators in the content
                error_indicators = ["rate limit exceeded", "too many requests", "access denied"]
                if any(indicator in response.text.lower() for indicator in error_indicators):
                    raise Exception("Detected error page: site is likely rate limiting")
                
                # Apply delay before returning
                self._random_delay()
                
                # Parse the content
                soup = bs4.BeautifulSoup(response.text, parser)
                self._update_request_history(True)  # Track successful request
                return True, soup, None
                
            except Exception as e:
                retries += 1
                error_message = f"{type(e).__name__}: {str(e)}"
                self.logger.warning(f"Requests attempt {retries} failed: {error_message}")
                
                # Log rate limiting
                if "rate" in str(e).lower() or "429" in str(e):
                    self.logger.warning("Detected rate limiting")

        # Log and track the failed request after max retries
        self._log_failed_request(url, error_message, "requests")
        self._update_request_history(False)  # Track failed request
        return False, None, error_message

    
    def close(self):
        """Close all resources"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
        
        if self.session:
            try:
                self.session.close()
            except:
                pass
            self.session = None
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
