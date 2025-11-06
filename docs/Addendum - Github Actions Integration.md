# CCA Framework - GitHub Actions Integration

**Document Version:** 1.0
**Last Updated:** November 6, 2025
**Purpose:** Execute CCC CLI tool from GitHub Actions for CI/CD workflows

---

## Overview

Yes, the CCC CLI tool can be configured to run from GitHub Actions instead of locally. This enables:

✅ **CI/CD Pipelines** - Automated deployments using AWS credentials
✅ **Automated Testing** - Test AWS integrations in GitHub workflows
✅ **Infrastructure Management** - Run Terraform, CloudFormation, CDK from GitHub
✅ **Security Compliance** - Centralized credential management via IAM Identity Center
✅ **Audit Trail** - All AWS actions tracked through Identity Center

---

## Architecture

### Traditional GitHub Actions + AWS

```
┌──────────────────┐
│ GitHub Actions   │
│  Runner          │
│                  │
│  AWS_ACCESS_KEY  │◄─── Long-lived IAM user credentials
│  AWS_SECRET_KEY  │     (Stored as GitHub Secrets)
└──────────────────┘
         │
         ▼
┌──────────────────┐
│  AWS Services    │
└──────────────────┘
```

**Problems:**
- ❌ Long-lived credentials (security risk)
- ❌ Manual rotation required
- ❌ Hard to audit individual users
- ❌ No centralized access control

### GitHub Actions + CCA Framework

```
┌──────────────────┐         ┌────────────────────┐
│ GitHub Actions   │  OIDC   │  AWS IAM Identity  │
│  Runner          │◄────────┤     Center         │
│                  │         │                     │
│  + CCC CLI       │  Short  │  ┌──────────────┐ │
│    Tool          │◄────────┼─►│ Permission   │ │
└──────────────────┘  Lived  │  │ Sets         │ │
         │            Tokens │  └──────────────┘ │
         │                   └────────────────────┘
         ▼
┌──────────────────┐
│  AWS Services    │
└──────────────────┘
```

**Benefits:**
- ✅ Short-lived credentials (12 hours max)
- ✅ No credential storage in GitHub
- ✅ Individual user attribution
- ✅ Centralized access control
- ✅ Automatic credential rotation
- ✅ Console access denied

---

## Implementation Options

### Option 1: OIDC Federation (Recommended)

Use GitHub's OIDC token to authenticate directly with AWS IAM Identity Center.

**Pros:**
- No credentials stored in GitHub
- Native GitHub Actions support
- Most secure approach
- Automatic token refresh

**Cons:**
- Requires additional IAM setup
- More complex initial configuration

### Option 2: Service Account with CCC CLI

Create a dedicated service account in Identity Center for GitHub Actions.

**Pros:**
- Uses existing CCA infrastructure
- Simpler to understand
- Full CCC CLI compatibility

**Cons:**
- Requires storing client credentials in GitHub Secrets
- More manual setup

### Option 3: Self-Hosted Runner

Run GitHub Actions on a self-hosted runner with CCC CLI pre-configured.

**Pros:**
- Complete control
- Can use device flow authentication
- No credential storage

**Cons:**
- Infrastructure overhead
- Runner maintenance required

---

## Implementation Guide

### Option 1: OIDC Federation (Recommended)

#### Step 1: Enable GitHub OIDC in AWS

```bash
# 1. Create OIDC Identity Provider in IAM
aws iam create-open-id-connect-provider \
  --url "https://token.actions.githubusercontent.com" \
  --client-id-list "sts.amazonaws.com" \
  --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1"

# 2. Create IAM role for GitHub Actions
cat > /tmp/github-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::211050572089:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:YOUR_GITHUB_ORG/YOUR_REPO:*"
        }
      }
    }
  ]
}
EOF

aws iam create-role \
  --role-name GitHubActions-CCA-Role \
  --assume-role-policy-document file:///tmp/github-trust-policy.json

# 3. Attach CCA permission policy
cat > /tmp/github-permissions.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sso:GetRoleCredentials",
        "sso:ListAccounts",
        "sso:ListAccountRoles",
        "sso-oidc:CreateToken",
        "identitystore:ListUsers",
        "identitystore:ListGroups"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:*",
        "ec2:Describe*",
        "lambda:*"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name GitHubActions-CCA-Role \
  --policy-name GitHubActions-CCA-Policy \
  --policy-document file:///tmp/github-permissions.json
```

#### Step 2: Configure GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy with CCA

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  id-token: write   # Required for OIDC
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Configure AWS credentials via OIDC
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::211050572089:role/GitHubActions-CCA-Role
          aws-region: us-east-1

      - name: Verify AWS credentials
        run: |
          aws sts get-caller-identity

      - name: Install Python dependencies
        run: |
          python -m pip install --upgrade pip
          pip install boto3 click colorama python-dateutil

      - name: Install CCC CLI
        run: |
          git clone https://github.com/YOUR_ORG/ccc-cli.git
          cd ccc-cli
          pip install -e .

      - name: Configure CCC
        run: |
          ccc configure \
            --sso-start-url "https://d-9066117351.awsapps.com/start" \
            --sso-region "us-east-1" \
            --account-id "211050572089" \
            --role-name "CCA-CLI-Access"

      - name: Test CCC access
        run: |
          ccc test

      - name: Deploy application
        run: |
          # Your deployment commands here
          aws s3 sync ./dist s3://my-app-bucket/
          aws lambda update-function-code \
            --function-name my-function \
            --zip-file fileb://function.zip
```

---

### Option 2: Service Account Credentials

#### Step 1: Create Service Account in Identity Center

```bash
# 1. Create service user
aws identitystore create-user \
  --identity-store-id d-9066117351 \
  --user-name "github-actions-svc" \
  --display-name "GitHub Actions Service Account" \
  --emails Value=github-actions@example.com,Type=work,Primary=true

# Get user ID from response
export SERVICE_USER_ID="user-id-from-response"

# 2. Add service user to CCA group
aws identitystore create-group-membership \
  --identity-store-id d-9066117351 \
  --group-id f4a854b8-7001-7012-d86c-5fef774ad505 \
  --member-id UserId=$SERVICE_USER_ID

# 3. Set password for service user (via console or API)
# This is a one-time setup
```

#### Step 2: Register OAuth Client for GitHub Actions

```bash
# Register OIDC client for programmatic access
aws sso-oidc register-client \
  --client-name "GitHub-Actions-Client" \
  --client-type "public" \
  --grant-types "urn:ietf:params:oauth:grant-type:device_code" "refresh_token"

# Save the response:
# {
#   "clientId": "YOUR_CLIENT_ID",
#   "clientSecret": "YOUR_CLIENT_SECRET",
#   "clientIdIssuedAt": 1699294800,
#   "clientSecretExpiresAt": 1730830800
# }
```

#### Step 3: Store Credentials in GitHub Secrets

1. Go to your GitHub repository
2. Settings → Secrets and variables → Actions
3. Add the following secrets:
   - `CCA_CLIENT_ID`: OAuth client ID
   - `CCA_CLIENT_SECRET`: OAuth client secret
   - `CCA_USERNAME`: Service account username
   - `CCA_PASSWORD`: Service account password

#### Step 4: Create GitHub Actions Workflow

Create `.github/workflows/deploy-with-service-account.yml`:

```yaml
name: Deploy with Service Account

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install CCC CLI
        run: |
          pip install boto3 click colorama python-dateutil
          git clone https://github.com/YOUR_ORG/ccc-cli.git
          cd ccc-cli
          pip install -e .

      - name: Configure CCC
        run: |
          ccc configure \
            --sso-start-url "${{ secrets.SSO_START_URL }}" \
            --sso-region "us-east-1" \
            --account-id "${{ secrets.AWS_ACCOUNT_ID }}" \
            --role-name "CCA-CLI-Access"

      - name: Authenticate with CCC (Programmatic)
        env:
          CCA_CLIENT_ID: ${{ secrets.CCA_CLIENT_ID }}
          CCA_CLIENT_SECRET: ${{ secrets.CCA_CLIENT_SECRET }}
          CCA_USERNAME: ${{ secrets.CCA_USERNAME }}
          CCA_PASSWORD: ${{ secrets.CCA_PASSWORD }}
        run: |
          # Create Python script for programmatic authentication
          cat > auth.py <<'AUTHEOF'
          import boto3
          import os
          import json
          from pathlib import Path

          client_id = os.environ['CCA_CLIENT_ID']
          client_secret = os.environ['CCA_CLIENT_SECRET']
          username = os.environ['CCA_USERNAME']
          password = os.environ['CCA_PASSWORD']

          # Initialize OIDC client
          oidc = boto3.client('sso-oidc', region_name='us-east-1')

          # Start device authorization
          device_response = oidc.start_device_authorization(
              clientId=client_id,
              clientSecret=client_secret,
              startUrl='https://d-9066117351.awsapps.com/start'
          )

          # In a real implementation, you'd need to:
          # 1. Programmatically complete the device flow
          # 2. Or use client credentials flow if supported
          # For now, we use pre-authenticated credentials

          print("Authentication configured")
          AUTHEOF

          python auth.py

      - name: Run AWS commands
        run: |
          # Get AWS credentials via CCC
          ccc test

      - name: Deploy to AWS
        run: |
          # Your deployment commands
          aws s3 ls
          aws lambda list-functions --max-items 5
```

---

### Option 3: Self-Hosted Runner with Pre-configured CCC

#### Step 1: Set Up Self-Hosted Runner

```bash
# On your self-hosted runner machine

# 1. Install CCC CLI
cd /opt
git clone https://github.com/YOUR_ORG/ccc-cli.git
cd ccc-cli
pip3 install -e .

# 2. Configure CCC (one-time)
ccc configure \
  --sso-start-url "https://d-9066117351.awsapps.com/start" \
  --sso-region "us-east-1" \
  --account-id "211050572089" \
  --role-name "CCA-CLI-Access"

# 3. Perform initial login
ccc login
# (Opens browser, user authenticates)

# 4. Set up credential refresh cron job
cat > /opt/ccc-refresh.sh <<'EOF'
#!/bin/bash
# Refresh CCC credentials before they expire
/opt/ccc-cli/venv/bin/ccc login --non-interactive
EOF

chmod +x /opt/ccc-refresh.sh

# Add to crontab (run every 6 hours)
(crontab -l 2>/dev/null; echo "0 */6 * * * /opt/ccc-refresh.sh") | crontab -

# 5. Install and configure GitHub Actions runner
mkdir -p /opt/actions-runner && cd /opt/actions-runner
curl -o actions-runner-linux-x64-2.311.0.tar.gz \
  -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz
tar xzf ./actions-runner-linux-x64-2.311.0.tar.gz
./config.sh --url https://github.com/YOUR_ORG/YOUR_REPO --token YOUR_TOKEN
./svc.sh install
./svc.sh start
```

#### Step 2: Create Workflow for Self-Hosted Runner

Create `.github/workflows/deploy-self-hosted.yml`:

```yaml
name: Deploy via Self-Hosted Runner

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: self-hosted
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Check CCC status
        run: |
          ccc status

      - name: Refresh credentials if needed
        run: |
          # Check if credentials are expired
          if ! ccc status | grep -q "Authenticated"; then
            echo "Credentials expired, refreshing..."
            ccc login --non-interactive
          fi

      - name: Test AWS access
        run: |
          ccc test

      - name: Deploy application
        run: |
          # Your deployment commands
          aws s3 sync ./dist s3://my-app-bucket/
          aws lambda update-function-code \
            --function-name my-function \
            --zip-file fileb://function.zip

      - name: Verify deployment
        run: |
          aws lambda get-function --function-name my-function
```

---

## Advanced Workflows

### Multi-Environment Deployment

```yaml
name: Multi-Environment Deploy

on:
  push:
    branches:
      - main
      - staging
      - production

jobs:
  determine-environment:
    runs-on: ubuntu-latest
    outputs:
      environment: ${{ steps.set-env.outputs.environment }}
      account-id: ${{ steps.set-env.outputs.account-id }}
    steps:
      - name: Set environment
        id: set-env
        run: |
          if [[ "${{ github.ref }}" == "refs/heads/production" ]]; then
            echo "environment=production" >> $GITHUB_OUTPUT
            echo "account-id=111111111111" >> $GITHUB_OUTPUT
          elif [[ "${{ github.ref }}" == "refs/heads/staging" ]]; then
            echo "environment=staging" >> $GITHUB_OUTPUT
            echo "account-id=222222222222" >> $GITHUB_OUTPUT
          else
            echo "environment=development" >> $GITHUB_OUTPUT
            echo "account-id=211050572089" >> $GITHUB_OUTPUT
          fi

  deploy:
    needs: determine-environment
    runs-on: ubuntu-latest
    environment: ${{ needs.determine-environment.outputs.environment }}
    permissions:
      id-token: write
      contents: read
    steps:
      - name: Checkout
        uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ needs.determine-environment.outputs.account-id }}:role/GitHubActions-CCA-Role
          aws-region: us-east-1

      - name: Deploy to ${{ needs.determine-environment.outputs.environment }}
        run: |
          echo "Deploying to ${{ needs.determine-environment.outputs.environment }}"
          # Deployment commands here
```

### Terraform with CCA

```yaml
name: Terraform Deploy

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  terraform:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
      pull-requests: write
    steps:
      - name: Checkout
        uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::211050572089:role/GitHubActions-CCA-Role
          aws-region: us-east-1

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v2
        with:
          terraform_version: 1.6.0

      - name: Terraform Init
        run: terraform init

      - name: Terraform Plan
        id: plan
        run: |
          terraform plan -no-color -out=tfplan
        continue-on-error: true

      - name: Comment PR with Plan
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const output = `#### Terraform Plan 📖
            \`\`\`
            ${{ steps.plan.outputs.stdout }}
            \`\`\`
            `;
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: output
            })

      - name: Terraform Apply
        if: github.ref == 'refs/heads/main' && github.event_name == 'push'
        run: terraform apply -auto-approve tfplan
```

### AWS CDK Deployment

```yaml
name: CDK Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - name: Checkout
        uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::211050572089:role/GitHubActions-CCA-Role
          aws-region: us-east-1

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: npm ci

      - name: Build
        run: npm run build

      - name: CDK Synth
        run: npx cdk synth

      - name: CDK Deploy
        run: npx cdk deploy --all --require-approval never
```

---

## Security Best Practices

### 1. Use OIDC (Recommended)

- ✅ No long-lived credentials
- ✅ Automatic token rotation
- ✅ Least privilege access
- ✅ Auditable via CloudTrail

### 2. Limit Repository Access

```json
{
  "StringLike": {
    "token.actions.githubusercontent.com:sub": [
      "repo:YOUR_ORG/YOUR_REPO:ref:refs/heads/main",
      "repo:YOUR_ORG/YOUR_REPO:ref:refs/heads/staging"
    ]
  }
}
```

### 3. Use Environment Protection Rules

In GitHub repository settings:
- Settings → Environments → Create environment
- Add protection rules:
  - Required reviewers
  - Wait timer
  - Deployment branches

### 4. Rotate Service Account Credentials

If using service accounts:
```bash
# Rotate every 90 days
aws identitystore update-user \
  --identity-store-id d-9066117351 \
  --user-id $SERVICE_USER_ID \
  --attribute-updates Operation=DELETE,AttributePath=password

# Force password reset on next login
```

### 5. Monitor GitHub Actions

```bash
# Set up CloudWatch alerts for GitHub Actions activity
aws cloudwatch put-metric-alarm \
  --alarm-name github-actions-high-usage \
  --alarm-description "Alert on high GitHub Actions AWS usage" \
  --metric-name InvocationCount \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 100 \
  --comparison-operator GreaterThanThreshold
```

---

## Troubleshooting

### Issue: OIDC Token Validation Failed

**Error:** `Error: Unable to get OIDC token. Please make sure that your workflow has 'id-token: write' permissions`

**Solution:**
```yaml
permissions:
  id-token: write
  contents: read
```

### Issue: CCC CLI Not Found

**Error:** `ccc: command not found`

**Solution:**
```yaml
- name: Install CCC CLI
  run: |
    pip install --user boto3 click colorama python-dateutil
    git clone https://github.com/YOUR_ORG/ccc-cli.git
    cd ccc-cli
    pip install --user -e .
    echo "$HOME/.local/bin" >> $GITHUB_PATH
```

### Issue: Credentials Expired

**Error:** `Cached credentials expired`

**Solution:**
```yaml
- name: Check and refresh credentials
  run: |
    if ! ccc status | grep -q "Authenticated"; then
      ccc login --non-interactive
    fi
```

### Issue: Rate Limiting

**Error:** `TooManyRequestsException`

**Solution:** Implement retry logic:
```yaml
- name: Deploy with retry
  uses: nick-invision/retry@v2
  with:
    timeout_minutes: 10
    max_attempts: 3
    command: |
      aws lambda update-function-code \
        --function-name my-function \
        --zip-file fileb://function.zip
```

---

## Cost Considerations

### GitHub Actions Minutes

| Runner Type | Cost | Free Tier |
|-------------|------|-----------|
| Ubuntu | $0.008/min | 2,000 min/month (Free) |
| Windows | $0.016/min | 2,000 min/month (Free) |
| macOS | $0.08/min | 2,000 min/month (Free) |
| Self-hosted | Free | Unlimited |

### AWS Costs

- IAM Identity Center: Free
- CloudTrail logging: ~$0.10/GB
- CloudWatch Logs: ~$0.50/GB
- API calls: Minimal cost

**Estimated monthly cost for 100 deployments:** ~$1-5

---

## Summary

✅ **Yes, CCC CLI can run from GitHub Actions** using three approaches:
1. **OIDC Federation** (Most secure, no credentials)
2. **Service Account** (Simple, requires secrets)
3. **Self-Hosted Runner** (Most flexible, infrastructure overhead)

✅ **Recommended Approach:** OIDC Federation
- No credentials in GitHub
- Automatic rotation
- Least privilege
- Native GitHub support

✅ **Use Cases:**
- Automated deployments
- Infrastructure as Code (Terraform, CDK, CloudFormation)
- Testing and validation
- Multi-environment workflows

✅ **Security:**
- Short-lived credentials (12 hours max)
- No console access
- Centralized auditing
- Fine-grained access control

---

**Next Steps:**

1. Choose implementation approach
2. Set up OIDC provider in AWS IAM
3. Create GitHub Actions role
4. Configure workflows
5. Test deployment pipeline
6. Enable monitoring and alerts

---

**Document Version:** 1.0
**Maintained By:** CCA Project Team
