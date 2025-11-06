# Cloud CLI Access (CCA)

**Secure, self-service CLI authentication framework using AWS IAM Identity Center**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![AWS](https://img.shields.io/badge/AWS-IAM%20Identity%20Center-orange.svg)](https://aws.amazon.com/iam/identity-center/)

---

## Overview

Cloud CLI Access (CCA) is a **simplified, cost-effective authentication framework** for CLI tools using AWS IAM Identity Center. It provides:

✅ **Self-Service Registration** - Users register via a simple web form
✅ **Admin Approval Workflow** - One-click email approval/denial
✅ **CLI Authentication** - Browser-based OAuth device flow
✅ **Minimal Infrastructure** - Only 3 AWS services required
✅ **No Database** - State managed with JWT tokens
✅ **Console Access Blocked** - CLI/API only by default
✅ **Cost Effective** - ~$0.01-0.31/month

### Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   User      │────►│  S3 + Form   │────►│  Lambda         │
│   Browser   │     │  Registration│     │  (Approval)     │
└─────────────┘     └──────────────┘     └────────┬────────┘
                                                   │
                                                   ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  CCC CLI    │◄───►│  IAM Identity│◄────│  Admin Email    │
│  Tool       │     │  Center      │     │  Approve/Deny   │
└──────┬──────┘     └──────┬───────┘     └─────────────────┘
       │                   │
       ▼                   ▼
┌─────────────────────────────────┐
│      AWS Services (S3, EC2...)  │
└─────────────────────────────────┘
```

---

## Features

### User Experience
- **Self-Service Registration**: Simple web form, no admin involvement needed upfront
- **Email-Based Approval**: Admin receives email with approve/deny links
- **Automatic Password Setup**: IAM Identity Center sends password setup email after approval
- **Browser-Based Login**: CCC CLI opens browser, user authenticates, gets 12-hour credentials
- **No Console Access**: Users get CLI/API access only, no AWS Console access

### Administrator Experience
- **One-Click Deployment**: Complete setup in ~30 minutes
- **Minimal Maintenance**: No database, no complex infrastructure
- **Email Notifications**: All approval requests via email
- **Centralized Management**: IAM Identity Center for user management
- **Audit Trail**: All access tracked through CloudTrail

### Technical Features
- **3 AWS Services**: Identity Center + Lambda + S3 (no DynamoDB, API Gateway, or SNS)
- **JWT State Management**: No database required
- **Lambda Function URLs**: No API Gateway needed
- **Direct SES Integration**: No SNS topic required
- **PowerUserAccess**: Configurable permissions via permission sets

---

## Quick Start

### For End Users

1. **Register** at your organization's registration portal
2. **Wait for approval** email from administrator
3. **Set password** using link from IAM Identity Center
4. **Install CCC CLI:**
   ```bash
   git clone https://github.com/YOUR_ORG/cloud-cli-access.git
   cd cloud-cli-access/ccc-cli
   pip3 install -e .
   ```
5. **Configure:**
   ```bash
   ccc configure
   ```
6. **Login:**
   ```bash
   ccc login
   ```
7. **Use AWS:**
   ```bash
   ccc test
   aws s3 ls
   ```

### For Administrators

See [CCA - Cloud CLI Access - Implementation Guide](./docs/CCA%20-%20%20Cloud%20CLI%20Access%20-%20Implementation%20Guide.md) for complete deployment instructions.

**Quick deployment checklist:**
- [ ] Enable IAM Identity Center
- [ ] Deploy Lambda function
- [ ] Create S3 bucket with registration form
- [ ] Verify SES email
- [ ] Configure IAM permission sets
- [ ] Test registration and approval workflow

---

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git
- AWS IAM Identity Center access (provided by administrator)

### Install CCC CLI

```bash
# Clone repository
git clone https://github.com/YOUR_ORG/cloud-cli-access.git
cd cloud-cli-access/ccc-cli

# Install
pip3 install -r requirements.txt
pip3 install -e .

# Verify
ccc --version
```

See [INSTALL.md](./INSTALL.md) for detailed installation instructions.

---

## Usage

### Basic Commands

```bash
# Configure (one-time setup)
ccc configure \
  --sso-start-url "https://d-xxxxxxxxxx.awsapps.com/start" \
  --sso-region "us-east-1" \
  --account-id "123456789012" \
  --role-name "CCA-CLI-Access"

# Login
ccc login

# Check status
ccc status

# Test AWS access
ccc test

# Logout
ccc logout
```

### Example Workflow

```bash
# First-time setup
$ ccc configure
SSO start URL: https://d-xxxxxxxxxx.awsapps.com/start
AWS Account ID: 123456789012
✅ Configuration saved

# Authenticate
$ ccc login
🔐 Initiating Cloud CLI Access authentication...
Opening browser for authentication...
✅ Authentication successful!
💾 Credentials cached successfully

# Verify access
$ ccc status
Authentication Status:
  Status: ✓ Authenticated
  Account ID: 123456789012
  Expires: 2025-11-07 08:30:15 UTC
  Time Remaining: 11h 45m

# Test AWS APIs
$ ccc test
🧪 Testing Cloud CLI Access credentials...
Test 1: STS GetCallerIdentity ✓ Success
Test 2: S3 ListBuckets ✓ Success
Test 3: EC2 DescribeRegions ✓ Success
✅ All tests completed
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [INSTALL.md](./INSTALL.md) | Installation guide |
| [CCA - Cloud CLI Access - Implementation Guide](./docs/CCA%20-%20%20Cloud%20CLI%20Access%20-%20Implementation%20Guide.md) | Complete deployment guide |
| [CCA - Deployment Summary](./docs/CCA%20-%20Deployment%20Summary.md) | Deployment summary and configuration |
| [TEST-RESULTS.md](./docs/TEST-RESULTS.md) | End-to-end test results |
| [Addendum - AWS Resources Inventory](./docs/Addendum%20-%20AWS%20Resources%20Inventory.md) | Complete resource inventory |
| [Addendum - User Management Guide](./docs/Addendum%20-%20User%20Management%20Guide.md) | User management and administration |
| [Addendum - Console Navigation Guide](./docs/Addendum%20-%20Console%20Navigation%20Guide.md) | AWS Console troubleshooting |
| [Addendum - REST API Authentication.md](./docs/Addendum%20-%20REST%20API%20Authentication.md) | REST API client integration |
| [Addendum - Github Actions Integration.md](./docs/Addendum%20-%20Github%20Actions%20Integration.md) | CI/CD with GitHub Actions |
| [Addendum - Custom Domain Setup.md](./docs/Addendum%20-%20Custom%20Domain%20Setup.md) | Custom domain configuration |

---

## Project Structure

```
cloud-cli-access/
├── README.md                     # This file
├── INSTALL.md                    # Installation guide
├── LICENSE                       # MIT License
├── docs/                         # Documentation
│   ├── CCA -  Cloud CLI Access - Implementation Guide.md  # Full deployment guide
│   ├── CCA - Deployment Summary.md
│   ├── TEST-RESULTS.md          # End-to-end test results
│   ├── Addendum - AWS Resources Inventory.md
│   ├── Addendum - User Management Guide.md
│   ├── Addendum - Console Navigation Guide.md
│   ├── Addendum - REST API Authentication.md
│   ├── Addendum - Github Actions Integration.md
│   └── Addendum - Custom Domain Setup.md
├── ccc-cli/                      # CCC CLI tool
│   ├── ccc/                      # Python package
│   │   ├── __init__.py
│   │   ├── __main__.py
│   │   ├── auth.py              # Authentication module
│   │   ├── cli.py               # CLI commands
│   │   └── config.py            # Configuration management
│   ├── requirements.txt
│   └── setup.py
├── lambda/                       # Lambda function
│   ├── lambda_function.py       # Registration/approval handler
│   └── lambda_function.zip      # Deployment package
└── tmp/                          # Build artifacts and configs
    ├── registration.html        # Self-service registration form
    ├── cca-config.env           # Environment configuration
    └── *.json                   # AWS resource configurations
```

---

## AWS Infrastructure

### Resources Deployed

| Service | Resource | Purpose |
|---------|----------|---------|
| **IAM Identity Center** | 1 Instance | User authentication |
| | 1 Permission Set | CLI-only access permissions |
| | 1 Group | CCA-CLI-Users group |
| **Lambda** | 1 Function | Registration/approval workflow |
| | 1 Function URL | Public HTTPS endpoint |
| **S3** | 1 Bucket | Static website hosting |
| | 1 Object | registration.html |
| **IAM** | 1 Role | Lambda execution role |
| **SES** | 1 Email Identity | Notification emails |

**Total:** 9 resources across 5 AWS services

### Cost Estimate

**Low usage (~10 users/month):** ~$0.01/month
**Medium usage (~100 users/month):** ~$0.10/month
**High usage (~1000 users/month):** ~$0.31/month

All services use free tier or minimal usage pricing.

---

## Security

### Authentication & Authorization
- ✅ IAM Identity Center native authentication
- ✅ OAuth2 device flow (industry standard)
- ✅ JWT-signed approval tokens (7-day expiration)
- ✅ Short-lived credentials (12 hours)
- ✅ Console access explicitly denied
- ✅ Admin approval required for all users

### Data Protection
- ✅ Credentials cached locally with 0600 permissions
- ✅ HTTPS for all communication
- ✅ No passwords stored in Lambda
- ✅ JWT secret key in environment variables
- ✅ CloudTrail logging for audit

### Network Security
- ✅ Lambda Function URL with CORS
- ✅ S3 bucket public read only (single HTML file)
- ✅ SES email verification required
- ✅ No database to secure
- ✅ Minimal attack surface

---

## Use Cases

### Supported Scenarios

1. **CLI Tools** - Current implementation (Device Code flow)
2. **REST API Clients** - See REST API Authentication guide
3. **Web Applications** - Authorization Code flow
4. **Mobile Apps** - Authorization Code + PKCE flow
5. **CI/CD Pipelines** - GitHub Actions, GitLab CI, etc.
6. **Backend Services** - Client Credentials flow

### Who Should Use CCA?

✅ **Good fit:**
- Organizations needing CLI access without AWS Console
- Teams wanting self-service user registration
- Companies seeking minimal infrastructure overhead
- Projects requiring centralized access management
- Organizations with IAM Identity Center already deployed

❌ **Not ideal for:**
- Console access requirements (use Identity Center directly)
- Sub-second authentication needs (12-hour credential duration)
- Offline access requirements (needs internet for authentication)

---

## Advanced Topics

### REST API Authentication

CCA can authenticate REST API clients using the same infrastructure. See [Addendum - REST API Authentication.md](./docs/Addendum%20-%20REST%20API%20Authentication.md).

**Supported flows:**
- Authorization Code (web apps)
- Authorization Code + PKCE (mobile/SPA)
- Client Credentials (service-to-service)
- Device Code (CLI tools - already implemented)

### GitHub Actions Integration

Run CCC CLI from GitHub Actions for CI/CD workflows. See [Addendum - Github Actions Integration.md](./docs/Addendum%20-%20Github%20Actions%20Integration.md).

**Three options:**
1. **OIDC Federation** (Recommended - no credentials)
2. **Service Account** (Simple - uses secrets)
3. **Self-Hosted Runner** (Most flexible)

### Custom Domains

Configure custom domains for professional branding. See [Addendum - Custom Domain Setup.md](./docs/Addendum%20-%20Custom%20Domain%20Setup.md).

**Examples:**
- Registration: `https://register.example.com`
- SSO Portal: `https://sso.example.com`

**Cost:** ~$2-3/month additional

---

## Troubleshooting

### Common Issues

**Issue: `ccc: command not found`**
```bash
# Add to PATH
export PATH="$HOME/.local/bin:$PATH"
```

**Issue: Login fails**
```bash
# Check configuration
ccc status

# Reconfigure
ccc configure
```

**Issue: Credentials expired**
```bash
# Re-authenticate
ccc login
```

**Issue: Permission denied**
```bash
# Contact administrator to verify:
# - User is in CCA-CLI-Users group
# - Permission set is assigned
# - Account assignment is provisioned
```

See [INSTALL.md](./INSTALL.md) for more troubleshooting steps.

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/cloud-cli-access.git
cd cloud-cli-access

# Install in development mode
cd ccc-cli
pip3 install -e .

# Make changes and test
ccc --version
```

---

## Roadmap

### Planned Features

- [ ] PyPI package distribution
- [ ] AWS credential process integration
- [ ] Multi-account support
- [ ] MFA enforcement options
- [ ] Custom permission set templates
- [ ] Terraform/CloudFormation templates
- [ ] Docker containerization
- [ ] Session recording and audit logs
- [ ] Slack/Teams integration for approvals

### Future Enhancements

- AWS Organizations integration
- SCIM provisioning support
- Custom authentication flows
- Advanced monitoring dashboard
- Automated user lifecycle management

---

## FAQ

**Q: Do users get AWS Console access?**
A: No. By default, users get CLI/API access only. Console access is explicitly denied.

**Q: How long do credentials last?**
A: 12 hours. This is configurable by the administrator via IAM Identity Center.

**Q: Can I use this with multiple AWS accounts?**
A: Currently supports single account. Multi-account support is on the roadmap.

**Q: Do I need a database?**
A: No. CCA uses JWT tokens for state management.

**Q: What happens if a user forgets their password?**
A: IAM Identity Center handles password resets. Users can reset via the SSO portal.

**Q: Can I customize the registration form?**
A: Yes. Edit `tmp/registration.html` and redeploy to S3.

**Q: Is MFA supported?**
A: Yes, but must be configured in IAM Identity Center settings (not CCA-specific).

**Q: Can I use my own domain?**
A: Yes. See [Addendum - Custom Domain Setup.md](./docs/Addendum%20-%20Custom%20Domain%20Setup.md).

---

## Support

- **Documentation:** See `/docs` directory
- **Issues:** [GitHub Issues](https://github.com/YOUR_ORG/cloud-cli-access/issues)
- **Discussions:** [GitHub Discussions](https://github.com/YOUR_ORG/cloud-cli-access/discussions)

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- Built with [AWS IAM Identity Center](https://aws.amazon.com/iam/identity-center/)
- CLI framework powered by [Click](https://click.palletsprojects.com/)
- AWS SDK: [Boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)

---

## Authors

- **CCA Project Team**

---

**Cloud CLI Access - Simplified, Secure, Self-Service** ✨

---

## Quick Links

- [Installation Guide](./INSTALL.md)
- [Deployment Guide](./docs/CCA%20-%20%20Cloud%20CLI%20Access%20-%20Implementation%20Guide.md)
- [Test Results](./docs/TEST-RESULTS.md)
- [AWS Resources](./docs/Addendum%20-%20AWS%20Resources%20Inventory.md)
- [User Management](./docs/Addendum%20-%20User%20Management%20Guide.md)
- [Console Navigation](./docs/Addendum%20-%20Console%20Navigation%20Guide.md)
- [REST API Guide](./docs/Addendum%20-%20REST%20API%20Authentication.md)
- [GitHub Actions](./docs/Addendum%20-%20Github%20Actions%20Integration.md)
- [Custom Domains](./docs/Addendum%20-%20Custom%20Domain%20Setup.md)
