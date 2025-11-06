# CCA Framework - REST API Client Authentication

**Document Version:** 1.0
**Last Updated:** November 6, 2025
**Purpose:** Extend CCA framework to support REST API client authentication

---

## Overview

The Cloud CLI Access (CCA) framework can be extended to authenticate not just CLI tools, but also REST API clients, web applications, mobile apps, and any OAuth2-compatible client.

### Key Points

✅ **Same Infrastructure** - No additional AWS resources needed
✅ **OAuth2 / OIDC Standard** - Industry-standard authentication flow
✅ **Multiple Client Types** - Support CLI, web, mobile, and server-to-server
✅ **Token-Based** - Stateless authentication with JWT tokens
✅ **IAM Integration** - Leverages existing IAM Identity Center

---

## Architecture Comparison

### Current: CLI Authentication Only

```
┌──────────┐        Device Flow          ┌─────────────────┐
│   CCC    │◄──────────────────────────►│  IAM Identity   │
│   CLI    │   (Browser-based OAuth)     │     Center      │
└──────────┘                              └─────────────────┘
                                                   │
                                                   ▼
                                          ┌─────────────────┐
                                          │  AWS Services   │
                                          │  (S3, EC2, etc) │
                                          └─────────────────┘
```

### Extended: CLI + REST API Clients

```
┌──────────┐        Device Flow          ┌─────────────────┐
│   CCC    │◄──────────────────────────►│                 │
│   CLI    │                             │                 │
└──────────┘                             │   IAM Identity  │
                                          │     Center      │
┌──────────┐    Authorization Code       │   (OIDC/OAuth2) │
│   Web    │◄──────────────────────────►│                 │
│   App    │                             │                 │
└──────────┘                             └────────┬────────┘
                                                   │
┌──────────┐    Client Credentials                │
│  API     │◄───────────────────────────────────►│
│ Service  │    (Machine-to-Machine)              │
└──────────┘                                       ▼
                                          ┌─────────────────┐
┌──────────┐    Implicit/PKCE            │  AWS Services   │
│ Mobile   │◄─────────────────────────►  │  (S3, EC2, etc) │
│   App    │                             │  + Custom APIs  │
└──────────┘                              └─────────────────┘
```

---

## Supported OAuth2 Flows

IAM Identity Center supports multiple OAuth2 flows for different client types:

| Flow | Use Case | Security | Best For |
|------|----------|----------|----------|
| **Device Code** | CLI tools, IoT devices | High | Current CCC implementation |
| **Authorization Code** | Web applications | Very High | Server-side web apps |
| **Authorization Code + PKCE** | Mobile/SPA | High | Mobile apps, SPAs |
| **Client Credentials** | Service-to-service | Very High | Backend services, APIs |
| **Refresh Token** | Long-lived sessions | High | All flows (token renewal) |

---

## Implementation Guide

### 1. Web Application Authentication

**Scenario:** Authenticate users of a web application using IAM Identity Center

#### 1.1 Register Application Client

```bash
# Create OIDC application client in Identity Center
aws sso-oidc register-client \
  --client-name "CCA-WebApp" \
  --client-type "public" \
  --scopes "openid" "profile" "email" \
  --redirect-uris "https://myapp.example.com/callback" \
  --grant-types "authorization_code" "refresh_token"
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

#### 1.2 Configure Web Application

**Backend Configuration (Node.js Example):**

```javascript
const express = require('express');
const session = require('express-session');
const { Issuer, generators } = require('openid-client');

const app = express();

// IAM Identity Center configuration
const SSO_START_URL = 'https://d-9066117351.awsapps.com/start';
const SSO_REGION = 'us-east-1';
const CLIENT_ID = 'AbCdEf123456';
const CLIENT_SECRET = 'SECRET_VALUE_HERE';
const REDIRECT_URI = 'https://myapp.example.com/callback';

// Session configuration
app.use(session({
  secret: 'your-session-secret',
  resave: false,
  saveUninitialized: false,
  cookie: { secure: true, httpOnly: true, maxAge: 3600000 } // 1 hour
}));

// Discover OIDC endpoints
async function setupOIDC() {
  const issuerUrl = `https://oidc.${SSO_REGION}.amazonaws.com/${SSO_START_URL.split('/')[3]}`;
  const issuer = await Issuer.discover(issuerUrl);

  const client = new issuer.Client({
    client_id: CLIENT_ID,
    client_secret: CLIENT_SECRET,
    redirect_uris: [REDIRECT_URI],
    response_types: ['code'],
  });

  return client;
}

// Login route - initiate authentication
app.get('/login', async (req, res) => {
  const client = await setupOIDC();
  const code_verifier = generators.codeVerifier();
  const code_challenge = generators.codeChallenge(code_verifier);

  req.session.code_verifier = code_verifier;

  const authUrl = client.authorizationUrl({
    scope: 'openid profile email',
    code_challenge,
    code_challenge_method: 'S256',
  });

  res.redirect(authUrl);
});

// Callback route - handle authentication response
app.get('/callback', async (req, res) => {
  const client = await setupOIDC();
  const params = client.callbackParams(req);

  try {
    const tokenSet = await client.callback(REDIRECT_URI, params, {
      code_verifier: req.session.code_verifier
    });

    // Store tokens in session
    req.session.access_token = tokenSet.access_token;
    req.session.id_token = tokenSet.id_token;
    req.session.refresh_token = tokenSet.refresh_token;

    // Get user info
    const userinfo = await client.userinfo(tokenSet.access_token);
    req.session.user = userinfo;

    // Exchange token for AWS credentials
    const awsCredentials = await getAWSCredentials(tokenSet.access_token);
    req.session.aws_credentials = awsCredentials;

    res.redirect('/dashboard');
  } catch (err) {
    console.error('Authentication error:', err);
    res.redirect('/error');
  }
});

// Get AWS credentials from Identity Center token
async function getAWSCredentials(accessToken) {
  const ssoClient = new AWS.SSO({ region: SSO_REGION });

  const roleCredentials = await ssoClient.getRoleCredentials({
    roleName: 'CCA-CLI-Access',
    accountId: '211050572089',
    accessToken: accessToken
  }).promise();

  return {
    accessKeyId: roleCredentials.roleCredentials.accessKeyId,
    secretAccessKey: roleCredentials.roleCredentials.secretAccessKey,
    sessionToken: roleCredentials.roleCredentials.sessionToken,
    expiration: roleCredentials.roleCredentials.expiration
  };
}

// Protected API endpoint
app.get('/api/data', (req, res) => {
  if (!req.session.access_token) {
    return res.status(401).json({ error: 'Not authenticated' });
  }

  // Use AWS credentials to access services
  const s3 = new AWS.S3({
    credentials: req.session.aws_credentials
  });

  s3.listBuckets((err, data) => {
    if (err) return res.status(500).json({ error: err.message });
    res.json({ buckets: data.Buckets });
  });
});

// Logout route
app.get('/logout', (req, res) => {
  req.session.destroy();
  res.redirect('/');
});

app.listen(3000);
```

#### 1.3 Frontend Integration (React Example)

```javascript
import React, { useState, useEffect } from 'react';
import axios from 'axios';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is authenticated
    axios.get('/api/user')
      .then(response => {
        setUser(response.data);
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
      });
  }, []);

  const handleLogin = () => {
    window.location.href = '/login';
  };

  const handleLogout = () => {
    window.location.href = '/logout';
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      {user ? (
        <div>
          <h1>Welcome, {user.name}</h1>
          <button onClick={handleLogout}>Logout</button>
        </div>
      ) : (
        <div>
          <h1>Please login</h1>
          <button onClick={handleLogin}>Login with IAM Identity Center</button>
        </div>
      )}
    </div>
  );
}

export default App;
```

---

### 2. REST API Client Authentication

**Scenario:** Authenticate a REST API client (Postman, curl, custom app)

#### 2.1 Client Credentials Flow (Service Accounts)

For machine-to-machine authentication without user interaction:

```bash
# 1. Register service client
aws sso-oidc register-client \
  --client-name "CCA-API-Service" \
  --client-type "confidential" \
  --grant-types "client_credentials"

# Response includes clientId and clientSecret

# 2. Get access token
curl -X POST "https://oidc.us-east-1.amazonaws.com/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=${CLIENT_ID}" \
  -d "client_secret=${CLIENT_SECRET}" \
  -d "scope=openid"

# Response:
# {
#   "access_token": "eyJra...",
#   "token_type": "Bearer",
#   "expires_in": 3600
# }

# 3. Use token to get AWS credentials
aws sso get-role-credentials \
  --role-name "CCA-CLI-Access" \
  --account-id "211050572089" \
  --access-token "eyJra..."
```

#### 2.2 REST API Client (Python Example)

```python
import requests
import boto3
from datetime import datetime, timedelta

class CCAuthClient:
    def __init__(self, client_id, client_secret, sso_region='us-east-1'):
        self.client_id = client_id
        self.client_secret = client_secret
        self.sso_region = sso_region
        self.token_url = f"https://oidc.{sso_region}.amazonaws.com/token"
        self.access_token = None
        self.token_expiry = None

    def authenticate(self):
        """Get access token using client credentials"""
        response = requests.post(
            self.token_url,
            data={
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'openid'
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data['access_token']
            self.token_expiry = datetime.now() + timedelta(seconds=token_data['expires_in'])
            return True
        else:
            raise Exception(f"Authentication failed: {response.text}")

    def get_aws_credentials(self, account_id, role_name):
        """Exchange access token for AWS credentials"""
        if not self.access_token or datetime.now() >= self.token_expiry:
            self.authenticate()

        sso_client = boto3.client('sso', region_name=self.sso_region)

        response = sso_client.get_role_credentials(
            roleName=role_name,
            accountId=account_id,
            accessToken=self.access_token
        )

        return response['roleCredentials']

    def make_api_request(self, method, url, **kwargs):
        """Make authenticated API request"""
        if not self.access_token or datetime.now() >= self.token_expiry:
            self.authenticate()

        headers = kwargs.get('headers', {})
        headers['Authorization'] = f"Bearer {self.access_token}"
        kwargs['headers'] = headers

        return requests.request(method, url, **kwargs)

# Usage
client = CCAuthClient(
    client_id='YOUR_CLIENT_ID',
    client_secret='YOUR_CLIENT_SECRET'
)

# Get AWS credentials
credentials = client.get_aws_credentials(
    account_id='211050572089',
    role_name='CCA-CLI-Access'
)

# Use credentials with boto3
session = boto3.Session(
    aws_access_key_id=credentials['accessKeyId'],
    aws_secret_access_key=credentials['secretAccessKey'],
    aws_session_token=credentials['sessionToken']
)

# Access AWS services
s3 = session.client('s3')
buckets = s3.list_buckets()
print(buckets)
```

---

### 3. Mobile App Authentication

**Scenario:** Authenticate users in a mobile app (iOS/Android)

#### 3.1 Authorization Code Flow with PKCE

PKCE (Proof Key for Code Exchange) adds security for public clients:

```swift
// iOS Swift Example
import AuthenticationServices

class CCAuthManager: NSObject, ASWebAuthenticationPresentationContextProviding {
    let clientId = "YOUR_CLIENT_ID"
    let redirectUri = "myapp://callback"
    let ssoRegion = "us-east-1"
    let ssoStartUrl = "https://d-9066117351.awsapps.com/start"

    func login(completion: @escaping (Result<String, Error>) -> Void) {
        // Generate PKCE code verifier and challenge
        let codeVerifier = generateCodeVerifier()
        let codeChallenge = generateCodeChallenge(from: codeVerifier)

        // Build authorization URL
        let authUrl = buildAuthorizationUrl(codeChallenge: codeChallenge)

        // Start web authentication session
        let session = ASWebAuthenticationSession(
            url: authUrl,
            callbackURLScheme: "myapp"
        ) { callbackUrl, error in
            if let error = error {
                completion(.failure(error))
                return
            }

            guard let callbackUrl = callbackUrl,
                  let code = self.extractAuthCode(from: callbackUrl) else {
                completion(.failure(AuthError.invalidCallback))
                return
            }

            // Exchange code for tokens
            self.exchangeCodeForTokens(
                code: code,
                codeVerifier: codeVerifier
            ) { result in
                completion(result)
            }
        }

        session.presentationContextProvider = self
        session.start()
    }

    private func generateCodeVerifier() -> String {
        var buffer = [UInt8](repeating: 0, count: 32)
        _ = SecRandomCopyBytes(kSecRandomDefault, buffer.count, &buffer)
        return Data(buffer).base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
    }

    private func generateCodeChallenge(from verifier: String) -> String {
        guard let data = verifier.data(using: .utf8) else {
            fatalError("Failed to encode verifier")
        }
        var buffer = [UInt8](repeating: 0, count: Int(CC_SHA256_DIGEST_LENGTH))
        data.withUnsafeBytes {
            _ = CC_SHA256($0.baseAddress, CC_LONG(data.count), &buffer)
        }
        return Data(buffer).base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
    }

    private func buildAuthorizationUrl(codeChallenge: String) -> URL {
        var components = URLComponents(string: "https://\(ssoStartUrl)/authorize")!
        components.queryItems = [
            URLQueryItem(name: "client_id", value: clientId),
            URLQueryItem(name: "response_type", value: "code"),
            URLQueryItem(name: "redirect_uri", value: redirectUri),
            URLQueryItem(name: "scope", value: "openid profile email"),
            URLQueryItem(name: "code_challenge", value: codeChallenge),
            URLQueryItem(name: "code_challenge_method", value: "S256")
        ]
        return components.url!
    }

    func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        return ASPresentationAnchor()
    }
}
```

---

## Configuration Checklist

### For Each Client Type

- [ ] Register application in IAM Identity Center
- [ ] Configure appropriate OAuth2 flow (authorization code, device, client credentials)
- [ ] Set up redirect URIs for web/mobile clients
- [ ] Implement token storage (secure, encrypted)
- [ ] Implement token refresh logic
- [ ] Handle token expiration gracefully
- [ ] Exchange tokens for AWS credentials
- [ ] Implement proper error handling
- [ ] Add logout functionality
- [ ] Test authentication flow end-to-end

---

## Security Considerations

### Token Management

1. **Storage:**
   - **Web:** Secure HTTP-only cookies
   - **Mobile:** iOS Keychain / Android KeyStore
   - **CLI:** Encrypted file with proper permissions
   - **Never:** LocalStorage, SessionStorage for sensitive tokens

2. **Transmission:**
   - Always use HTTPS
   - Use Authorization header: `Bearer <token>`
   - Never include tokens in URLs

3. **Expiration:**
   - Access tokens: Short-lived (1 hour)
   - Refresh tokens: Long-lived (days/weeks)
   - AWS credentials: 12 hours (configured)
   - Always implement refresh logic

### PKCE for Public Clients

PKCE prevents authorization code interception attacks:

```
flow without PKCE:
Authorization Code → Anyone can intercept → Get tokens

flow with PKCE:
Authorization Code + Code Verifier → Only legitimate client has verifier → Get tokens
```

Always use PKCE for:
- Mobile apps
- Single Page Applications (SPAs)
- Desktop applications
- Any public client

---

## Testing

### Test Web Application Flow

```bash
# 1. Start authentication
curl -v "https://d-9066117351.awsapps.com/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=http://localhost:3000/callback&scope=openid"

# 2. After redirect, exchange code for token
curl -X POST "https://oidc.us-east-1.amazonaws.com/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "client_id=YOUR_CLIENT_ID" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "code=AUTHORIZATION_CODE" \
  -d "redirect_uri=http://localhost:3000/callback"

# 3. Use access token to get AWS credentials
aws sso get-role-credentials \
  --role-name "CCA-CLI-Access" \
  --account-id "211050572089" \
  --access-token "ACCESS_TOKEN_FROM_STEP_2"
```

### Test Client Credentials Flow

```bash
# Get token
TOKEN=$(curl -s -X POST "https://oidc.us-east-1.amazonaws.com/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=${CLIENT_ID}" \
  -d "client_secret=${CLIENT_SECRET}" \
  -d "scope=openid" | jq -r '.access_token')

# Use token
aws sso get-role-credentials \
  --role-name "CCA-CLI-Access" \
  --account-id "211050572089" \
  --access-token "$TOKEN"
```

---

## Comparison: CLI vs REST API Authentication

| Aspect | CLI (Current) | REST API (Extended) |
|--------|---------------|---------------------|
| **Flow** | Device Code | Various (Auth Code, Client Creds, etc.) |
| **User Interaction** | Browser opens automatically | Depends on client type |
| **Token Storage** | Local file (~/.ccc/) | Session/Keychain/Database |
| **Token Duration** | 12 hours (AWS credentials) | Configurable (access + refresh) |
| **Infrastructure** | Same (IAM Identity Center) | Same (IAM Identity Center) |
| **Additional Setup** | None | Register application client |
| **Use Cases** | CLI tools, IoT devices | Web apps, mobile apps, services |
| **Security** | High (PKCE-like) | Very High (multiple options) |

---

## Summary

✅ **Yes, CCA can authenticate REST API clients** using the same IAM Identity Center infrastructure

✅ **No additional AWS resources needed** - uses existing Identity Center, Permission Sets, and Groups

✅ **Multiple client types supported:**
- Web applications (Authorization Code flow)
- Mobile apps (Authorization Code + PKCE flow)
- Backend services (Client Credentials flow)
- CLI tools (Device Code flow - already implemented)

✅ **Same security model:**
- Users authenticate via Identity Center
- Get temporary AWS credentials
- No console access
- 12-hour sessions

✅ **Flexible and scalable:**
- Add new clients without infrastructure changes
- Centralized user management
- Consistent security policies

---

**Next Steps:**

1. Identify client types needing authentication
2. Register application clients in Identity Center
3. Implement appropriate OAuth2 flow for each client
4. Test authentication and AWS credential exchange
5. Deploy and monitor

---

**Document Version:** 1.0
**Maintained By:** CCA Project Team
