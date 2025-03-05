#!/bin/bash
#
# EC2 Secondary ENI Setup Script
# ------------------------------
# This script creates a secondary Elastic Network Interface (ENI) and attaches it
# to an EC2 instance. It then associates an Elastic IP with this ENI to provide
# a stable SSH connection endpoint. The primary ENI will be rotated separately by
# your Python script.
#
# Usage: ./setup-secondary-eni.sh <instance-id> [region]
#
# Prerequisites:
# - AWS CLI installed and configured with appropriate permissions
# - jq for JSON parsing

set -e  # Exit immediately if a command exits with a non-zero status

# Parse arguments
INSTANCE_ID=$1
REGION=${2:-$(aws configure get region)}  # Use provided region or default from AWS config

if [ -z "$INSTANCE_ID" ]; then
    echo "Error: Instance ID is required."
    echo "Usage: $0 <instance-id> [region]"
    exit 1
fi

# Check dependencies
if ! command -v jq &> /dev/null; then
    echo "Installing jq..."
    sudo apt-get update && sudo apt-get install -y jq || sudo yum install -y jq
fi

echo "=== EC2 Secondary ENI Setup ==="
echo "Instance ID: $INSTANCE_ID"
echo "Region: $REGION"
echo "================================"

# Get instance details
echo "Retrieving instance details..."
INSTANCE_INFO=$(aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --region "$REGION" \
    --output json)

# Extract subnet ID and security group ID from the primary ENI
SUBNET_ID=$(echo "$INSTANCE_INFO" | jq -r '.Reservations[0].Instances[0].SubnetId')
SECURITY_GROUP_IDS=$(echo "$INSTANCE_INFO" | jq -r '.Reservations[0].Instances[0].SecurityGroups[].GroupId' | tr '\n' ' ')
AZ=$(echo "$INSTANCE_INFO" | jq -r '.Reservations[0].Instances[0].Placement.AvailabilityZone')
PRIMARY_ENI_ID=$(echo "$INSTANCE_INFO" | jq -r '.Reservations[0].Instances[0].NetworkInterfaces[0].NetworkInterfaceId')
PRIMARY_PRIVATE_IP=$(echo "$INSTANCE_INFO" | jq -r '.Reservations[0].Instances[0].PrivateIpAddress')
PRIMARY_PUBLIC_IP=$(echo "$INSTANCE_INFO" | jq -r '.Reservations[0].Instances[0].PublicIpAddress')

echo "Primary ENI ID: $PRIMARY_ENI_ID"
echo "Primary Private IP: $PRIMARY_PRIVATE_IP"
echo "Primary Public IP: $PRIMARY_PUBLIC_IP"
echo "Subnet ID: $SUBNET_ID"
echo "Security Group IDs: $SECURITY_GROUP_IDS"
echo "Availability Zone: $AZ"

# Create a secondary ENI
echo "Creating secondary ENI..."
SECONDARY_ENI_OUTPUT=$(aws ec2 create-network-interface \
    --subnet-id "$SUBNET_ID" \
    --description "SSH Connection ENI for $INSTANCE_ID" \
    --groups $SECURITY_GROUP_IDS \
    --region "$REGION" \
    --output json)

SECONDARY_ENI_ID=$(echo "$SECONDARY_ENI_OUTPUT" | jq -r '.NetworkInterface.NetworkInterfaceId')
SECONDARY_PRIVATE_IP=$(echo "$SECONDARY_ENI_OUTPUT" | jq -r '.NetworkInterface.PrivateIpAddress')

echo "Secondary ENI created:"
echo "  ENI ID: $SECONDARY_ENI_ID"
echo "  Private IP: $SECONDARY_PRIVATE_IP"

# Attach the secondary ENI to the instance
echo "Attaching secondary ENI to instance..."
aws ec2 attach-network-interface \
    --network-interface-id "$SECONDARY_ENI_ID" \
    --instance-id "$INSTANCE_ID" \
    --device-index 1 \
    --region "$REGION"

echo "Secondary ENI attached to instance."

# Allocate an Elastic IP
echo "Allocating Elastic IP..."
EIP_OUTPUT=$(aws ec2 allocate-address \
    --domain vpc \
    --region "$REGION" \
    --output json)

EIP_ALLOCATION_ID=$(echo "$EIP_OUTPUT" | jq -r '.AllocationId')
EIP_PUBLIC_IP=$(echo "$EIP_OUTPUT" | jq -r '.PublicIp')

echo "Elastic IP allocated:"
echo "  Allocation ID: $EIP_ALLOCATION_ID"
echo "  Public IP: $EIP_PUBLIC_IP"

# Associate Elastic IP with the secondary ENI
echo "Associating Elastic IP with secondary ENI..."
ASSOC_OUTPUT=$(aws ec2 associate-address \
    --allocation-id "$EIP_ALLOCATION_ID" \
    --network-interface-id "$SECONDARY_ENI_ID" \
    --region "$REGION" \
    --output json)

ASSOC_ID=$(echo "$ASSOC_OUTPUT" | jq -r '.AssociationId')

echo "Elastic IP associated with secondary ENI:"
echo "  Association ID: $ASSOC_ID"

# Wait for the association to stabilize
echo "Waiting for network changes to stabilize..."
sleep 15

# Print the configuration summary
echo ""
echo "=== Configuration Summary ==="
echo "Instance ID: $(aws ec2 describe-instances --instance-ids $INSTANCE_ID --region $REGION --query 'Reservations[0].Instances[0].InstanceId' --output text)"
echo ""
echo "Primary Network Interface (for scraping, IP will be rotated by your Python script):"
echo "  ENI ID: $(aws ec2 describe-network-interfaces --network-interface-ids $PRIMARY_ENI_ID --region $REGION --query 'NetworkInterfaces[0].NetworkInterfaceId' --output text)"
echo "  Private IP: $(aws ec2 describe-network-interfaces --network-interface-ids $PRIMARY_ENI_ID --region $REGION --query 'NetworkInterfaces[0].PrivateIpAddress' --output text)"
echo "  Public IP: $(aws ec2 describe-network-interfaces --network-interface-ids $PRIMARY_ENI_ID --region $REGION --query 'NetworkInterfaces[0].Association.PublicIp' --output text)"
echo ""
echo "Secondary Network Interface (for stable SSH):"
echo "  ENI ID: $(aws ec2 describe-network-interfaces --network-interface-ids $SECONDARY_ENI_ID --region $REGION --query 'NetworkInterfaces[0].NetworkInterfaceId' --output text)"
echo "  Private IP: $(aws ec2 describe-network-interfaces --network-interface-ids $SECONDARY_ENI_ID --region $REGION --query 'NetworkInterfaces[0].PrivateIpAddress' --output text)"
echo "  Elastic IP: $(aws ec2 describe-network-interfaces --network-interface-ids $SECONDARY_ENI_ID --region $REGION --query 'NetworkInterfaces[0].Association.PublicIp' --output text)"
echo ""
echo "SSH Connection Commands:"
echo "  Connect via Stable Secondary IP: ssh ubuntu@$(aws ec2 describe-network-interfaces --network-interface-ids $SECONDARY_ENI_ID --region $REGION --query 'NetworkInterfaces[0].Association.PublicIp' --output text)"
echo ""
echo "Python Script Configuration:"
echo "  Update your Python rotation script to specifically target ENI ID: $(aws ec2 describe-network-interfaces --network-interface-ids $PRIMARY_ENI_ID --region $REGION --query 'NetworkInterfaces[0].NetworkInterfaceId' --output text)"
echo "  This will leave your SSH connection (via $(aws ec2 describe-network-interfaces --network-interface-ids $SECONDARY_ENI_ID --region $REGION --query 'NetworkInterfaces[0].Association.PublicIp' --output text)) unaffected"
echo "==============================="

# Create a configuration file for the Python script
cat > primary_eni_config.json << EOL
{
  "instance_id": "$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --region $REGION --query 'Reservations[0].Instances[0].InstanceId' --output text)",
  "primary_eni_id": "$(aws ec2 describe-network-interfaces --network-interface-ids $PRIMARY_ENI_ID --region $REGION --query 'NetworkInterfaces[0].NetworkInterfaceId' --output text)",
  "primary_private_ip": "$(aws ec2 describe-network-interfaces --network-interface-ids $PRIMARY_ENI_ID --region $REGION --query 'NetworkInterfaces[0].PrivateIpAddress' --output text)",
  "secondary_eni_id": "$(aws ec2 describe-network-interfaces --network-interface-ids $SECONDARY_ENI_ID --region $REGION --query 'NetworkInterfaces[0].NetworkInterfaceId' --output text)", 
  "secondary_ip": "$(aws ec2 describe-network-interfaces --network-interface-ids $SECONDARY_ENI_ID --region $REGION --query 'NetworkInterfaces[0].Association.PublicIp' --output text)",
  "region": "$REGION"
}
EOL

echo "Created configuration file 'primary_eni_config.json' for your Python rotation script."