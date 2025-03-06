from rotate_ip import IPRotator
from scraper import BrowserManager, IPRotateArgs

INSTANCE_ID = "i-0bd15629230269e08"
PRIMARY_ENI = "eni-070a58b722386fce4"
REGION = "us-east-2"

rotator = IPRotator(INSTANCE_ID, PRIMARY_ENI, REGION, rotation_limit=5)

# Initialize the browser manager
browser = BrowserManager(
    request_delay=(1, 3), 
    max_retries=3,
    window_size=10,
    fail_rate=1,
    rotation_config=IPRotateArgs(
        instance_id=INSTANCE_ID,
        eni_id=PRIMARY_ENI,
        region="us-east-2",
        rotation_limit=3
    )
)
browser.selenium_get("https://google.ca")
browser.requests_get("https://google.ca")

try:
    print("Starting Elastic IP rotation test...")
    success = rotator.test_rotation()
    
    if success:
        print("Elastic IP rotation test completed successfully.")
        print("\nRotation Results:")
        print("-----------------")
        print(f"Status: SUCCESS")
        print(f"Current IP: {rotator.get_current_public_ip()}")
    else:
        print("\nRotation Results:")
        print("-----------------")
        print("Status: FAILED")
        print("Elastic IP rotation test failed.")

except KeyboardInterrupt:
    print("Script interrupted by user.")
    print("\nRotation Results:")
    print("-----------------")
    print("Status: FAILED")
    print("Error: Script interrupted by user")
except Exception as e:
    error_message = str(e)
    print(f"Script failed with error: {error_message}")
    print("\nRotation Results:")
    print("-----------------")
    print("Status: FAILED") 
    print(f"Error: {error_message}")
