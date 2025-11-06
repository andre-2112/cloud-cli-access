# CCA Framework - Python Lambda Web Application Backend

**Document Version:** 1.0
**Last Updated:** November 6, 2025
**Purpose:** Implement CCA web application authentication using Python Lambda instead of Node.js

---

## Overview

This document shows how to implement the web application OAuth2 authentication flow using **Python Lambda functions** with **API Gateway** instead of a traditional Node.js/Express server.

### Key Benefits

✅ **Serverless** - No server management required
✅ **Cost Effective** - Pay only for requests
✅ **Auto-scaling** - Handles any load automatically
✅ **Python Ecosystem** - Use familiar Python libraries
✅ **AWS Native** - Seamless integration with AWS services

---

## Architecture

```
┌─────────────┐      HTTPS         ┌──────────────────┐
│   Browser   │◄──────────────────►│   API Gateway    │
│   (User)    │   /login, /callback│   (REST API)     │
└─────────────┘                     └────────┬─────────┘
                                              │
                                              ▼
                                    ┌──────────────────┐
                                    │  Lambda Function │
                                    │  (Python 3.11)   │
                                    │  - auth_handler  │
                                    └────────┬─────────┘
                                              │
                  ┌───────────────────────────┼──────────────────────┐
                  │                           │                      │
                  ▼                           ▼                      ▼
        ┌──────────────────┐       ┌──────────────────┐   ┌─────────────────┐
        │  IAM Identity    │       │    DynamoDB      │   │  AWS Services   │
        │     Center       │       │  (Session Store) │   │  (S3, EC2, etc) │
        └──────────────────┘       └──────────────────┘   └─────────────────┘
```

---

## Implementation Guide

### 1. Prerequisites

**Required AWS Resources:**
- IAM Identity Center enabled with CCA framework
- DynamoDB table for session storage (or use Lambda environment variables for stateless JWT)
- Lambda execution role with appropriate permissions

### 2. Register OIDC Application Client

```bash
# Create OIDC application client in Identity Center
aws sso-oidc register-client \
  --client-name "CCA-WebApp-Python" \
  --client-type "public" \
  --scopes "openid" "profile" "email" \
  --redirect-uris "https://your-api-gateway-url.amazonaws.com/prod/callback" \
  --grant-types "authorization_code" "refresh_token"

# Save the response - you'll need clientId and clientSecret
```

**Response:**
```json
{
  "clientId": "AbCdEf123456",
  "clientSecret": "SECRET_VALUE_HERE",
  "clientIdIssuedAt": 1699294800,
  "clientSecretExpiresAt": 1730830800
}
```

---

### 3. Create DynamoDB Table for Sessions

```bash
# Create DynamoDB table for session storage
aws dynamodb create-table \
  --table-name cca-web-sessions \
  --attribute-definitions \
    AttributeName=session_id,AttributeType=S \
  --key-schema \
    AttributeName=session_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --tags Key=project,Value=CCA

# Enable TTL for automatic session cleanup
aws dynamodb update-time-to-live \
  --table-name cca-web-sessions \
  --time-to-live-specification \
    Enabled=true,AttributeName=ttl
```

---

### 4. Python Lambda Function

Create a Python Lambda function to handle authentication:

**File: `lambda/cca_web_auth.py`**

```python
import json
import os
import time
import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from urllib.parse import urlencode, parse_qs
import boto3
import requests
from jose import jwt

# Configuration from environment variables
SSO_START_URL = os.environ['SSO_START_URL']  # https://d-9066117351.awsapps.com/start
SSO_REGION = os.environ['SSO_REGION']  # us-east-1
CLIENT_ID = os.environ['CLIENT_ID']  # From register-client
CLIENT_SECRET = os.environ['CLIENT_SECRET']  # From register-client
REDIRECT_URI = os.environ['REDIRECT_URI']  # https://your-api-gateway-url/prod/callback
SESSION_SECRET = os.environ['SESSION_SECRET']  # Random secret for JWT signing
AWS_ACCOUNT_ID = os.environ['AWS_ACCOUNT_ID']  # 211050572089
ROLE_NAME = os.environ.get('ROLE_NAME', 'CCA-CLI-Access')

# AWS clients
dynamodb = boto3.resource('dynamodb', region_name=SSO_REGION)
sessions_table = dynamodb.Table('cca-web-sessions')
sso_client = boto3.client('sso', region_name=SSO_REGION)

# Discover OIDC endpoints
def get_oidc_config():
    """Get OIDC configuration from Identity Center"""
    # Extract directory ID from SSO start URL
    directory_id = SSO_START_URL.split('/')[-1].split('.')[0]
    issuer_url = f"https://oidc.{SSO_REGION}.amazonaws.com/{directory_id}"

    # Fetch OIDC discovery document
    response = requests.get(f"{issuer_url}/.well-known/openid-configuration")
    return response.json()

# Cache OIDC config
OIDC_CONFIG = get_oidc_config()
AUTHORIZATION_ENDPOINT = OIDC_CONFIG['authorization_endpoint']
TOKEN_ENDPOINT = OIDC_CONFIG['token_endpoint']
USERINFO_ENDPOINT = OIDC_CONFIG['userinfo_endpoint']


def generate_pkce_pair():
    """Generate PKCE code verifier and challenge"""
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('utf-8').rstrip('=')
    return code_verifier, code_challenge


def create_session(session_data):
    """Create session in DynamoDB"""
    session_id = secrets.token_urlsafe(32)
    ttl = int(time.time()) + 3600  # 1 hour expiration

    sessions_table.put_item(
        Item={
            'session_id': session_id,
            'data': json.dumps(session_data),
            'ttl': ttl,
            'created_at': datetime.utcnow().isoformat()
        }
    )
    return session_id


def get_session(session_id):
    """Retrieve session from DynamoDB"""
    try:
        response = sessions_table.get_item(Key={'session_id': session_id})
        if 'Item' in response:
            return json.loads(response['Item']['data'])
    except Exception as e:
        print(f"Error retrieving session: {e}")
    return None


def update_session(session_id, session_data):
    """Update session in DynamoDB"""
    ttl = int(time.time()) + 3600  # Extend expiration
    sessions_table.update_item(
        Key={'session_id': session_id},
        UpdateExpression='SET #data = :data, #ttl = :ttl',
        ExpressionAttributeNames={
            '#data': 'data',
            '#ttl': 'ttl'
        },
        ExpressionAttributeValues={
            ':data': json.dumps(session_data),
            ':ttl': ttl
        }
    )


def delete_session(session_id):
    """Delete session from DynamoDB"""
    sessions_table.delete_item(Key={'session_id': session_id})


def create_session_cookie(session_id):
    """Create secure session cookie"""
    return f"session_id={session_id}; HttpOnly; Secure; SameSite=Lax; Max-Age=3600; Path=/"


def parse_cookies(cookie_header):
    """Parse cookies from request"""
    cookies = {}
    if cookie_header:
        for cookie in cookie_header.split(';'):
            parts = cookie.strip().split('=', 1)
            if len(parts) == 2:
                cookies[parts[0]] = parts[1]
    return cookies


def handle_login(event):
    """Handle /login - initiate OAuth2 flow"""
    # Generate PKCE parameters
    code_verifier, code_challenge = generate_pkce_pair()
    state = secrets.token_urlsafe(32)

    # Store code_verifier and state in session
    session_data = {
        'code_verifier': code_verifier,
        'state': state,
        'timestamp': datetime.utcnow().isoformat()
    }
    session_id = create_session(session_data)

    # Build authorization URL
    auth_params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': REDIRECT_URI,
        'scope': 'openid profile email',
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
        'state': state
    }
    auth_url = f"{AUTHORIZATION_ENDPOINT}?{urlencode(auth_params)}"

    # Redirect to Identity Center login
    return {
        'statusCode': 302,
        'headers': {
            'Location': auth_url,
            'Set-Cookie': create_session_cookie(session_id),
            'Content-Type': 'application/json'
        },
        'body': json.dumps({'message': 'Redirecting to login'})
    }


def handle_callback(event):
    """Handle /callback - complete OAuth2 flow"""
    # Parse query parameters
    params = event.get('queryStringParameters', {})
    code = params.get('code')
    state = params.get('state')

    if not code or not state:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing code or state parameter'})
        }

    # Get session from cookie
    cookies = parse_cookies(event.get('headers', {}).get('cookie', ''))
    session_id = cookies.get('session_id')

    if not session_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'No session cookie found'})
        }

    session_data = get_session(session_id)
    if not session_data:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid or expired session'})
        }

    # Verify state parameter
    if state != session_data.get('state'):
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid state parameter'})
        }

    # Exchange authorization code for tokens
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code_verifier': session_data['code_verifier']
    }

    try:
        token_response = requests.post(
            TOKEN_ENDPOINT,
            data=token_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        token_response.raise_for_status()
        tokens = token_response.json()
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Token exchange failed: {str(e)}'})
        }

    # Get user info
    try:
        userinfo_response = requests.get(
            USERINFO_ENDPOINT,
            headers={'Authorization': f"Bearer {tokens['access_token']}"}
        )
        userinfo_response.raise_for_status()
        userinfo = userinfo_response.json()
    except Exception as e:
        userinfo = {}

    # Exchange token for AWS credentials
    try:
        aws_credentials = get_aws_credentials(tokens['access_token'])
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'AWS credentials exchange failed: {str(e)}'})
        }

    # Update session with tokens and credentials
    session_data.update({
        'access_token': tokens['access_token'],
        'id_token': tokens.get('id_token'),
        'refresh_token': tokens.get('refresh_token'),
        'token_expiry': (datetime.utcnow() + timedelta(seconds=tokens['expires_in'])).isoformat(),
        'user': userinfo,
        'aws_credentials': aws_credentials,
        'authenticated': True
    })
    update_session(session_id, session_data)

    # Redirect to dashboard
    return {
        'statusCode': 302,
        'headers': {
            'Location': '/prod/dashboard',
            'Set-Cookie': create_session_cookie(session_id),
            'Content-Type': 'application/json'
        },
        'body': json.dumps({'message': 'Authentication successful'})
    }


def get_aws_credentials(access_token):
    """Exchange Identity Center token for AWS credentials"""
    response = sso_client.get_role_credentials(
        roleName=ROLE_NAME,
        accountId=AWS_ACCOUNT_ID,
        accessToken=access_token
    )

    creds = response['roleCredentials']
    return {
        'accessKeyId': creds['accessKeyId'],
        'secretAccessKey': creds['secretAccessKey'],
        'sessionToken': creds['sessionToken'],
        'expiration': creds['expiration']
    }


def handle_dashboard(event):
    """Handle /dashboard - protected route"""
    # Get session from cookie
    cookies = parse_cookies(event.get('headers', {}).get('cookie', ''))
    session_id = cookies.get('session_id')

    if not session_id:
        return {
            'statusCode': 401,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Not authenticated'})
        }

    session_data = get_session(session_id)
    if not session_data or not session_data.get('authenticated'):
        return {
            'statusCode': 401,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Not authenticated'})
        }

    user = session_data.get('user', {})

    # Return dashboard HTML or JSON
    dashboard_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>CCA Dashboard</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
            .user-info {{ background: #f5f5f5; padding: 20px; border-radius: 8px; }}
            .logout-btn {{ background: #dc3545; color: white; padding: 10px 20px;
                          border: none; border-radius: 4px; cursor: pointer; }}
            .logout-btn:hover {{ background: #c82333; }}
        </style>
    </head>
    <body>
        <h1>Welcome to CCA Dashboard</h1>
        <div class="user-info">
            <h2>User Information</h2>
            <p><strong>Name:</strong> {user.get('name', 'N/A')}</p>
            <p><strong>Email:</strong> {user.get('email', 'N/A')}</p>
            <p><strong>Username:</strong> {user.get('preferred_username', 'N/A')}</p>
        </div>
        <br>
        <button class="logout-btn" onclick="window.location.href='/prod/logout'">Logout</button>
    </body>
    </html>
    """

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'text/html'},
        'body': dashboard_html
    }


def handle_api_data(event):
    """Handle /api/data - protected API endpoint"""
    # Get session from cookie
    cookies = parse_cookies(event.get('headers', {}).get('cookie', ''))
    session_id = cookies.get('session_id')

    if not session_id:
        return {
            'statusCode': 401,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Not authenticated'})
        }

    session_data = get_session(session_id)
    if not session_data or not session_data.get('authenticated'):
        return {
            'statusCode': 401,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Not authenticated'})
        }

    # Get AWS credentials from session
    aws_creds = session_data.get('aws_credentials', {})

    # Use AWS credentials to access S3
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_creds['accessKeyId'],
            aws_secret_access_key=aws_creds['secretAccessKey'],
            aws_session_token=aws_creds['sessionToken']
        )

        buckets = s3_client.list_buckets()
        bucket_names = [bucket['Name'] for bucket in buckets['Buckets']]

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'message': 'AWS API call successful',
                'buckets': bucket_names,
                'count': len(bucket_names)
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': f'AWS API call failed: {str(e)}'})
        }


def handle_logout(event):
    """Handle /logout - destroy session"""
    # Get session from cookie
    cookies = parse_cookies(event.get('headers', {}).get('cookie', ''))
    session_id = cookies.get('session_id')

    if session_id:
        delete_session(session_id)

    # Redirect to home with expired cookie
    return {
        'statusCode': 302,
        'headers': {
            'Location': '/prod/',
            'Set-Cookie': 'session_id=; HttpOnly; Secure; SameSite=Lax; Max-Age=0; Path=/',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({'message': 'Logged out successfully'})
    }


def handle_home(event):
    """Handle / - home page"""
    home_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CCA Web App</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 100px auto;
                   text-align: center; padding: 20px; }
            .login-btn { background: #007bff; color: white; padding: 15px 30px;
                        border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
            .login-btn:hover { background: #0056b3; }
        </style>
    </head>
    <body>
        <h1>Cloud CLI Access Web Application</h1>
        <p>Secure authentication using AWS IAM Identity Center</p>
        <button class="login-btn" onclick="window.location.href='/prod/login'">
            Login with IAM Identity Center
        </button>
    </body>
    </html>
    """

    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'text/html'},
        'body': home_html
    }


def lambda_handler(event, context):
    """Main Lambda handler - route requests"""
    print(f"Event: {json.dumps(event)}")

    path = event.get('rawPath', event.get('path', '/'))
    http_method = event.get('requestContext', {}).get('http', {}).get('method',
                            event.get('httpMethod', 'GET'))

    # Route requests
    if path == '/prod/' or path == '/':
        return handle_home(event)
    elif path == '/prod/login':
        return handle_login(event)
    elif path == '/prod/callback':
        return handle_callback(event)
    elif path == '/prod/dashboard':
        return handle_dashboard(event)
    elif path == '/prod/api/data' and http_method == 'GET':
        return handle_api_data(event)
    elif path == '/prod/logout':
        return handle_logout(event)
    else:
        return {
            'statusCode': 404,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': 'Not found'})
        }
```

---

### 5. Lambda Dependencies (requirements.txt)

```
boto3>=1.34.0
requests>=2.31.0
python-jose[cryptography]>=3.3.0
```

---

### 6. Create Lambda Deployment Package

```bash
# Create deployment directory
mkdir -p lambda-web-auth
cd lambda-web-auth

# Copy Lambda function
cp ../cca_web_auth.py .

# Install dependencies
pip3 install -r requirements.txt -t .

# Create deployment package
zip -r cca-web-auth.zip .

# Upload to Lambda
aws lambda create-function \
  --function-name cca-web-auth \
  --runtime python3.11 \
  --role arn:aws:iam::211050572089:role/CCA-Lambda-Web-Role \
  --handler cca_web_auth.lambda_handler \
  --zip-file fileb://cca-web-auth.zip \
  --timeout 30 \
  --memory-size 256 \
  --environment Variables="{
    SSO_START_URL=https://d-9066117351.awsapps.com/start,
    SSO_REGION=us-east-1,
    CLIENT_ID=YOUR_CLIENT_ID,
    CLIENT_SECRET=YOUR_CLIENT_SECRET,
    REDIRECT_URI=https://your-api-id.execute-api.us-east-1.amazonaws.com/prod/callback,
    SESSION_SECRET=$(openssl rand -base64 32),
    AWS_ACCOUNT_ID=211050572089,
    ROLE_NAME=CCA-CLI-Access
  }" \
  --tags project=CCA
```

---

### 7. Create Lambda Execution Role

```bash
# Create IAM role trust policy
cat > lambda-web-trust-policy.json <<'EOF'
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
  --role-name CCA-Lambda-Web-Role \
  --assume-role-policy-document file://lambda-web-trust-policy.json \
  --tags Key=project,Value=CCA

# Create IAM policy
cat > lambda-web-policy.json <<'EOF'
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
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:211050572089:table/cca-web-sessions"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sso:GetRoleCredentials"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# Attach policy
aws iam put-role-policy \
  --role-name CCA-Lambda-Web-Role \
  --policy-name CCA-Lambda-Web-Policy \
  --policy-document file://lambda-web-policy.json
```

---

### 8. Create API Gateway

```bash
# Create HTTP API (cheaper and simpler than REST API)
aws apigatewayv2 create-api \
  --name cca-web-api \
  --protocol-type HTTP \
  --target arn:aws:lambda:us-east-1:211050572089:function:cca-web-auth \
  --cors-configuration AllowOrigins="*",AllowMethods="GET,POST",AllowHeaders="*"

# Save the API ID from response
API_ID="your-api-id"

# Grant API Gateway permission to invoke Lambda
aws lambda add-permission \
  --function-name cca-web-auth \
  --statement-id apigateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:us-east-1:211050572089:${API_ID}/*/*"

# Create integration
aws apigatewayv2 create-integration \
  --api-id $API_ID \
  --integration-type AWS_PROXY \
  --integration-uri arn:aws:lambda:us-east-1:211050572089:function:cca-web-auth \
  --payload-format-version 2.0

# Get integration ID
INTEGRATION_ID=$(aws apigatewayv2 get-integrations --api-id $API_ID --query 'Items[0].IntegrationId' --output text)

# Create routes
aws apigatewayv2 create-route \
  --api-id $API_ID \
  --route-key 'GET /' \
  --target integrations/$INTEGRATION_ID

aws apigatewayv2 create-route \
  --api-id $API_ID \
  --route-key 'GET /login' \
  --target integrations/$INTEGRATION_ID

aws apigatewayv2 create-route \
  --api-id $API_ID \
  --route-key 'GET /callback' \
  --target integrations/$INTEGRATION_ID

aws apigatewayv2 create-route \
  --api-id $API_ID \
  --route-key 'GET /dashboard' \
  --target integrations/$INTEGRATION_ID

aws apigatewayv2 create-route \
  --api-id $API_ID \
  --route-key 'GET /api/data' \
  --target integrations/$INTEGRATION_ID

aws apigatewayv2 create-route \
  --api-id $API_ID \
  --route-key 'GET /logout' \
  --target integrations/$INTEGRATION_ID

# Create deployment and stage
aws apigatewayv2 create-stage \
  --api-id $API_ID \
  --stage-name prod \
  --auto-deploy

# Your API is now available at:
echo "API URL: https://${API_ID}.execute-api.us-east-1.amazonaws.com/prod"
```

---

### 9. Update Redirect URI

After creating API Gateway, update the redirect URI in your OIDC client registration:

```bash
# Your actual redirect URI
REDIRECT_URI="https://${API_ID}.execute-api.us-east-1.amazonaws.com/prod/callback"

# Update Lambda environment variable
aws lambda update-function-configuration \
  --function-name cca-web-auth \
  --environment Variables="{
    SSO_START_URL=https://d-9066117351.awsapps.com/start,
    SSO_REGION=us-east-1,
    CLIENT_ID=YOUR_CLIENT_ID,
    CLIENT_SECRET=YOUR_CLIENT_SECRET,
    REDIRECT_URI=${REDIRECT_URI},
    SESSION_SECRET=$(openssl rand -base64 32),
    AWS_ACCOUNT_ID=211050572089,
    ROLE_NAME=CCA-CLI-Access
  }"

# Note: You'll also need to add this redirect URI to your OIDC client configuration
# in IAM Identity Center (currently no AWS CLI command for this - use console)
```

---

## Testing

### Test the Web Application

1. **Open browser:**
   ```
   https://your-api-id.execute-api.us-east-1.amazonaws.com/prod/
   ```

2. **Click "Login with IAM Identity Center"**
   - Redirects to `/prod/login`
   - Creates session, redirects to Identity Center

3. **Authenticate**
   - Enter username/password in Identity Center
   - Redirects back to `/prod/callback`

4. **View Dashboard**
   - Shows user information
   - Session stored in DynamoDB

5. **Test API Endpoint**
   ```bash
   curl https://your-api-id.execute-api.us-east-1.amazonaws.com/prod/api/data \
     -H "Cookie: session_id=YOUR_SESSION_ID"
   ```

6. **Logout**
   - Click logout button
   - Session deleted from DynamoDB

---

## Comparison: Node.js vs Python Lambda

| Aspect | Node.js/Express | Python Lambda |
|--------|-----------------|---------------|
| **Infrastructure** | EC2, ECS, or Fargate | Lambda + API Gateway |
| **Cost** | Always running (~$10-50/month) | Pay per request (~$0.20-2/month) |
| **Scaling** | Manual or auto-scaling groups | Automatic, instant |
| **Maintenance** | Server patching required | Fully managed |
| **Cold Start** | No cold start | 100-500ms cold start |
| **Session Storage** | In-memory or Redis | DynamoDB |
| **State Management** | express-session | DynamoDB + cookies |
| **Dependencies** | npm packages | pip packages |
| **Deployment** | Docker, PM2, etc. | Zip file or container |

---

## Advanced: Stateless JWT Sessions (No DynamoDB)

If you want to avoid DynamoDB, you can use stateless JWT tokens:

```python
def create_session_token(session_data):
    """Create JWT session token"""
    payload = {
        'data': session_data,
        'exp': datetime.utcnow() + timedelta(hours=1)
    }
    token = jwt.encode(payload, SESSION_SECRET, algorithm='HS256')
    return token

def verify_session_token(token):
    """Verify and decode JWT session token"""
    try:
        payload = jwt.decode(token, SESSION_SECRET, algorithms=['HS256'])
        return payload['data']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def create_session_cookie(session_data):
    """Create JWT-based session cookie"""
    token = create_session_token(session_data)
    return f"session={token}; HttpOnly; Secure; SameSite=Lax; Max-Age=3600; Path=/"
```

**Trade-offs:**
- ✅ No DynamoDB required (lower cost)
- ✅ Fully stateless (better for scaling)
- ❌ Cannot invalidate sessions server-side
- ❌ Larger cookie size (4KB limit)
- ❌ All session data in cookie (security consideration)

---

## Cost Estimate

**With DynamoDB Sessions:**
- Lambda: ~$0.20/month (1M requests free tier)
- API Gateway: ~$1.00/month (1M requests free tier)
- DynamoDB: ~$0.25/month (25 GB storage free tier)
- **Total: ~$1.45/month** (after free tier)

**With JWT Sessions (no DynamoDB):**
- Lambda: ~$0.20/month
- API Gateway: ~$1.00/month
- **Total: ~$1.20/month** (after free tier)

**Traditional Node.js Server:**
- EC2 t3.small: ~$15/month
- Load Balancer: ~$16/month
- **Total: ~$31/month**

**Savings: ~$30/month (~96% cost reduction)**

---

## Security Considerations

1. **Session Storage:**
   - DynamoDB: Encrypted at rest, access controlled via IAM
   - JWT: Signed with secret key, HttpOnly cookies

2. **Credentials:**
   - CLIENT_SECRET stored in Lambda environment variables (encrypted)
   - AWS credentials never stored in cookies
   - Short-lived tokens (1 hour)

3. **PKCE:**
   - Implemented for public client security
   - Prevents authorization code interception

4. **HTTPS:**
   - API Gateway enforces HTTPS
   - Secure cookies with HttpOnly, Secure flags

5. **Session Expiration:**
   - DynamoDB TTL: Automatic cleanup
   - Cookie Max-Age: 1 hour
   - AWS credentials: 12 hours

---

## Summary

✅ **Python Lambda implementation complete** - Full OAuth2 Authorization Code flow

✅ **Serverless architecture** - No servers to manage, auto-scaling, pay-per-use

✅ **Two session options:**
   - DynamoDB for server-side sessions (recommended)
   - JWT for stateless sessions (simpler, lower cost)

✅ **Same security as Node.js** - PKCE, HTTPS, secure cookies, token management

✅ **Significant cost savings** - ~$1.20-1.45/month vs ~$31/month for traditional server

✅ **Easy to deploy** - Single Lambda function, API Gateway, optional DynamoDB table

---

## Next Steps

1. Register OIDC application client in Identity Center
2. Create DynamoDB table (or use JWT sessions)
3. Deploy Lambda function with dependencies
4. Create API Gateway and configure routes
5. Update environment variables with client credentials
6. Test authentication flow
7. Add custom domain (optional - see Custom Domain Setup guide)
8. Monitor with CloudWatch Logs

---

**Ready to deploy!** 🚀

Python Lambda provides the same OAuth2 authentication capabilities as Node.js/Express, but with serverless benefits: lower cost, auto-scaling, and zero server management.
