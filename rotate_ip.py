#!/usr/bin/env python3
import boto3
import requests
import time
import logging
from botocore.exceptions import ClientError

class IPRotator:
    def __init__(self, 
                 instance_id: str, 
                 eni_id: str, 
                 region: str = "us-east-2", 
                 rotation_limit: int = None,
                 log_file: str = "app.log"):
        """
        Initialize the IP Rotator.

        Args:
            instance_id (str): AWS EC2 instance ID
            eni_id (str): Network Interface ID
            region (str): AWS region name
            rotation_limit (int, optional): Maximum number of IP rotations allowed
        """
        self.instance_id = instance_id
        self.eni_id = eni_id
        self.region = region
        self.rotation_limit = rotation_limit
        self.rotation_count = 0
        self.logger = self.config_logger(log_file)
        self.ec2 = boto3.client("ec2", region_name=region)

    def config_logger(self, log_file):
        # Create handlers
        stream_handler = logging.StreamHandler()
        file_handler = logging.FileHandler(log_file)

        # Create formatter and add it to handlers
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        stream_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        # Add handlers to logger
        logger = logging.getLogger(__name__)
        logger.addHandler(stream_handler)
        logger.addHandler(file_handler)

        # Set level for this specific logger
        logger.setLevel(logging.INFO)
        return logger

    def get_current_public_ip(self):
        """Get the current public IP address using an external service"""
        try:
            response = requests.get("https://api.ipify.org", timeout=5)
            return response.text
        except requests.RequestException as e:
            self.logger.error(f"Error retrieving current IP: {e}")
            raise

    def rotate_elastic_ip(self):
        """
        Rotates the Elastic IP address.

        Returns:
            dict: Information about the new Elastic IP
        """
        if self.rotation_limit and self.rotation_count >= self.rotation_limit:
            self.logger.error("Rotation limit reached")
            raise Exception("Rotation limit reached")

        try:
            # Get the current IP
            old_ip = self.get_current_public_ip()
            self.logger.info(f"Current public IP: {old_ip}")
            
            # Find any existing Elastic IP associated with the instance
            addresses = self.ec2.describe_addresses(
                Filters=[
                    {
                        "Name": "instance-id",
                        "Values": [self.instance_id]
                    }
                ]
            )
            
            old_allocation_id = None
            if addresses["Addresses"]:
                old_allocation_id = addresses["Addresses"][0]["AllocationId"]
                self.logger.info(f"Found existing Elastic IP with allocation ID: {old_allocation_id}")
            
            # Allocate a new Elastic IP
            self.logger.info("Allocating new Elastic IP...")
            new_address = self.ec2.allocate_address(Domain="vpc")
            new_allocation_id = new_address["AllocationId"]
            new_ip = new_address["PublicIp"]
            self.logger.info(f"Allocated new Elastic IP: {new_ip} (AllocationId: {new_allocation_id})")
            
            # Associate the new Elastic IP with the instance
            self.logger.info(f"Associating new Elastic IP with instance {self.instance_id}...")
            self.ec2.associate_address(
                AllocationId=new_allocation_id,
                NetworkInterfaceId=self.eni_id
            )
            
            # Wait for the association to complete
            self.logger.info("Waiting for the new IP to be associated...")
            time.sleep(5)
            
            # Release the old Elastic IP if it exists
            if old_allocation_id:
                self.logger.info(f"Releasing old Elastic IP (AllocationId: {old_allocation_id})...")
                self.ec2.release_address(AllocationId=old_allocation_id)
            
            self.rotation_count += 1
            
            return {
                "old_ip": old_ip,
                "new_ip": new_ip,
                "allocation_id": new_allocation_id,
                "instance_id": self.instance_id
            }
        
        except ClientError as e:
            self.logger.error(f"AWS Error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            raise

    def test_rotation(self):
        """
        Tests the Elastic IP rotation and verifies that the public IP address has changed.

        Returns:
            bool: True if IP rotation was successful, False otherwise
        """
        try:
            # Get the current IP before rotation
            pre_rotation_ip = self.get_current_public_ip()
            self.logger.info(f"Pre-rotation IP: {pre_rotation_ip}")
            
            # Rotate the Elastic IP
            result = self.rotate_elastic_ip()
            
            # Wait for the changes to propagate
            self.logger.info("Waiting for IP changes to propagate...")
            time.sleep(10)
            
            # Get the current IP after rotation
            post_rotation_ip = self.get_current_public_ip()
            self.logger.info(f"Post-rotation IP: {post_rotation_ip}")
            
            # Verify that the IP has changed
            if post_rotation_ip == result["new_ip"]:
                self.logger.info("IP rotation successful! Public IP has been updated.")
                return True
            else:
                self.logger.warning(f"IP verification failed. Expected {result['new_ip']}, got {post_rotation_ip}")
                return False
        
        except Exception as e:
            self.logger.error(f"Error testing IP rotation: {e}")
            return False

# if __name__ == "__main__":
#     INSTANCE_ID = "i-0bd15629230269e08"
#     PRIMARY_ENI = "eni-070a58b722386fce4"
#     REGION = "us-east-2"
    
#     rotator = IPRotator(INSTANCE_ID, PRIMARY_ENI, REGION, rotation_limit=5)
    
#     try:
#         self.logger.info("Starting Elastic IP rotation test...")
#         success = rotator.test_rotation()
        
#         if success:
#             self.logger.info("Elastic IP rotation test completed successfully.")
#             current_ip = rotator.get_current_public_ip()
#             print("\nRotation Results:")
#             print("-----------------")
#             print(f"Status: SUCCESS")
#             print(f"Current IP: {current_ip}")
#             print(f"Rotation Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
#         else:
#             print("\nRotation Results:")
#             print("-----------------")
#             print("Status: FAILED")
#             self.logger.error("Elastic IP rotation test failed.")
    
#     except KeyboardInterrupt:
#         self.logger.info("Script interrupted by user.")
#         print("\nRotation Results:")
#         print("-----------------")
#         print("Status: FAILED")
#         print("Error: Script interrupted by user")
#     except Exception as e:
#         error_message = str(e)
#         self.logger.error(f"Script failed with error: {error_message}")
#         print("\nRotation Results:")
#         print("-----------------")
#         print("Status: FAILED") 
#         print(f"Error: {error_message}")
