#!/usr/bin/env python3
import boto3
import requests
import time
import logging
from botocore.exceptions import ClientError

INSTANCE_ID = "i-0bd15629230269e08"
PRIMARY_ENI = "eni-070a58b722386fce4"
REGION = "us-east-2"

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log")
    ]
)

def get_instance_id():
    """
    Get the current EC2 instance ID using instance metadata service
    """
    try:
        response = requests.get('http://169.254.169.254/latest/meta-data/instance-id', timeout=2)
        return response.text
    except requests.RequestException as e:
        logger.error(f"Error retrieving instance ID: {e}")
        raise

def get_current_public_ip():
    """
    Get the current public IP address using an external service
    """
    try:
        response = requests.get('https://api.ipify.org', timeout=5)
        return response.text
    except requests.RequestException as e:
        logger.error(f"Error retrieving current IP: {e}")
        raise

def rotate_elastic_ip(region=REGION):
    """
    Rotates the Elastic IP address by:
    1. Getting a new Elastic IP from the pool
    2. Associating it with the current instance
    3. Releasing the old Elastic IP

    Args:
        region (str): AWS region

    Returns:
        dict: Information about the new Elastic IP
    """
    try:
        # Initialize AWS EC2 client
        ec2 = boto3.client('ec2', region_name=region)
        
        # Get the instance ID
        instance_id = INSTANCE_ID
        logger.info(f"Current instance ID: {instance_id}")
        
        # Get the current IP
        old_ip = get_current_public_ip()
        logger.info(f"Current public IP: {old_ip}")
        
        # Find any existing Elastic IP associated with the instance
        addresses = ec2.describe_addresses(
            Filters=[
                {
                    'Name': 'instance-id',
                    'Values': [instance_id]
                }
            ]
        )
        
        old_allocation_id = None
        if addresses['Addresses']:
            old_allocation_id = addresses['Addresses'][0]['AllocationId']
            logger.info(f"Found existing Elastic IP with allocation ID: {old_allocation_id}")
        
        # Allocate a new Elastic IP
        logger.info("Allocating new Elastic IP...")
        new_address = ec2.allocate_address(Domain='vpc')
        new_allocation_id = new_address['AllocationId']
        new_ip = new_address['PublicIp']
        logger.info(f"Allocated new Elastic IP: {new_ip} (AllocationId: {new_allocation_id})")
        
        # Associate the new Elastic IP with the instance
        logger.info(f"Associating new Elastic IP with instance {instance_id}...")

        print("PRIMARY ENI: ", PRIMARY_ENI)

        ec2.associate_address(
            AllocationId=new_allocation_id,
            NetworkInterfaceId=PRIMARY_ENI
        )
        
        # Wait for the association to complete
        logger.info("Waiting for the new IP to be associated...")
        time.sleep(5)
        
        # Release the old Elastic IP if it exists
        if old_allocation_id:
            logger.info(f"Releasing old Elastic IP (AllocationId: {old_allocation_id})...")
            ec2.release_address(AllocationId=old_allocation_id)
        
        return {
            'old_ip': old_ip,
            'new_ip': new_ip,
            'allocation_id': new_allocation_id,
            'instance_id': instance_id
        }
    
    except ClientError as e:
        logger.error(f"AWS Error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

def test_ip_rotation(region=REGION):
    """
    Tests the Elastic IP rotation function and verifies that
    the public IP address has changed.

    Args:
        region (str): AWS region

    Returns:
        bool: True if IP rotation was successful, False otherwise
    """
    try:
        # Get the current IP before rotation
        pre_rotation_ip = get_current_public_ip()
        logger.info(f"Pre-rotation IP: {pre_rotation_ip}")
        
        # Rotate the Elastic IP
        result = rotate_elastic_ip(region)
        
        # Wait for the changes to propagate
        logger.info("Waiting for IP changes to propagate...")
        time.sleep(10)
        
        # Get the current IP after rotation
        post_rotation_ip = get_current_public_ip()
        logger.info(f"Post-rotation IP: {post_rotation_ip}")
        
        # Verify that the IP has changed
        if post_rotation_ip == result["new_ip"]:
            logger.info("IP rotation successful! Public IP has been updated.")
            return True
        else:
            logger.warning(f"IP verification failed. Expected {result['new_ip']}, got {post_rotation_ip}")
            return False
    
    except Exception as e:
        logger.error(f"Error testing IP rotation: {e}")
        return False

if __name__ == "__main__":    
    try:
        logger.info("Starting Elastic IP rotation test...")
        success = test_ip_rotation()
        
        if success:
            logger.info("Elastic IP rotation test completed successfully.")
            current_ip = get_current_public_ip()
            print("\nRotation Results:")
            print("-----------------")
            print(f"Status: SUCCESS")
            print(f"Current IP: {current_ip}")
            print(f"Rotation Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Instance ID: {get_instance_id()}")
        else:
            print("\nRotation Results:")
            print("-----------------")
            print("Status: FAILED")
            logger.error("Elastic IP rotation test failed.")
    
    except KeyboardInterrupt:
        logger.info("Script interrupted by user.")
        print("\nRotation Results:")
        print("-----------------")
        print("Status: FAILED")
        print("Error: Script interrupted by user")
    except Exception as e:
        error_message = str(e)
        logger.error(f"Script failed with error: {error_message}")
        print("\nRotation Results:")
        print("-----------------")
        print("Status: FAILED") 
        print(f"Error: {error_message}")
