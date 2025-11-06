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
    print(f"Event: {json.dumps(event)}")
    path = event.get('rawPath', event.get('path', ''))
    if path == '/register' or path == '/':
        return handle_registration(event)
    elif path == '/approve':
        return handle_approval(event)
    elif path == '/deny':
        return handle_denial(event)
    else:
        return {'statusCode': 404, 'body': json.dumps({'error': 'Not found'})}

def handle_registration(event):
    try:
        if event.get('body'):
            body = json.loads(event['body'])
        else:
            return error_response('Missing request body', 400)
    except json.JSONDecodeError:
        return error_response('Invalid JSON', 400)
    required = ['username', 'email', 'first_name', 'last_name']
    missing = [f for f in required if not body.get(f)]
    if missing:
        return error_response(f'Missing fields: {", ".join(missing)}', 400)
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
    lambda_url = event['requestContext']['domainName']
    protocol = 'https'
    approve_url = f"{protocol}://{lambda_url}/approve?token={approve_token}"
    deny_url = f"{protocol}://{lambda_url}/deny?token={deny_token}"
    try:
        send_admin_email(user_data, approve_url, deny_url)
    except Exception as e:
        print(f"Error sending email: {e}")
        return error_response(f'Failed to send email: {str(e)}', 500)
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
        'body': json.dumps({'message': 'Registration submitted successfully', 'status': 'pending_approval'})
    }

def handle_approval(event):
    params = event.get('queryStringParameters', {}) or {}
    token = params.get('token')
    if not token:
        return html_response('<h1>Error: Missing token</h1>', 400)
    try:
        user_data = verify_signed_token(token, 'approve')
    except Exception as e:
        return html_response(f'<h1>Error: Invalid or expired token</h1><p>{str(e)}</p>', 400)
    try:
        existing = identitystore.list_users(
            IdentityStoreId=IDENTITY_STORE_ID,
            Filters=[{'AttributePath': 'UserName', 'AttributeValue': user_data['username']}]
        )
        if existing.get('Users'):
            return html_response(f'<h1>User Already Exists</h1><p>User {user_data["username"]} was already created.</p>', 200)
    except Exception as e:
        print(f"Error checking existing user: {e}")
    try:
        user_id = create_identity_center_user(user_data)
        identitystore.create_group_membership(
            IdentityStoreId=IDENTITY_STORE_ID,
            GroupId=CLI_GROUP_ID,
            MemberId={'UserId': user_id}
        )
        send_welcome_email(user_data)
        return html_response(f'''<html><head><title>Registration Approved</title><style>body{{font-family:Arial,sans-serif;max-width:600px;margin:50px auto;padding:20px;text-align:center}}h1{{color:#28a745}}.info{{background:#f8f9fa;padding:15px;border-radius:5px;margin:20px 0}}</style></head><body><h1>Registration Approved</h1><div class="info"><p><strong>Username:</strong> {user_data["username"]}</p><p><strong>Email:</strong> {user_data["email"]}</p><p><strong>Name:</strong> {user_data["first_name"]} {user_data["last_name"]}</p></div><p>User has been created successfully.</p><p>They will receive an email to set their password.</p></body></html>''', 200)
    except Exception as e:
        print(f"Error creating user: {e}")
        return html_response(f'<h1>Error Creating User</h1><p>{str(e)}</p>', 500)

def handle_denial(event):
    params = event.get('queryStringParameters', {}) or {}
    token = params.get('token')
    if not token:
        return html_response('<h1>Error: Missing token</h1>', 400)
    try:
        user_data = verify_signed_token(token, 'deny')
    except Exception as e:
        return html_response(f'<h1>Error: Invalid or expired token</h1><p>{str(e)}</p>', 400)
    try:
        send_denial_email(user_data)
    except Exception as e:
        print(f"Error sending denial email: {e}")
    return html_response(f'''<html><head><title>Registration Denied</title><style>body{{font-family:Arial,sans-serif;max-width:600px;margin:50px auto;padding:20px;text-align:center}}h1{{color:#dc3545}}.info{{background:#f8f9fa;padding:15px;border-radius:5px;margin:20px 0}}</style></head><body><h1>Registration Denied</h1><div class="info"><p><strong>Username:</strong> {user_data["username"]}</p><p><strong>Email:</strong> {user_data["email"]}</p></div><p>Registration request has been denied.</p></body></html>''', 200)

def create_signed_token(data, action):
    payload = {'data': data, 'action': action}
    payload_json = json.dumps(payload, separators=(',', ':'))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode()
    signature = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    token = f"{payload_b64}.{signature}"
    return base64.urlsafe_b64encode(token.encode()).decode()

def verify_signed_token(token, expected_action):
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        payload_b64, signature = decoded.split('.')
        expected_sig = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            raise ValueError("Invalid signature")
        payload_json = base64.urlsafe_b64decode(payload_b64.encode()).decode()
        payload = json.loads(payload_json)
        if payload['action'] != expected_action:
            raise ValueError("Invalid action")
        expires_at = datetime.fromisoformat(payload['data']['expires_at'])
        if datetime.utcnow() > expires_at:
            raise ValueError("Token expired")
        return payload['data']
    except Exception as e:
        raise ValueError(f"Token verification failed: {str(e)}")

def create_identity_center_user(user_data):
    response = identitystore.create_user(
        IdentityStoreId=IDENTITY_STORE_ID,
        UserName=user_data['username'],
        DisplayName=f"{user_data['first_name']} {user_data['last_name']}",
        Name={'GivenName': user_data['first_name'], 'FamilyName': user_data['last_name'], 'Formatted': f"{user_data['first_name']} {user_data['last_name']}"},
        Emails=[{'Value
