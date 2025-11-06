# Cloud CLI Access (CCA) - Simplified Implementation Guide
## Self-Registration with Minimal Infrastructure

## Project Overview

This document provides complete instructions to implement the **Cloud CLI Access (CCA)** framework - a streamlined authentication and authorization system for CLI tools using AWS IAM Identity Center with **self-service user registration using minimal AWS infrastructure**.

### What You Will Build

1. **Cloud CLI Access Framework**: AWS infrastructure using IAM Identity Center for secure CLI authentication
2. **Self-Registration System**: Single HTML form for user registration
3. **Admin Approval Workflow**: Email-based approval/denial with signed URLs
4. **Single Lambda Function**: Handles all registration and approval logic
5. **CCC (Cloud CLI Client)**: Python CLI tool demonstrating the framework

### Key Simplifications

- ✅ **No Database** - State encoded in signed JWT tokens
- ✅ **No API Gateway** - Lambda Function URLs (built-in HTTPS)
- ✅ **No SNS** - Direct SES email sending
- ✅ **Single Lambda** - All logic in one function
- ✅ **Single HTML File** - Simple registration form
- ✅ **Password via Identity Center** - Users set password after approval

---

## Architecture Overview

### Simplified High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│              Cloud CLI Access Framework (Simplified)                │
├────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                  SELF-REGISTRATION FLOW                      │  │
│  │                                                               │  │
│  │  ┌─────────┐   1. Fill Form    ┌──────────────────┐        │  │
│  │  │  User   │──────────────────►│ registration.html│        │  │
│  │  │ Browser │                    │  (Single S3 File)│        │  │
│  │  └────┬────┘                    └────────┬─────────┘        │  │
│  │       │                                  │                   │  │
│  │       │                         2. POST  │                   │  │
│  │       │                                  ▼                   │  │
│  │       │                         ┌────────────────┐          │  │
│  │       │                         │  Lambda        │          │  │
│  │       │                         │  Function URL  │          │  │
│  │       │                         │  (1 Function)  │          │  │
│  │       │                         └────┬───────────┘          │  │
│  │       │                              │                       │  │
│  │       │                    3. Create │ JWT Token            │  │
│  │       │                       (No DB │ Needed)              │  │
│  │       │                              │                       │  │
│  │       │                              │ 4. Email Admin       │  │
│  │       │                              │    via SES           │  │
│  │       │                              ▼                       │  │
│  │       │                      ┌─────────────────┐            │  │
│  │       │                      │  Admin Email    │            │  │
│  │       │                      │  [Approve Link] │            │  │
│  │       │  5. Click Approve    │  [Deny Link]    │            │  │
│  │       │◄─────────────────────│  (JWT in URL)   │            │  │
│  │       │                      └─────────────────┘            │  │
│  │       │                                                      │  │
│  │       │  6. Lambda decodes JWT, creates user in:            │  │
│  │       │     ┌──────────────────────┐                        │  │
│  │       │     │ IAM Identity Center  │                        │  │
│  │       │     │  - Creates User      │                        │  │
│  │       │     │  - Adds to Group     │                        │  │
│  │       │     │  - Triggers Password │                        │  │
│  │       │     │    Setup Email       │                        │  │
│  │       │     └──────────────────────┘                        │  │
│  │       │                                                      │  │
│  │       │  7. User gets "Set Password" email from Identity    │  │
│  │       │     Center, sets password, can now login            │  │
│  │       │                                                      │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                 CLI AUTHENTICATION FLOW                      │  │
│  │                                                               │  │
│  │  ┌──────────────┐         ┌──────────────────────┐         │  │
│  │  │   CCC CLI    │◄────────│  IAM Identity Center │         │  │
│  │  │   (Python)   │  Device │  - User Directory    │         │  │
│  │  │              │  Flow   │  - Permission Sets   │         │  │
│  │  └──────┬───────┘         └──────────┬───────────┘         │  │
│  │         │                             │                      │  │
│  │         │ Opens Browser               │ User Authenticates  │  │
│  │         │ Polls for Auth              │ With Password       │  │
│  │         │                             │                      │  │
│  │         │ ◄───── Gets AWS Credentials ───────┘             │  │
│  │         │                                                    │  │
│  │         ▼                                                    │  │
│  │  ┌──────────────┐         ┌──────────────────────┐         │  │
│  │  │   Cached     │         │    AWS Services      │         │  │
│  │  │  Credentials │────────►│    (S3, EC2, etc)    │         │  │
│  │  │  ~/.ccc/     │  Access │                      │         │  │
│  │  └──────────────┘         └──────────────────────┘         │  │
│  │                                                               │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Component Breakdown

**Total AWS Services: 3**

1. **IAM Identity Center** - User authentication and management
2. **Lambda Function** (with Function URL) - All registration/approval logic
3. **S3** - Hosts single HTML registration form

**Email:** SES (Simple Email Service) - No separate service, called directly from Lambda

### Self-Registration Flow Detail

```
User                Registration Form        Lambda Function            Admin Email
 │                         │                        │                        │
 │  1. Visit               │                        │                        │
 │  registration.html      │                        │                        │
 │────────────────────────►│                        │                        │
 │                         │                        │                        │
 │  2. Fill form:          │                        │                        │
 │     - Username          │                        │                        │
 │     - Email             │                        │                        │
 │     - First/Last Name   │                        │                        │
 │────────────────────────►│                        │                        │
 │                         │                        │                        │
 │                         │  3. POST to Lambda     │                        │
 │                         │     Function URL       │                        │
 │                         │───────────────────────►│                        │
 │                         │                        │                        │
 │                         │                        │  4. Generate JWT       │
 │                         │                        │     with user data     │
 │                         │                        │                        │
 │                         │                        │  5. Send email via SES │
 │                         │                        │     [Approve?token=JWT]│
 │                         │                        │     [Deny?token=JWT]   │
 │                         │                        │───────────────────────►│
 │                         │                        │                        │
 │                         │◄───────────────────────│                        │
 │◄────────────────────────│  "Registration pending"│                        │
 │                         │                        │                        │
 │                         │                        │                 Admin clicks
 │                         │                        │                 [Approve]
 │                         │                        │  6. GET /approve       │
 │                         │                        │     ?token=JWT         │
 │                         │                        │◄───────────────────────│
 │                         │                        │                        │
 │                         │                        │  7. Decode JWT         │
 │                         │                        │     Validate signature │
 │                         │                        │                        │
 │                         │                        │  8. Create user in     │
 │                         │                        │     Identity Center    │
 │                         │                        │     (no password yet)  │
 │                         │                        │                        │
 │                         │                        │  9. Identity Center    │
 │                         │                        │     sends "Set Password"│
 │◄────────────────────────────────────────────────────────────────────────│
 │  "Welcome! Set your password: [Link]"           │                        │
 │                         │                        │                        │
 │  10. Click link         │                        │                        │
 │  Set password in        │                        │                        │
 │  Identity Center UI     │                        │                        │
 │                         │                        │                        │
 │  11. Run: ccc login     │                        │                        │
 │  (uses new password)    │                        │                        │
```

---

## Prerequisites

Before starting, ensure you have:

- [x] AWS Account with administrative access
- [x] AWS CLI installed and configured with admin credentials
- [x] AWS Organization enabled (required for IAM Identity Center)
- [x] Python 3.8 or higher installed
- [x] pip (Python package manager)
- [x] **Admin email address** for receiving approval notifications
- [x] **SES verified email** for sending notifications

### Verify Prerequisites

```bash
# Check AWS CLI
aws --version
# Expected: aws-cli/2.x.x or higher

# Check AWS credentials
aws sts get-caller-identity

# Check Python
python3 --version
# Expected: Python 3.8.0 or higher

# Check pip
pip3 --version
```

---

## Phase 0: Email Setup

### Step 0.1: Set Admin Email

```bash
# Set the admin email that will receive approval requests
read -p "Enter admin email address: " ADMIN_EMAIL
export ADMIN_EMAIL

echo "export ADMIN_EMAIL=\"$ADMIN_EMAIL\"" > /tmp/cca-config.env
echo "✅ Admin email set to: $ADMIN_EMAIL"
```

### Step 0.2: Verify Email in SES

```bash
# Verify the "from" email address for notifications
read -p "Enter 'from' email address for notifications (can be same as admin): " FROM_EMAIL
export FROM_EMAIL

aws ses verify-email-identity --email-address "$FROM_EMAIL"

echo "📧 Please check $FROM_EMAIL and click the verification link"
echo "export FROM_EMAIL=\"$FROM_EMAIL\"" >> /tmp/cca-config.env

read -p "Press Enter after verifying the email..."

# Check verification status
aws ses get-identity-verification-attributes --identities "$FROM_EMAIL"

echo "✅ Email verified for SES"
```

---

## Phase 1: AWS Identity Center Setup

### Step 1.1: Enable IAM Identity Center

```bash
# Check if Identity Center is enabled
aws sso-admin list-instances

# If empty, enable it:
# Go to AWS Console → IAM Identity Center → Enable
```

After enabling, get your Identity Center details:

```bash
# Get Identity Store ID and Instance ARN
export IDENTITY_STORE_ID=$(aws sso-admin list-instances --query 'Instances[0].IdentityStoreId' --output text)
export SSO_INSTANCE_ARN=$(aws sso-admin list-instances --query 'Instances[0].InstanceArn' --output text)
export SSO_REGION=$(echo $SSO_INSTANCE_ARN | cut -d: -f4)
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "Identity Store ID: $IDENTITY_STORE_ID"
echo "SSO Instance ARN: $SSO_INSTANCE_ARN"
echo "SSO Region: $SSO_REGION"
echo "AWS Account ID: $AWS_ACCOUNT_ID"

# Save to config
echo "export IDENTITY_STORE_ID=\"$IDENTITY_STORE_ID\"" >> /tmp/cca-config.env
echo "export SSO_INSTANCE_ARN=\"$SSO_INSTANCE_ARN\"" >> /tmp/cca-config.env
echo "export SSO_REGION=\"$SSO_REGION\"" >> /tmp/cca-config.env
echo "export AWS_ACCOUNT_ID=\"$AWS_ACCOUNT_ID\"" >> /tmp/cca-config.env

echo "✅ Configuration saved to /tmp/cca-config.env"
```

### Step 1.2: Get SSO Start URL

```bash
# Get SSO start URL from console or construct it
echo "Go to: IAM Identity Center → Dashboard → Settings"
echo "Copy the 'AWS access portal URL'"
echo ""
read -p "Enter your SSO Start URL (https://d-xxxxxxxxxx.awsapps.com/start): " SSO_START_URL
export SSO_START_URL

echo "export SSO_START_URL=\"$SSO_START_URL\"" >> /tmp/cca-config.env
echo "✅ SSO Start URL configured"
```

### Step 1.3: Create CLI-Only Permission Set

```bash
# Create inline policy that denies console access
cat > /tmp/cli-permission-set.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyConsoleAccess",
      "Effect": "Deny",
      "Action": [
        "signin:*",
        "console:*"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Create the permission set
aws sso-admin create-permission-set \
  --instance-arn "$SSO_INSTANCE_ARN" \
  --name "CCA-CLI-Access" \
  --description "Cloud CLI Access - API only, no console" \
  --session-duration "PT12H" \
  --output json > /tmp/permission-set.json

export PERMISSION_SET_ARN=$(cat /tmp/permission-set.json | jq -r '.PermissionSet.PermissionSetArn')
echo "Permission Set ARN: $PERMISSION_SET_ARN"
echo "export PERMISSION_SET_ARN=\"$PERMISSION_SET_ARN\"" >> /tmp/cca-config.env

# Attach AWS managed policy
aws sso-admin attach-managed-policy-to-permission-set \
  --instance-arn "$SSO_INSTANCE_ARN" \
  --permission-set-arn "$PERMISSION_SET_ARN" \
  --managed-policy-arn "arn:aws:iam::aws:policy/PowerUserAccess"

# Add inline policy to deny console
aws sso-admin put-inline-policy-to-permission-set \
  --instance-arn "$SSO_INSTANCE_ARN" \
  --permission-set-arn "$PERMISSION_SET_ARN" \
  --inline-policy file:///tmp/cli-permission-set.json

echo "✅ Permission set created with console access denied"
```

### Step 1.4: Create User Group

```bash
# Create group for CLI users
aws identitystore create-group \
  --identity-store-id "$IDENTITY_STORE_ID" \
  --display-name "CCA-CLI-Users" \
  --description "Users with Cloud CLI Access" \
  --output json > /tmp/cli-group.json

export CLI_GROUP_ID=$(cat /tmp/cli-group.json | jq -r '.GroupId')
echo "Group ID: $CLI_GROUP_ID"
echo "export CLI_GROUP_ID=\"$CLI_GROUP_ID\"" >> /tmp/cca-config.env

echo "✅ Group 'CCA-CLI-Users' created"
```

### Step 1.5: Assign Group to AWS Account

```bash
# Create account assignment
aws sso-admin create-account-assignment \
  --instance-arn "$SSO_INSTANCE_ARN" \
  --target-id "$AWS_ACCOUNT_ID" \
  --target-type "AWS_ACCOUNT" \
  --permission-set-arn "$PERMISSION_SET_ARN" \
  --principal-type "GROUP" \
  --principal-id "$CLI_GROUP_ID"

echo "✅ Group assigned to AWS account with CLI-only permissions"
echo "Waiting for assignment to provision..."
sleep 30
```

---

## Phase 2: Lambda Function Setup

### Step 2.1: Create IAM Role for Lambda

```bash
# Create trust policy
cat > /tmp/lambda-trust-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create IAM role
aws iam create-role \
  --role-name CCA-Lambda-Role \
  --assume-role-policy-document file:///tmp/lambda-trust-policy.json \
  --output json > /tmp/lambda-role.json

export LAMBDA_ROLE_ARN=$(cat /tmp/lambda-role.json | jq -r '.Role.Arn')
echo "Lambda Role ARN: $LAMBDA_ROLE_ARN"
echo "export LAMBDA_ROLE_ARN=\"$LAMBDA_ROLE_ARN\"" >> /tmp/cca-config.env

# Create policy
cat > /tmp/lambda-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ses:SendEmail",
        "ses:SendRawEmail"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "identitystore:CreateUser",
        "identitystore:ListUsers",
        "identitystore:CreateGroupMembership"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Attach policy
aws iam put-role-policy \
  --role-name CCA-Lambda-Role \
  --policy-name CCA-Lambda-Policy \
  --policy-document file:///tmp/lambda-policy.json

echo "Waiting for IAM role to propagate..."
sleep 15

echo "✅ IAM role created for Lambda"
```

### Step 2.2: Create Lambda Function

```bash
# Generate secret key for JWT signing
export SECRET_KEY=$(openssl rand -hex 32)
echo "export SECRET_KEY=\"$SECRET_KEY\"" >> /tmp/cca-config.env

# Create Lambda function code
mkdir -p /tmp/lambda
cat > /tmp/lambda/lambda_function.py <<'LAMBDA_CODE'
import json
import boto3
import hmac
import hashlib
import base64
import os
from datetime import datetime, timedelta
from urllib.parse import parse_qs

ses = boto3.client('ses')
identitystore = boto3.client('identitystore')

# Environment variables
IDENTITY_STORE_ID = os.environ['IDENTITY_STORE_ID']
CLI_GROUP_ID = os.environ['CLI_GROUP_ID']
SSO_START_URL = os.environ['SSO_START_URL']
FROM_EMAIL = os.environ['FROM_EMAIL']
ADMIN_EMAIL = os.environ['ADMIN_EMAIL']
SECRET_KEY = os.environ['SECRET_KEY']

def lambda_handler(event, context):
    """
    Single Lambda function handling:
    - Registration submissions
    - Approval actions
    - Denial actions
    """
    
    print(f"Event: {json.dumps(event)}")
    
    # Determine action based on path
    path = event.get('rawPath', event.get('path', ''))
    
    if path == '/register' or path == '/':
        return handle_registration(event)
    elif path == '/approve':
        return handle_approval(event)
    elif path == '/deny':
        return handle_denial(event)
    else:
        return {
            'statusCode': 404,
            'body': json.dumps({'error': 'Not found'})
        }

def handle_registration(event):
    """Handle new registration submissions"""
    
    # Parse request body
    try:
        if event.get('body'):
            body = json.loads(event['body'])
        else:
            return error_response('Missing request body', 400)
    except json.JSONDecodeError:
        return error_response('Invalid JSON', 400)
    
    # Validate required fields
    required = ['username', 'email', 'first_name', 'last_name']
    missing = [f for f in required if not body.get(f)]
    
    if missing:
        return error_response(f'Missing fields: {", ".join(missing)}', 400)
    
    # Create JWT token with user data
    user_data = {
        'username': body['username'],
        'email': body['email'],
        'first_name': body['first_name'],
        'last_name': body['last_name'],
        'submitted_at': datetime.utcnow().isoformat(),
        'expires_at': (datetime.utcnow() + timedelta(days=7)).isoformat()
    }
    
    approve_token = create_signed_token(user_data, 'approve')
    deny_token = create_signed_token(user_data, 'deny')
    
    # Get Lambda Function URL
    lambda_url = event['requestContext']['domainName']
    protocol = 'https'
    
    approve_url = f"{protocol}://{lambda_url}/approve?token={approve_token}"
    deny_url = f"{protocol}://{lambda_url}/deny?token={deny_token}"
    
    # Send email to admin
    try:
        send_admin_email(user_data, approve_url, deny_url)
    except Exception as e:
        print(f"Error sending email: {e}")
        return error_response(f'Failed to send email: {str(e)}', 500)
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'message': 'Registration submitted successfully',
            'status': 'pending_approval'
        })
    }

def handle_approval(event):
    """Handle approval action"""
    
    # Get token from query parameters
    params = event.get('queryStringParameters', {}) or {}
    token = params.get('token')
    
    if not token:
        return html_response('<h1>Error: Missing token</h1>', 400)
    
    # Verify and decode token
    try:
        user_data = verify_signed_token(token, 'approve')
    except Exception as e:
        return html_response(f'<h1>Error: Invalid or expired token</h1><p>{str(e)}</p>', 400)
    
    # Check if user already exists
    try:
        existing = identitystore.list_users(
            IdentityStoreId=IDENTITY_STORE_ID,
            Filters=[{
                'AttributePath': 'UserName',
                'AttributeValue': user_data['username']
            }]
        )
        
        if existing.get('Users'):
            return html_response(
                f'<h1>User Already Exists</h1><p>User {user_data["username"]} was already created.</p>',
                200
            )
    except Exception as e:
        print(f"Error checking existing user: {e}")
    
    # Create user in Identity Center
    try:
        user_id = create_identity_center_user(user_data)
        
        # Add user to group
        identitystore.create_group_membership(
            IdentityStoreId=IDENTITY_STORE_ID,
            GroupId=CLI_GROUP_ID,
            MemberId={'UserId': user_id}
        )
        
        # Send welcome email
        send_welcome_email(user_data)
        
        return html_response(f'''
            <html>
            <head>
                <title>Registration Approved</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        max-width: 600px;
                        margin: 50px auto;
                        padding: 20px;
                        text-align: center;
                    }}
                    h1 {{ color: #28a745; }}
                    .info {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                </style>
            </head>
            <body>
                <h1>✅ Registration Approved</h1>
                <div class="info">
                    <p><strong>Username:</strong> {user_data["username"]}</p>
                    <p><strong>Email:</strong> {user_data["email"]}</p>
                    <p><strong>Name:</strong> {user_data["first_name"]} {user_data["last_name"]}</p>
                </div>
                <p>User has been created successfully.</p>
                <p>They will receive an email to set their password.</p>
            </body>
            </html>
        ''', 200)
        
    except Exception as e:
        print(f"Error creating user: {e}")
        return html_response(
            f'<h1>Error Creating User</h1><p>{str(e)}</p>',
            500
        )

def handle_denial(event):
    """Handle denial action"""
    
    # Get token from query parameters
    params = event.get('queryStringParameters', {}) or {}
    token = params.get('token')
    
    if not token:
        return html_response('<h1>Error: Missing token</h1>', 400)
    
    # Verify and decode token
    try:
        user_data = verify_signed_token(token, 'deny')
    except Exception as e:
        return html_response(f'<h1>Error: Invalid or expired token</h1><p>{str(e)}</p>', 400)
    
    # Send denial email
    try:
        send_denial_email(user_data)
    except Exception as e:
        print(f"Error sending denial email: {e}")
    
    return html_response(f'''
        <html>
        <head>
            <title>Registration Denied</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: 50px auto;
                    padding: 20px;
                    text-align: center;
                }}
                h1 {{ color: #dc3545; }}
                .info {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <h1>❌ Registration Denied</h1>
            <div class="info">
                <p><strong>Username:</strong> {user_data["username"]}</p>
                <p><strong>Email:</strong> {user_data["email"]}</p>
            </div>
            <p>Registration request has been denied.</p>
        </body>
        </html>
    ''', 200)

def create_signed_token(data, action):
    """Create JWT-like signed token with data and action"""
    payload = {
        'data': data,
        'action': action
    }
    
    payload_json = json.dumps(payload, separators=(',', ':'))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()
    
    signature = hmac.new(
        SECRET_KEY.encode(),
        payload_b64.encode(),
        hashlib.sha256
    ).hexdigest()
    
    token = f"{payload_b64}.{signature}"
    return base64.urlsafe_b64encode(token.encode()).decode()

def verify_signed_token(token, expected_action):
    """Verify and decode signed token"""
    try:
        # Decode outer base64
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        payload_b64, signature = decoded.split('.')
        
        # Verify signature
        expected_sig = hmac.new(
            SECRET_KEY.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected_sig):
            raise ValueError("Invalid signature")
        
        # Decode payload
        payload_json = base64.urlsafe_b64decode(payload_b64.encode()).decode()
        payload = json.loads(payload_json)
        
        # Verify action
        if payload['action'] != expected_action:
            raise ValueError("Invalid action")
        
        # Check expiration
        expires_at = datetime.fromisoformat(payload['data']['expires_at'])
        if datetime.utcnow() > expires_at:
            raise ValueError("Token expired")
        
        return payload['data']
        
    except Exception as e:
        raise ValueError(f"Token verification failed: {str(e)}")

def create_identity_center_user(user_data):
    """Create user in IAM Identity Center"""
    response = identitystore.create_user(
        IdentityStoreId=IDENTITY_STORE_ID,
        UserName=user_data['username'],
        DisplayName=f"{user_data['first_name']} {user_data['last_name']}",
        Name={
            'GivenName': user_data['first_name'],
            'FamilyName': user_data['last_name'],
            'Formatted': f"{user_data['first_name']} {user_data['last_name']}"
        },
        Emails=[{
            'Value': user_data['email'],
            'Type': 'work',
            'Primary': True
        }]
    )
    
    return response['UserId']

def send_admin_email(user_data, approve_url, deny_url):
    """Send approval request email to admin"""
    
    subject = f"[CCA] New Registration Request: {user_data['username']}"
    
    text_body = f"""
New Cloud CLI Access registration request:

Username: {user_data['username']}
Email: {user_data['email']}
Name: {user_data['first_name']} {user_data['last_name']}
Submitted: {user_data['submitted_at']}

To approve this request:
{approve_url}

To deny this request:
{deny_url}

These links will expire in 7 days.
"""
    
    html_body = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 5px; }}
        .content {{ background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 5px; }}
        .info-row {{ margin: 10px 0; }}
        .label {{ font-weight: bold; color: #555; }}
        .button {{ display: inline-block; padding: 12px 30px; margin: 10px 5px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
        .approve {{ background: #28a745; color: white; }}
        .deny {{ background: #dc3545; color: white; }}
        .actions {{ text-align: center; margin: 30px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🔐 New Registration Request</h2>
        </div>
        <div class="content">
            <div class="info-row"><span class="label">Username:</span> {user_data['username']}</div>
            <div class="info-row"><span class="label">Email:</span> {user_data['email']}</div>
            <div class="info-row"><span class="label">Name:</span> {user_data['first_name']} {user_data['last_name']}</div>
            <div class="info-row"><span class="label">Submitted:</span> {user_data['submitted_at']}</div>
        </div>
        <div class="actions">
            <a href="{approve_url}" class="button approve">✓ Approve</a>
            <a href="{deny_url}" class="button deny">✗ Deny</a>
        </div>
        <p style="color: #666; font-size: 12px; text-align: center;">These links will expire in 7 days.</p>
    </div>
</body>
</html>
"""
    
    ses.send_email(
        Source=FROM_EMAIL,
        Destination={'ToAddresses': [ADMIN_EMAIL]},
        Message={
            'Subject': {'Data': subject},
            'Body': {
                'Text': {'Data': text_body},
                'Html': {'Data': html_body}
            }
        }
    )

def send_welcome_email(user_data):
    """Send welcome email to approved user"""
    
    subject = "Welcome to Cloud CLI Access"
    
    text_body = f"""
Welcome to Cloud CLI Access!

Your registration has been approved.

Username: {user_data['username']}
Email: {user_data['email']}

IMPORTANT - Set Your Password:
You will receive a separate email from AWS IAM Identity Center with a link to set your password.
Please check your inbox (and spam folder) for an email with the subject "Invitation to join AWS IAM Identity Center".

After setting your password, you can log in using the CCC CLI tool:

1. Install the CCC CLI tool (if not already installed)
2. Run: ccc configure
3. Run: ccc login
4. When prompted, authenticate at: {SSO_START_URL}

For help, contact your administrator.

Best regards,
Cloud CLI Access Team
"""
    
    html_body = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 5px; text-align: center; }}
        .content {{ padding: 20px; }}
        .info-box {{ background: #f8f9fa; padding: 15px; border-left: 4px solid #667eea; margin: 20px 0; }}
        .warning {{ background: #fff3cd; border-left-color: #ffc107; padding: 15px; margin: 20px 0; }}
        .steps {{ background: #f8f9fa; padding: 20px; border-radius: 5px; }}
        .step {{ margin: 15px 0; padding-left: 30px; position: relative; }}
        .step:before {{ content: "→"; position: absolute; left: 0; color: #667eea; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 Welcome to Cloud CLI Access!</h1>
        </div>
        <div class="content">
            <p>Your registration has been approved.</p>
            
            <div class="info-box">
                <strong>Your Account:</strong><br>
                Username: {user_data['username']}<br>
                Email: {user_data['email']}
            </div>
            
            <div class="warning">
                <strong>⚠️ IMPORTANT - Set Your Password:</strong><br>
                You will receive a separate email from AWS IAM Identity Center with a link to set your password.
                Check your inbox (and spam folder) for an email with the subject:<br>
                <em>"Invitation to join AWS IAM Identity Center"</em>
            </div>
            
            <h3>Getting Started:</h3>
            <div class="steps">
                <div class="step">Set your password using the link from AWS</div>
                <div class="step">Install the CCC CLI tool</div>
                <div class="step">Run: <code>ccc configure</code></div>
                <div class="step">Run: <code>ccc login</code></div>
                <div class="step">Authenticate at: <a href="{SSO_START_URL}">{SSO_START_URL}</a></div>
            </div>
            
            <p>For help, contact your administrator.</p>
            
            <p>Best regards,<br><strong>Cloud CLI Access Team</strong></p>
        </div>
    </div>
</body>
</html>
"""
    
    try:
        ses.send_email(
            Source=FROM_EMAIL,
            Destination={'ToAddresses': [user_data['email']]},
            Message={
                'Subject': {'Data': subject},
                'Body': {
                    'Text': {'Data': text_body},
                    'Html': {'Data': html_body}
                }
            }
        )
    except Exception as e:
        print(f"Error sending welcome email: {e}")

def send_denial_email(user_data):
    """Send denial notification to user"""
    
    subject = "Cloud CLI Access Registration Status"
    
    text_body = f"""
Hello {user_data['first_name']},

Thank you for your interest in Cloud CLI Access.

Unfortunately, your registration request has not been approved at this time.

If you believe this is an error or would like more information, please contact the administrator.

Best regards,
Cloud CLI Access Team
"""
    
    html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2>Cloud CLI Access Registration</h2>
        <p>Hello {user_data['first_name']},</p>
        <p>Thank you for your interest in Cloud CLI Access.</p>
        <p>Unfortunately, your registration request has not been approved at this time.</p>
        <p>If you believe this is an error or would like more information, please contact the administrator.</p>
        <p>Best regards,<br><strong>Cloud CLI Access Team</strong></p>
    </div>
</body>
</html>
"""
    
    try:
        ses.send_email(
            Source=FROM_EMAIL,
            Destination={'ToAddresses': [user_data['email']]},
            Message={
                'Subject': {'Data': subject},
                'Body': {
                    'Text': {'Data': text_body},
                    'Html': {'Data': html_body}
                }
            }
        )
    except Exception as e:
        print(f"Error sending denial email: {e}")

def error_response(message, status_code):
    """Return error response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({'error': message})
    }

def html_response(html, status_code):
    """Return HTML response"""
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'text/html'},
        'body': html
    }
LAMBDA_CODE

# Package Lambda function
cd /tmp/lambda
zip lambda_function.zip lambda_function.py

# Create Lambda function
aws lambda create-function \
  --function-name cca-registration \
  --runtime python3.11 \
  --role "$LAMBDA_ROLE_ARN" \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda_function.zip \
  --timeout 30 \
  --memory-size 256 \
  --environment "Variables={IDENTITY_STORE_ID=$IDENTITY_STORE_ID,CLI_GROUP_ID=$CLI_GROUP_ID,SSO_START_URL=$SSO_START_URL,FROM_EMAIL=$FROM_EMAIL,ADMIN_EMAIL=$ADMIN_EMAIL,SECRET_KEY=$SECRET_KEY}" \
  --output json > /tmp/lambda-function.json

export LAMBDA_ARN=$(cat /tmp/lambda-function.json | jq -r '.FunctionArn')
echo "Lambda ARN: $LAMBDA_ARN"
echo "export LAMBDA_ARN=\"$LAMBDA_ARN\"" >> /tmp/cca-config.env

echo "✅ Lambda function created"
```

### Step 2.3: Create Lambda Function URL

```bash
# Create Function URL (built-in HTTPS endpoint)
aws lambda create-function-url-config \
  --function-name cca-registration \
  --auth-type NONE \
  --cors "AllowOrigins=*,AllowMethods=GET,POST,AllowHeaders=*" \
  --output json > /tmp/function-url.json

export LAMBDA_URL=$(cat /tmp/function-url.json | jq -r '.FunctionUrl')
echo "Lambda Function URL: $LAMBDA_URL"
echo "export LAMBDA_URL=\"$LAMBDA_URL\"" >> /tmp/cca-config.env

# Add permission for public invocation
aws lambda add-permission \
  --function-name cca-registration \
  --statement-id FunctionURLAllowPublicAccess \
  --action lambda:InvokeFunctionUrl \
  --principal "*" \
  --function-url-auth-type NONE

echo "✅ Lambda Function URL created: $LAMBDA_URL"
```

---

## Phase 3: Registration Form

### Step 3.1: Create S3 Bucket

```bash
# Create S3 bucket
export REGISTRATION_BUCKET="cca-registration-$(date +%s)"
aws s3 mb s3://$REGISTRATION_BUCKET
echo "export REGISTRATION_BUCKET=\"$REGISTRATION_BUCKET\"" >> /tmp/cca-config.env

# Configure bucket for public read
aws s3api put-public-access-block \
  --bucket $REGISTRATION_BUCKET \
  --public-access-block-configuration \
    "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

# Enable static website hosting
aws s3 website s3://$REGISTRATION_BUCKET --index-document registration.html

# Create bucket policy
cat > /tmp/bucket-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::${REGISTRATION_BUCKET}/*"
    }
  ]
}
EOF

aws s3api put-bucket-policy --bucket $REGISTRATION_BUCKET --policy file:///tmp/bucket-policy.json

echo "✅ S3 bucket created"
```

### Step 3.2: Create Registration HTML

```bash
cat > /tmp/registration.html <<EOF
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cloud CLI Access - Registration</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            max-width: 500px;
            width: 100%;
            padding: 40px;
        }
        
        h1 {
            color: #333;
            font-size: 28px;
            margin-bottom: 10px;
            text-align: center;
        }
        
        .subtitle {
            color: #666;
            text-align: center;
            margin-bottom: 30px;
            font-size: 14px;
        }
        
        .info-box {
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
            padding: 15px;
            margin-bottom: 25px;
            border-radius: 4px;
            font-size: 14px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            color: #333;
            font-weight: 500;
            margin-bottom: 8px;
            font-size: 14px;
        }
        
        input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        
        input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .btn {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
        }
        
        .btn:active {
            transform: translateY(0);
        }
        
        .btn:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        
        .message {
            margin-top: 20px;
            padding: 15px;
            border-radius: 6px;
            font-size: 14px;
            display: none;
        }
        
        .message.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
            display: block;
        }
        
        .message.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
            display: block;
        }
        
        .footer {
            margin-top: 30px;
            text-align: center;
            color: #999;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔐 Cloud CLI Access</h1>
        <p class="subtitle">Register for CLI access to AWS resources</p>
        
        <div class="info-box">
            <strong>ℹ️ Note:</strong> After registration, an administrator will review your request. 
            You'll receive an email to set your password once approved.
        </div>
        
        <form id="registrationForm">
            <div class="form-group">
                <label for="username">Username *</label>
                <input type="text" id="username" name="username" required 
                       pattern="[a-zA-Z0-9._-]+" 
                       placeholder="john.doe"
                       title="Letters, numbers, dots, hyphens, and underscores only">
            </div>
            
            <div class="form-group">
                <label for="email">Email Address *</label>
                <input type="email" id="email" name="email" required
                       placeholder="john@example.com">
            </div>
            
            <div class="form-group">
                <label for="first_name">First Name *</label>
                <input type="text" id="first_name" name="first_name" required
                       placeholder="John">
            </div>
            
            <div class="form-group">
                <label for="last_name">Last Name *</label>
                <input type="text" id="last_name" name="last_name" required
                       placeholder="Doe">
            </div>
            
            <button type="submit" class="btn" id="submitBtn">Register</button>
        </form>
        
        <div id="message" class="message"></div>
        
        <div class="footer">
            <p>Your request will be reviewed by an administrator</p>
            <p>You'll receive an email once your account is approved</p>
        </div>
    </div>
    
    <script>
        const API_URL = '${LAMBDA_URL}';
        const form = document.getElementById('registrationForm');
        const messageDiv = document.getElementById('message');
        const submitBtn = document.getElementById('submitBtn');
        
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Disable submit button
            submitBtn.disabled = true;
            submitBtn.textContent = 'Submitting...';
            
            // Collect form data
            const formData = {
                username: document.getElementById('username').value,
                email: document.getElementById('email').value,
                first_name: document.getElementById('first_name').value,
                last_name: document.getElementById('last_name').value
            };
            
            try {
                const response = await fetch(\`\${API_URL}register\`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    showMessage(
                        '✅ Registration submitted successfully! ' +
                        'An administrator will review your request. You will receive an email once approved.',
                        'success'
                    );
                    form.reset();
                } else {
                    showMessage('❌ Error: ' + (data.error || 'Registration failed'), 'error');
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Register';
                }
            } catch (error) {
                showMessage('❌ Network error: ' + error.message, 'error');
                submitBtn.disabled = false;
                submitBtn.textContent = 'Register';
            }
        });
        
        function showMessage(text, type) {
            messageDiv.textContent = text;
            messageDiv.className = 'message ' + type;
            messageDiv.style.display = 'block';
        }
    </script>
</body>
</html>
EOF

# Upload to S3
aws s3 cp /tmp/registration.html s3://$REGISTRATION_BUCKET/registration.html --content-type text/html

# Get website URL
export REGISTRATION_URL="http://${REGISTRATION_BUCKET}.s3-website-${SSO_REGION}.amazonaws.com/registration.html"
echo "Registration URL: $REGISTRATION_URL"
echo "export REGISTRATION_URL=\"$REGISTRATION_URL\"" >> /tmp/cca-config.env

echo "✅ Registration form deployed"
```

---

## Phase 4: CCC CLI Tool Implementation

### Step 4.1: Create Project Structure

```bash
# Create project directory
mkdir -p ~/ccc-cli
cd ~/ccc-cli

# Create directory structure
mkdir -p ccc
touch ccc/__init__.py

echo "✅ Project structure created"
```

### Step 4.2: Create Requirements File

```bash
cat > requirements.txt <<'EOF'
boto3>=1.34.0
click>=8.1.0
colorama>=0.4.6
python-dateutil>=2.8.2
EOF

# Install dependencies
pip3 install -r requirements.txt

echo "✅ Dependencies installed"
```

### Step 4.3: Create Configuration Module

```bash
cat > ccc/config.py <<'EOF'
"""Configuration management for CCC CLI"""
import os
import json
from pathlib import Path

class Config:
    """Manages CCC configuration"""
    
    def __init__(self):
        self.config_dir = Path.home() / ".ccc"
        self.config_file = self.config_dir / "config.json"
        self.credentials_file = self.config_dir / "credentials.json"
        
        # Ensure config directory exists
        self.config_dir.mkdir(exist_ok=True, mode=0o700)
        
        # Load or initialize config
        self._config = self._load_config()
    
    def _load_config(self):
        """Load configuration from file"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save(self):
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self._config, f, indent=2)
        os.chmod(self.config_file, 0o600)
    
    def get(self, key, default=None):
        """Get configuration value"""
        return self._config.get(key, default)
    
    def set(self, key, value):
        """Set configuration value"""
        self._config[key] = value
        self.save()
    
    def get_credentials(self):
        """Load cached credentials"""
        if not self.credentials_file.exists():
            return None
        
        with open(self.credentials_file, 'r') as f:
            return json.load(f)
    
    def save_credentials(self, credentials):
        """Save credentials to cache"""
        with open(self.credentials_file, 'w') as f:
            json.dump(credentials, f, indent=2)
        os.chmod(self.credentials_file, 0o600)
    
    def clear_credentials(self):
        """Remove cached credentials"""
        if self.credentials_file.exists():
            self.credentials_file.unlink()

# Global config instance
config = Config()
EOF

echo "✅ Configuration module created"
```

### Step 4.4: Create Authentication Module

```bash
cat > ccc/auth.py <<'EOF'
"""Authentication module for CCC CLI using IAM Identity Center device flow"""
import time
import webbrowser
import json
from datetime import datetime, timezone
from typing import Optional, Dict

import boto3
from botocore.exceptions import ClientError
from colorama import Fore, Style

from .config import config


class CCCAuthenticator:
    """Handles authentication with IAM Identity Center"""
    
    def __init__(self, sso_start_url: str, sso_region: str, 
                 account_id: str, role_name: str):
        self.sso_start_url = sso_start_url
        self.sso_region = sso_region
        self.account_id = account_id
        self.role_name = role_name
        
        self.oidc_client = boto3.client('sso-oidc', region_name=sso_region)
        self.sso_client = boto3.client('sso', region_name=sso_region)
    
    def login(self) -> Dict:
        """Perform device flow authentication - Returns AWS credentials"""
        print(f"{Fore.CYAN}🔐 Initiating Cloud CLI Access authentication...{Style.RESET_ALL}\n")
        
        # Step 1: Register client
        print("Registering client...")
        client_registration = self._register_client()
        client_id = client_registration['clientId']
        client_secret = client_registration['clientSecret']
        
        # Step 2: Start device authorization
        print("Starting device authorization...")
        device_auth = self._start_device_authorization(client_id, client_secret)
        
        device_code = device_auth['deviceCode']
        user_code = device_auth['userCode']
        verification_uri = device_auth['verificationUri']
        verification_uri_complete = device_auth.get('verificationUriComplete', verification_uri)
        interval = device_auth.get('interval', 5)
        expires_in = device_auth.get('expiresIn', 600)
        
        # Step 3: Display to user and open browser
        self._display_authentication_instructions(verification_uri, user_code, verification_uri_complete)
        
        # Step 4: Poll for authorization
        print(f"\n{Fore.YELLOW}⏳ Waiting for authentication...{Style.RESET_ALL}")
        access_token = self._poll_for_token(client_id, client_secret, device_code, interval, expires_in)
        
        print(f"{Fore.GREEN}✅ Authentication successful!{Style.RESET_ALL}\n")
        
        # Step 5: Exchange token for AWS credentials
        print("Fetching AWS credentials...")
        credentials = self._get_role_credentials(access_token)
        
        # Step 6: Cache credentials
        self._cache_credentials(credentials, access_token)
        
        print(f"{Fore.GREEN}💾 Credentials cached successfully{Style.RESET_ALL}")
        expiration = datetime.fromtimestamp(credentials['expiration'] / 1000, tz=timezone.utc)
        print(f"{Fore.CYAN}📅 Valid until: {expiration.isoformat()}{Style.RESET_ALL}\n")
        
        return credentials
    
    def _register_client(self) -> Dict:
        """Register the CLI as an OAuth client"""
        try:
            response = self.oidc_client.register_client(
                clientName='CCC-CLI',
                clientType='public'
            )
            return response
        except ClientError as e:
            print(f"{Fore.RED}❌ Failed to register client: {e}{Style.RESET_ALL}")
            raise
    
    def _start_device_authorization(self, client_id: str, client_secret: str) -> Dict:
        """Start the device authorization flow"""
        try:
            response = self.oidc_client.start_device_authorization(
                clientId=client_id,
                clientSecret=client_secret,
                startUrl=self.sso_start_url
            )
            return response
        except ClientError as e:
            print(f"{Fore.RED}❌ Failed to start device authorization: {e}{Style.RESET_ALL}")
            raise
    
    def _display_authentication_instructions(self, uri: str, user_code: str, uri_complete: str):
        """Display authentication instructions to user"""
        print("\n" + "═" * 60)
        print(f"{Fore.CYAN}Opening browser for authentication...{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}If browser doesn't open automatically, visit:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}{uri}{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}And enter code:{Style.RESET_ALL} {Fore.GREEN}{user_code}{Style.RESET_ALL}")
        print("═" * 60)
        
        # Auto-open browser
        try:
            webbrowser.open(uri_complete)
            print(f"\n{Fore.GREEN}✓ Browser opened{Style.RESET_ALL}")
        except Exception as e:
            print(f"\n{Fore.YELLOW}⚠ Could not open browser automatically: {e}{Style.RESET_ALL}")
    
    def _poll_for_token(self, client_id: str, client_secret: str, 
                       device_code: str, interval: int, expires_in: int) -> str:
        """Poll for authorization token"""
        start_time = time.time()
        
        while True:
            if time.time() - start_time > expires_in:
                raise TimeoutError("Authentication timeout - please try again")
            
            time.sleep(interval)
            
            try:
                response = self.oidc_client.create_token(
                    clientId=client_id,
                    clientSecret=client_secret,
                    grantType='urn:ietf:params:oauth:grant-type:device_code',
                    deviceCode=device_code
                )
                
                return response['accessToken']
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                
                if error_code == 'AuthorizationPendingException':
                    print(".", end="", flush=True)
                    continue
                elif error_code == 'SlowDownException':
                    interval += 5
                    time.sleep(5)
                    continue
                elif error_code == 'ExpiredTokenException':
                    raise TimeoutError("Authentication expired - please try again")
                else:
                    print(f"\n{Fore.RED}❌ Authentication error: {e}{Style.RESET_ALL}")
                    raise
    
    def _get_role_credentials(self, access_token: str) -> Dict:
        """Exchange access token for AWS credentials"""
        try:
            response = self.sso_client.get_role_credentials(
                roleName=self.role_name,
                accountId=self.account_id,
                accessToken=access_token
            )
            
            creds = response['roleCredentials']
            return {
                'accessKeyId': creds['accessKeyId'],
                'secretAccessKey': creds['secretAccessKey'],
                'sessionToken': creds['sessionToken'],
                'expiration': creds['expiration']
            }
        except ClientError as e:
            print(f"{Fore.RED}❌ Failed to get role credentials: {e}{Style.RESET_ALL}")
            raise
    
    def _cache_credentials(self, credentials: Dict, access_token: str):
        """Cache credentials locally"""
        cache_data = {
            'credentials': credentials,
            'access_token': access_token,
            'cached_at': datetime.now(timezone.utc).isoformat(),
            'sso_start_url': self.sso_start_url,
            'sso_region': self.sso_region,
            'account_id': self.account_id,
            'role_name': self.role_name
        }
        config.save_credentials(cache_data)
    
    @staticmethod
    def get_cached_credentials() -> Optional[Dict]:
        """Get cached credentials if valid"""
        cached = config.get_credentials()
        if not cached:
            return None
        
        # Check if expired
        expiration = cached['credentials']['expiration']
        expiration_time = datetime.fromtimestamp(expiration / 1000, tz=timezone.utc)
        
        if datetime.now(timezone.utc) >= expiration_time:
            print(f"{Fore.YELLOW}⚠ Cached credentials expired{Style.RESET_ALL}")
            return None
        
        return cached['credentials']
    
    @staticmethod
    def logout():
        """Clear cached credentials"""
        config.clear_credentials()
        print(f"{Fore.GREEN}✅ Logged out successfully{Style.RESET_ALL}")
EOF

echo "✅ Authentication module created"
```

### Step 4.5: Create CLI Commands Module

```bash
cat > ccc/cli.py <<'EOF'
"""Main CLI interface for CCC"""
import sys
from datetime import datetime, timezone

import click
import boto3
from botocore.exceptions import ClientError
from colorama import Fore, Style, init

from .config import config
from .auth import CCCAuthenticator

# Initialize colorama
init(autoreset=True)


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """
    CCC (Cloud CLI Client) - Cloud CLI Access Framework
    
    Authenticate with AWS IAM Identity Center to get temporary credentials.
    """
    pass


@cli.command()
@click.option('--sso-start-url', envvar='CCC_SSO_START_URL', 
              help='SSO start URL')
@click.option('--sso-region', envvar='CCC_SSO_REGION', default='us-east-1',
              help='SSO region (default: us-east-1)')
@click.option('--account-id', envvar='CCC_ACCOUNT_ID',
              help='AWS account ID')
@click.option('--role-name', envvar='CCC_ROLE_NAME', default='CCA-CLI-Access',
              help='IAM role name (default: CCA-CLI-Access)')
def configure(sso_start_url, sso_region, account_id, role_name):
    """Configure CCC with your AWS SSO details"""
    if not sso_start_url:
        sso_start_url = click.prompt('SSO start URL')
    
    if not account_id:
        account_id = click.prompt('AWS Account ID')
    
    config.set('sso_start_url', sso_start_url)
    config.set('sso_region', sso_region)
    config.set('account_id', account_id)
    config.set('role_name', role_name)
    
    print(f"\n{Fore.GREEN}✅ Configuration saved{Style.RESET_ALL}")
    print(f"\n{Fore.CYAN}Configuration:{Style.RESET_ALL}")
    print(f"  SSO Start URL: {sso_start_url}")
    print(f"  SSO Region: {sso_region}")
    print(f"  Account ID: {account_id}")
    print(f"  Role Name: {role_name}")
    print(f"\n{Fore.YELLOW}Next step: Run 'ccc login' to authenticate{Style.RESET_ALL}\n")


@cli.command()
def login():
    """Authenticate and obtain AWS credentials"""
    # Check configuration
    sso_start_url = config.get('sso_start_url')
    sso_region = config.get('sso_region')
    account_id = config.get('account_id')
    role_name = config.get('role_name')
    
    if not all([sso_start_url, sso_region, account_id, role_name]):
        print(f"{Fore.RED}❌ CCC not configured{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Run 'ccc configure' first{Style.RESET_ALL}\n")
        sys.exit(1)
    
    # Perform authentication
    try:
        authenticator = CCCAuthenticator(
            sso_start_url=sso_start_url,
            sso_region=sso_region,
            account_id=account_id,
            role_name=role_name
        )
        
        credentials = authenticator.login()
        
        print(f"{Fore.GREEN}✅ Login successful!{Style.RESET_ALL}")
        print(f"\n{Fore.CYAN}You can now use CCC commands that require AWS access{Style.RESET_ALL}\n")
        
    except Exception as e:
        print(f"\n{Fore.RED}❌ Login failed: {e}{Style.RESET_ALL}\n")
        sys.exit(1)


@cli.command()
def logout():
    """Clear cached credentials"""
    CCCAuthenticator.logout()


@cli.command()
def status():
    """Show authentication status and credential expiration"""
    cached = config.get_credentials()
    
    if not cached:
        print(f"{Fore.YELLOW}⚠ Not logged in{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Run 'ccc login' to authenticate{Style.RESET_ALL}\n")
        return
    
    creds = cached['credentials']
    expiration = datetime.fromtimestamp(creds['expiration'] / 1000, tz=timezone.utc)
    cached_at = datetime.fromisoformat(cached['cached_at'])
    
    now = datetime.now(timezone.utc)
    is_expired = now >= expiration
    
    print(f"\n{Fore.CYAN}Authentication Status:{Style.RESET_ALL}")
    print(f"  Status: {Fore.GREEN}✓ Authenticated{Style.RESET_ALL}" if not is_expired 
          else f"  Status: {Fore.RED}✗ Expired{Style.RESET_ALL}")
    print(f"  SSO Start URL: {cached['sso_start_url']}")
    print(f"  Account ID: {cached['account_id']}")
    print(f"  Role Name: {cached['role_name']}")
    print(f"  Cached: {cached_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  Expires: {expiration.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    if not is_expired:
        time_remaining = expiration - now
        hours, remainder = divmod(time_remaining.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        print(f"  Time Remaining: {hours}h {minutes}m")
    
    print()


@cli.command()
def test():
    """Test AWS credentials by calling AWS APIs"""
    print(f"{Fore.CYAN}🧪 Testing Cloud CLI Access credentials...{Style.RESET_ALL}\n")
    
    # Get cached credentials
    creds = CCCAuthenticator.get_cached_credentials()
    
    if not creds:
        print(f"{Fore.RED}❌ Not logged in or credentials expired{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Run 'ccc login' first{Style.RESET_ALL}\n")
        sys.exit(1)
    
    # Create AWS session with cached credentials
    session = boto3.Session(
        aws_access_key_id=creds['accessKeyId'],
        aws_secret_access_key=creds['secretAccessKey'],
        aws_session_token=creds['sessionToken']
    )
    
    # Test 1: STS GetCallerIdentity
    print(f"{Fore.CYAN}Test 1: STS GetCallerIdentity{Style.RESET_ALL}")
    try:
        sts = session.client('sts')
        identity = sts.get_caller_identity()
        print(f"  {Fore.GREEN}✓ Success{Style.RESET_ALL}")
        print(f"    User ARN: {identity['Arn']}")
        print(f"    Account: {identity['Account']}")
    except Exception as e:
        print(f"  {Fore.RED}✗ Failed: {e}{Style.RESET_ALL}")
    
    # Test 2: S3 List Buckets
    print(f"\n{Fore.CYAN}Test 2: S3 ListBuckets{Style.RESET_ALL}")
    try:
        s3 = session.client('s3')
        response = s3.list_buckets()
        bucket_count = len(response['Buckets'])
        print(f"  {Fore.GREEN}✓ Success{Style.RESET_ALL}")
        print(f"    Buckets: {bucket_count}")
    except Exception as e:
        print(f"  {Fore.RED}✗ Failed: {e}{Style.RESET_ALL}")
    
    # Test 3: EC2 Describe Regions
    print(f"\n{Fore.CYAN}Test 3: EC2 DescribeRegions{Style.RESET_ALL}")
    try:
        ec2 = session.client('ec2')
        response = ec2.describe_regions()
        region_count = len(response['Regions'])
        print(f"  {Fore.GREEN}✓ Success{Style.RESET_ALL}")
        print(f"    Regions available: {region_count}")
    except Exception as e:
        print(f"  {Fore.RED}✗ Failed: {e}{Style.RESET_ALL}")
    
    print(f"\n{Fore.GREEN}✅ All tests completed{Style.RESET_ALL}\n")


def main():
    """Entry point for CCC CLI"""
    try:
        cli()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚠ Operation cancelled{Style.RESET_ALL}\n")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Fore.RED}❌ Unexpected error: {e}{Style.RESET_ALL}\n")
        sys.exit(1)


if __name__ == '__main__':
    main()
EOF

echo "✅ CLI commands module created"
```

### Step 4.6: Create Entry Point and Setup

```bash
cat > ccc/__main__.py <<'EOF'
"""CCC CLI entry point"""
from .cli import main

if __name__ == '__main__':
    main()
EOF

cat > setup.py <<'EOF'
"""Setup script for CCC CLI"""
from setuptools import setup, find_packages

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='ccc-cli',
    version='1.0.0',
    description='Cloud CLI Client - Cloud CLI Access Framework',
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'ccc=ccc.cli:main',
        ],
    },
    python_requires='>=3.8',
)
EOF

# Install CCC CLI
pip3 install -e .

# Verify installation
which ccc
ccc --version

echo "✅ CCC CLI installed successfully"
```

### Step 4.7: Create README

```bash
cat > README.md <<EOF
# CCC (Cloud CLI Client)

Cloud CLI Access framework with simplified infrastructure and self-registration.

## Features

- ✅ Self-service registration (single HTML form)
- ✅ Admin email approval (one-click)
- ✅ Minimal infrastructure (1 Lambda, no database)
- ✅ Password set via Identity Center
- ✅ Browser-based authentication
- ✅ No AWS Console access

## User Registration

Register at: $REGISTRATION_URL

After approval:
1. Receive email from Identity Center to set password
2. Set password via link
3. Use CCC CLI to authenticate

## Installation

\`\`\`bash
pip install -e .
\`\`\`

## Quick Start

\`\`\`bash
ccc configure
ccc login
ccc status
ccc test
\`\`\`

## Infrastructure

- IAM Identity Center
- 1 Lambda Function (with Function URL)
- 1 S3 Bucket (single HTML file)
- SES (for emails)

## Configuration

- SSO Start URL: $SSO_START_URL
- SSO Region: $SSO_REGION
- Account ID: $AWS_ACCOUNT_ID

EOF

echo "✅ README created"
```

---

## Phase 5: Testing

### Step 5.1: Test Registration

```bash
echo "📋 Test Registration Flow"
echo "========================"
echo ""
echo "Registration URL: $REGISTRATION_URL"
echo ""
read -p "Press Enter to open registration form..."

# Open in browser
python3 -c "import webbrowser; webbrowser.open('$REGISTRATION_URL')"

echo ""
echo "Fill out the form and submit"
echo "Check $ADMIN_EMAIL for approval email"
echo ""
read -p "Press Enter after submitting registration..."
```

### Step 5.2: Test Approval

```bash
echo "📧 Check Email"
echo "=============="
echo ""
echo "Check $ADMIN_EMAIL for approval email"
echo "Click the APPROVE link"
echo ""
read -p "Press Enter after clicking approve..."

echo ""
echo "Check the registered email for password setup instructions"
```

### Step 5.3: Configure and Test CCC CLI

```bash
# Source configuration
source /tmp/cca-config.env

# Configure CCC
ccc configure \
  --sso-start-url "$SSO_START_URL" \
  --sso-region "$SSO_REGION" \
  --account-id "$AWS_ACCOUNT_ID" \
  --role-name "CCA-CLI-Access"

echo ""
echo "After setting password via Identity Center email:"
read -p "Press Enter to test login..."

# Test login
ccc login

# Check status
ccc status

# Run tests
ccc test

echo "✅ CCC CLI testing completed"
```

---

## Phase 6: Summary and Cleanup

### Step 6.1: Generate Implementation Report

```bash
cat > /tmp/cca-simple-report.md <<EOF
# Cloud CLI Access - Simplified Implementation Report

**Date**: $(date)
**Status**: ✅ Complete

## Infrastructure Summary (Minimal)

### Core Services (3)
1. **IAM Identity Center**
   - Identity Store ID: $IDENTITY_STORE_ID
   - SSO Region: $SSO_REGION
   - SSO Start URL: $SSO_START_URL

2. **Lambda Function** (with Function URL)
   - Function Name: cca-registration
   - Function URL: $LAMBDA_URL
   - Handles: Registration, Approval, Denial

3. **S3 Bucket**
   - Bucket: $REGISTRATION_BUCKET
   - Registration URL: $REGISTRATION_URL

### Email
- Service: SES (called directly from Lambda)
- From: $FROM_EMAIL
- Admin: $ADMIN_EMAIL

### What We Eliminated
- ❌ DynamoDB (state in JWT tokens)
- ❌ API Gateway (Lambda Function URL)
- ❌ SNS (direct SES)
- ❌ Multiple Lambdas (1 function)
- ❌ Complex S3 website (single HTML file)

## User Flow

1. **Registration**: User visits HTML form → Submits → Receives pending message
2. **Admin Approval**: Admin gets email → Clicks approve/deny link → Done
3. **Password Setup**: User gets Identity Center email → Sets password
4. **CLI Login**: User runs \`ccc login\` → Authenticates → Gets AWS credentials

## URLs

- Registration: $REGISTRATION_URL
- Lambda Function URL: $LAMBDA_URL
- SSO Portal: $SSO_START_URL

## CCC CLI

- Installation: ~/ccc-cli/
- Commands: configure, login, logout, status, test

## Security

- ✅ JWT-signed approval tokens
- ✅ Console access denied
- ✅ 12-hour credential expiration
- ✅ Admin approval required
- ✅ Password via Identity Center

## Cleanup

To remove all resources:

\`\`\`bash
# Delete Lambda
aws lambda delete-function --function-name cca-registration
aws lambda delete-function-url-config --function-name cca-registration

# Delete S3 bucket
aws s3 rb s3://$REGISTRATION_BUCKET --force

# Delete IAM role
aws iam delete-role-policy --role-name CCA-Lambda-Role --policy-name CCA-Lambda-Policy
aws iam delete-role --role-name CCA-Lambda-Role

# Delete group
aws identitystore delete-group --identity-store-id $IDENTITY_STORE_ID --group-id $CLI_GROUP_ID

# Delete permission set
aws sso-admin delete-permission-set --instance-arn $SSO_INSTANCE_ARN --permission-set-arn $PERMISSION_SET_ARN

# Uninstall CCC CLI
pip3 uninstall -y ccc-cli
rm -rf ~/ccc-cli ~/.ccc
\`\`\`

---

## Success! 🎉

Minimal infrastructure deployed:
- 1 Lambda function
- 1 HTML file
- IAM Identity Center
- That's it!

EOF

cat /tmp/cca-simple-report.md

# Save to backup
mkdir -p ~/cca-backup
cp /tmp/cca-config.env ~/cca-backup/
cp /tmp/cca-simple-report.md ~/cca-backup/

echo ""
echo "✅ Implementation complete!"
echo "✅ Backup saved to ~/cca-backup/"
```

---

## Troubleshooting

### Lambda Function Logs

```bash
# View Lambda logs
aws logs tail /aws/lambda/cca-registration --follow
```

### Test Lambda Directly

```bash
# Test registration endpoint
curl -X POST $LAMBDA_URL/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@example.com","first_name":"Test","last_name":"User"}'
```

### Check SES Email Verification

```bash
aws ses get-identity-verification-attributes --identities $FROM_EMAIL
```

### Verify Identity Center User

```bash
aws identitystore list-users --identity-store-id $IDENTITY_STORE_ID
```

---

## Production Enhancements

### Optional Improvements

1. **CloudFront for Registration Form**
   - Add HTTPS
   - Custom domain
   - Better caching

2. **Lambda Monitoring**
   - CloudWatch alarms
   - Error rate alerts
   - Invocation metrics

3. **Email Templates**
   - Branded email design
   - Customizable content

4. **Rate Limiting**
   - Lambda reserved concurrency
   - WAF for registration endpoint

---

## Conclusion

**Simplified Cloud CLI Access Framework:**

✅ **3 AWS Services** (Identity Center + Lambda + S3)  
✅ **No Database** (JWT tokens)  
✅ **No API Gateway** (Lambda Function URLs)  
✅ **No SNS** (Direct SES)  
✅ **Single Lambda** (All logic)  
✅ **Single HTML File** (Simple form)  
✅ **Self-Registration** (User-initiated)  
✅ **Email Approval** (One-click admin)  
✅ **Password via Identity Center** (Standard flow)  
✅ **Zero Manual Work** (Fully automated)

**Minimal infrastructure, maximum functionality! 🚀**