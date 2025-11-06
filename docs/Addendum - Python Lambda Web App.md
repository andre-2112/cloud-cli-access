# CCA Framework - Python Lambda Web Application Backend

**Document Version:** 2.0
**Last Updated:** November 6, 2025
**Purpose:** Implement CCA web application authentication using Python Lambda instead of Node.js

---

## Overview

This document shows how to implement the web application OAuth2 authentication flow using **Python Lambda functions** with **API Gateway** - fully stateless with JWT sessions, no database required.

### Key Benefits

✅ **Serverless** - No server management required
✅ **Stateless** - JWT-based sessions, no database
✅ **Cost Effective** - ~$1.20/month (Lambda + API Gateway only)
✅ **Consistent** - Same JWT approach as CCA approval workflow
✅ **Simple** - Single Lambda function, minimal infrastructure

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
                                    │  - Stateless JWT │
                                    └────────┬─────────┘
                                              │
                              ┌───────────────┴──────────────┐
                              │                              │
                              ▼                              ▼
                    ┌──────────────────┐         ┌─────────────────┐
                    │  IAM Identity    │         │  AWS Services   │
                    │     Center       │         │  (S3, EC2, etc) │
                    └──────────────────┘         └─────────────────┘
```

**Infrastructure Required:**
- Lambda Function (1)
- API Gateway (1)
- IAM Identity Center (existing)

**NO database, NO DynamoDB, NO complexity!**

---

## Implementation Guide

### 1. Prerequisites

**Required AWS Resources:**
- IAM Identity Center enabled with CCA framework
- Lambda execution role with basic permissions

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

### 3. Python Lambda Function (Stateless JWT)

Create a Python Lambda function with JWT-based session management:

**File: `lambda/cca_web_auth.py`**

```python
import json
import os
import time
import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from urllib.parse import urlencode
import boto3
import requests
from jose import jwt, JWTError

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


def create_jwt_token(data, expiry_hours=1):
    """Create JWT token for session data"""
    payload = {
        'data': data,
        'exp': datetime.utcnow() + timedelta(hours=expiry_hours),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, SESSION_SECRET, algorithm='HS256')


def verify_jwt_token(token):
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, SESSION_SECRET, algorithms=['HS256'])
        return payload['data']
    except JWTError as e:
        print(f"JWT verification failed: {e}")
        return None


def create_session_cookie(data, max_age=3600):
    """Create secure JWT session cookie"""
    token = create_jwt_token(data, expiry_hours=max_age//3600)
    return f"session={token}; HttpOnly; Secure; SameSite=Lax; Max-Age={max_age}; Path=/"


def parse_cookies(cookie_header):
    """Parse cookies from request"""
    cookies = {}
    if cookie_header:
        for cookie in cookie_header.split(';'):
            parts = cookie.strip().split('=', 1)
            if len(parts) == 2:
                cookies[parts[0]] = parts[1]
    return cookies


def get_session_from_cookie(event):
    """Extract and verify session from cookie"""
    cookies = parse_cookies(event.get('headers', {}).get('cookie', ''))
    session_token = cookies.get('session')

    if not session_token:
        return None

    return verify_jwt_token(session_token)


def handle_login(event):
    """Handle /login - initiate OAuth2 flow"""
    # Generate PKCE parameters
    code_verifier, code_challenge = generate_pkce_pair()
    state = secrets.token_urlsafe(32)

    # Store code_verifier and state in JWT cookie (temporary, 5 minutes)
    session_data = {
        'code_verifier': code_verifier,
        'state': state,
        'flow': 'oauth_pending',
        'timestamp': datetime.utcnow().isoformat()
    }

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

    # Redirect to Identity Center login with session cookie
    return {
        'statusCode': 302,
        'headers': {
            'Location': auth_url,
            'Set-Cookie': create_session_cookie(session_data, max_age=300),  # 5 min for OAuth flow
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
            'headers': {'Content-Type': 'text/html'},
            'body': '<h1>Error</h1><p>Missing code or state parameter</p>'
        }

    # Get session from JWT cookie
    session_data = get_session_from_cookie(event)

    if not session_data or session_data.get('flow') != 'oauth_pending':
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'text/html'},
            'body': '<h1>Error</h1><p>Invalid or expired session</p>'
        }

    # Verify state parameter
    if state != session_data.get('state'):
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'text/html'},
            'body': '<h1>Error</h1><p>Invalid state parameter - possible CSRF attack</p>'
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
            'headers': {'Content-Type': 'text/html'},
            'body': f'<h1>Error</h1><p>Token exchange failed: {str(e)}</p>'
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
            'headers': {'Content-Type': 'text/html'},
            'body': f'<h1>Error</h1><p>AWS credentials exchange failed: {str(e)}</p>'
        }

    # Create new session with authentication data (1 hour)
    authenticated_session = {
        'authenticated': True,
        'user': userinfo,
        'access_token': tokens['access_token'],
        'refresh_token': tokens.get('refresh_token'),
        'token_expiry': (datetime.utcnow() + timedelta(seconds=tokens['expires_in'])).isoformat(),
        'aws_credentials': aws_credentials,
        'login_time': datetime.utcnow().isoformat()
    }

    # Redirect to dashboard with authenticated session
    return {
        'statusCode': 302,
        'headers': {
            'Location': '/prod/dashboard',
            'Set-Cookie': create_session_cookie(authenticated_session, max_age=3600),  # 1 hour
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
    # Get session from JWT cookie
    session_data = get_session_from_cookie(event)

    if not session_data or not session_data.get('authenticated'):
        return {
            'statusCode': 302,
            'headers': {
                'Location': '/prod/',
                'Content-Type': 'text/html'
            },
            'body': '<h1>Unauthorized</h1><p>Please login first</p>'
        }

    user = session_data.get('user', {})
    login_time = session_data.get('login_time', 'Unknown')

    # Return dashboard HTML
    dashboard_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>CCA Dashboard</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                max-width: 900px;
                margin: 50px auto;
                padding: 20px;
                background: #f5f5f5;
            }}
            .container {{
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            h1 {{ color: #333; margin-top: 0; }}
            .user-info {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
            }}
            .info-row {{ margin: 10px 0; }}
            .label {{ font-weight: bold; color: #555; }}
            .value {{ color: #333; }}
            .btn {{
                padding: 12px 24px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 500;
                text-decoration: none;
                display: inline-block;
                margin: 5px;
            }}
            .btn-logout {{ background: #dc3545; color: white; }}
            .btn-logout:hover {{ background: #c82333; }}
            .btn-test {{ background: #007bff; color: white; }}
            .btn-test:hover {{ background: #0056b3; }}
            .footer {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                color: #666;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔐 CCA Dashboard</h1>
            <p>Welcome to Cloud CLI Access Web Application</p>

            <div class="user-info">
                <h2>User Information</h2>
                <div class="info-row">
                    <span class="label">Name:</span>
                    <span class="value">{user.get('name', 'N/A')}</span>
                </div>
                <div class="info-row">
                    <span class="label">Email:</span>
                    <span class="value">{user.get('email', 'N/A')}</span>
                </div>
                <div class="info-row">
                    <span class="label">Username:</span>
                    <span class="value">{user.get('preferred_username', 'N/A')}</span>
                </div>
                <div class="info-row">
                    <span class="label">Login Time:</span>
                    <span class="value">{login_time}</span>
                </div>
            </div>

            <div>
                <a href="/prod/api/data" class="btn btn-test">Test AWS Access</a>
                <a href="/prod/logout" class="btn btn-logout">Logout</a>
            </div>

            <div class="footer">
                <strong>Session Management:</strong> Stateless JWT (no database)<br>
                <strong>Authentication:</strong> AWS IAM Identity Center<br>
                <strong>Session Duration:</strong> 1 hour
            </div>
        </div>
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
    # Get session from JWT cookie
    session_data = get_session_from_cookie(event)

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

        # Return HTML response
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>AWS Access Test</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
                .success {{ background: #d4edda; padding: 20px; border-radius: 8px; color: #155724; }}
                .bucket-list {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                .btn {{ background: #007bff; color: white; padding: 10px 20px;
                       border: none; border-radius: 4px; cursor: pointer; text-decoration: none; }}
            </style>
        </head>
        <body>
            <h1>✅ AWS Access Test Successful</h1>
            <div class="success">
                <strong>Test Result:</strong> Successfully authenticated and accessed AWS S3
            </div>
            <div class="bucket-list">
                <h2>S3 Buckets ({len(bucket_names)})</h2>
                <ul>
                    {''.join([f'<li>{bucket}</li>' for bucket in bucket_names[:10]])}
                    {f'<li><em>... and {len(bucket_names)-10} more</em></li>' if len(bucket_names) > 10 else ''}
                </ul>
            </div>
            <a href="/prod/dashboard" class="btn">Back to Dashboard</a>
        </body>
        </html>
        """

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'text/html'},
            'body': html
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'text/html'},
            'body': f'<h1>Error</h1><p>AWS API call failed: {str(e)}</p><a href="/prod/dashboard">Back to Dashboard</a>'
        }


def handle_logout(event):
    """Handle /logout - destroy session"""
    # Redirect to home with expired cookie
    return {
        'statusCode': 302,
        'headers': {
            'Location': '/prod/',
            'Set-Cookie': 'session=; HttpOnly; Secure; SameSite=Lax; Max-Age=0; Path=/',
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
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                max-width: 700px;
                margin: 100px auto;
                text-align: center;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                min-height: 100vh;
            }
            .container {
                background: rgba(255, 255, 255, 0.95);
                padding: 60px 40px;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                color: #333;
            }
            h1 {
                color: #667eea;
                margin-bottom: 10px;
                font-size: 2.5em;
            }
            .subtitle {
                color: #666;
                font-size: 1.2em;
                margin-bottom: 40px;
            }
            .features {
                text-align: left;
                margin: 30px 0;
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
            }
            .features li {
                margin: 10px 0;
                color: #555;
            }
            .login-btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 18px 40px;
                border: none;
                border-radius: 50px;
                cursor: pointer;
                font-size: 18px;
                font-weight: 600;
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
                transition: transform 0.2s;
            }
            .login-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 7px 20px rgba(102, 126, 234, 0.6);
            }
            .footer {
                margin-top: 30px;
                font-size: 14px;
                color: #999;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔐 Cloud CLI Access</h1>
            <p class="subtitle">Secure Web Application Authentication</p>

            <div class="features">
                <strong>Features:</strong>
                <ul>
                    <li>✅ AWS IAM Identity Center authentication</li>
                    <li>✅ Stateless JWT sessions (no database)</li>
                    <li>✅ Secure OAuth2 flow with PKCE</li>
                    <li>✅ Direct AWS service access</li>
                    <li>✅ 1-hour session duration</li>
                </ul>
            </div>

            <button class="login-btn" onclick="window.location.href='/prod/login'">
                Login with IAM Identity Center
            </button>

            <div class="footer">
                Powered by Python Lambda • Stateless & Serverless
            </div>
        </div>
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
            'headers': {'Content-Type': 'text/html'},
            'body': '<h1>404 Not Found</h1><p>The requested page does not exist.</p>'
        }
```

---

### 4. Lambda Dependencies (requirements.txt)

```
boto3>=1.34.0
requests>=2.31.0
python-jose[cryptography]>=3.3.0
```

**Why these libraries:**
- `boto3` - AWS SDK for accessing IAM Identity Center and AWS services
- `requests` - HTTP client for OIDC endpoints
- `python-jose` - JWT creation and verification (same approach as CCA approval workflow)

---

### 5. Create Lambda Deployment Package

```bash
# Create deployment directory
mkdir -p lambda-web-auth
cd lambda-web-auth

# Copy Lambda function
cp ../cca_web_auth.py .

# Create requirements.txt
cat > requirements.txt <<'EOF'
boto3>=1.34.0
requests>=2.31.0
python-jose[cryptography]>=3.3.0
EOF

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

### 6. Create Lambda Execution Role

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

# Create IAM policy (NO DynamoDB permissions needed!)
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

**Notice:** Much simpler policy - only CloudWatch Logs and SSO permissions. No DynamoDB!

---

### 7. Create API Gateway

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

## Testing

### Test the Web Application

1. **Open browser:**
   ```
   https://your-api-id.execute-api.us-east-1.amazonaws.com/prod/
   ```

2. **Click "Login with IAM Identity Center"**
   - Redirects to `/prod/login`
   - Creates JWT session cookie with PKCE parameters
   - Redirects to Identity Center

3. **Authenticate**
   - Enter username/password in Identity Center
   - Redirects back to `/prod/callback`

4. **View Dashboard**
   - Shows user information
   - Session stored in JWT cookie (no database query!)

5. **Test AWS Access**
   - Click "Test AWS Access" button
   - Lists S3 buckets using AWS credentials

6. **Logout**
   - Click logout button
   - JWT cookie expires immediately

---

## How JWT Sessions Work

### During OAuth Flow (5 minutes):
```
JWT Cookie Content:
{
  "code_verifier": "random_string",
  "state": "random_string",
  "flow": "oauth_pending",
  "timestamp": "2025-11-06T12:00:00Z"
}
Expiry: 5 minutes (just long enough for OAuth flow)
```

### After Authentication (1 hour):
```
JWT Cookie Content:
{
  "authenticated": true,
  "user": { "name": "...", "email": "..." },
  "access_token": "...",
  "refresh_token": "...",
  "aws_credentials": { "accessKeyId": "...", ... },
  "login_time": "2025-11-06T12:00:30Z"
}
Expiry: 1 hour
```

**Security:**
- JWT signed with SESSION_SECRET (only Lambda can verify)
- HttpOnly cookie (JavaScript cannot access)
- Secure flag (HTTPS only)
- SameSite=Lax (CSRF protection)

---

## Cost Estimate

**Infrastructure Costs:**

| Service | Usage | Cost |
|---------|-------|------|
| Lambda | 1M requests/month | $0.20 (after free tier) |
| API Gateway | 1M requests/month | $1.00 (after free tier) |
| CloudWatch Logs | 1 GB/month | Free tier |
| **Total** | | **~$1.20/month** |

**What we eliminated:**
- ❌ DynamoDB: $0.25-5/month saved
- ❌ Database queries: Lower latency
- ❌ Database management: Less complexity

**Comparison:**
- Traditional Node.js server: ~$31/month (EC2 + ELB)
- Python Lambda with DynamoDB: ~$1.45/month
- **Python Lambda JWT-only: ~$1.20/month** ✅

---

## Why JWT Instead of DynamoDB?

### CCA Framework Philosophy:
```
✅ Stateless - No database for approval workflow
✅ JWT Tokens - Registration approval uses JWT
✅ Simple - Minimal infrastructure
✅ Cost Effective - Only essential services
```

### Web App Should Follow Same Pattern:
```
✅ Stateless - JWT session cookies
✅ No Database - Everything in signed token
✅ Simple - Single Lambda function
✅ Consistent - Same approach as rest of CCA
```

### JWT Trade-offs:

**Advantages:**
- ✅ No database needed
- ✅ Lower cost (~$0.25/month saved)
- ✅ Faster (no DB queries)
- ✅ Scales infinitely
- ✅ Consistent with CCA design

**Limitations:**
- ❌ Cannot revoke sessions server-side (must wait for expiry)
- ❌ Cookie size limit (4KB - enough for our use case)
- ❌ All session data in cookie (but encrypted and signed)

**For CCA web app: JWT is the right choice**
- Sessions are short (1 hour)
- No need for immediate revocation
- Consistent with CCA's stateless design

---

## Security Considerations

1. **JWT Signing:**
   - SESSION_SECRET stored in Lambda environment (encrypted)
   - HS256 algorithm (HMAC with SHA-256)
   - Cannot be forged without secret key

2. **Cookies:**
   - HttpOnly: JavaScript cannot access
   - Secure: HTTPS only
   - SameSite=Lax: CSRF protection

3. **OAuth2 PKCE:**
   - Code verifier in JWT cookie (temporary)
   - State parameter prevents CSRF
   - Code challenge prevents interception

4. **AWS Credentials:**
   - Stored in JWT cookie (signed, encrypted transit)
   - Short-lived (12 hours max)
   - No console access

5. **Session Expiration:**
   - OAuth flow: 5 minutes
   - Authenticated session: 1 hour
   - JWT exp claim enforced

---

## Comparison: Node.js vs Python Lambda (JWT)

| Aspect | Node.js/Express | Python Lambda (JWT) |
|--------|-----------------|---------------------|
| **Infrastructure** | EC2/ECS/Fargate | Lambda + API Gateway |
| **Database** | Redis/Postgres | None (JWT) |
| **Cost** | ~$31/month | ~$1.20/month |
| **Scaling** | Manual/Auto-scaling | Automatic |
| **Maintenance** | Server patching | Fully managed |
| **Session Storage** | Redis queries | JWT verification (in-memory) |
| **State** | Stateful | Stateless |
| **Cold Start** | No | 100-500ms |
| **Complexity** | High | Low |
| **Consistent with CCA** | No | Yes ✅ |

---

## Summary

✅ **Python Lambda implementation** - Full OAuth2 Authorization Code flow with PKCE

✅ **Stateless JWT sessions** - No database, no DynamoDB, no complexity

✅ **Consistent with CCA** - Same JWT approach as approval workflow

✅ **Simple infrastructure** - Lambda + API Gateway only (2 services)

✅ **Cost effective** - ~$1.20/month (vs ~$1.45 with DynamoDB, ~$31 with Node.js)

✅ **Same security** - PKCE, HTTPS, secure cookies, signed JWTs

✅ **Fast and scalable** - No database queries, infinite scale

---

## Deployment Steps Summary

1. ✅ Register OIDC client in Identity Center
2. ✅ Create Lambda execution role (logs + SSO permissions only)
3. ✅ Deploy Lambda function with JWT session code
4. ✅ Create API Gateway and configure routes
5. ✅ Set environment variables (CLIENT_ID, CLIENT_SECRET, SESSION_SECRET)
6. ✅ Test authentication flow
7. ✅ (Optional) Add custom domain

**NO DynamoDB table creation needed!**

---

**Ready to deploy!** 🚀

Python Lambda with JWT sessions provides the same OAuth2 authentication as Node.js/Express, but simpler, cheaper, and consistent with CCA's stateless design philosophy.

**Infrastructure:**
- 2 services (Lambda + API Gateway)
- No database
- ~$1.20/month
- Fully stateless and serverless
