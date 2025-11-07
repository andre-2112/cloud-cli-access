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
