# CCA Project - AWS Resources Inventory

**Project:** Cloud CLI Access (CCA)
**Account ID:** 211050572089
**Region:** us-east-1
**Deployment Date:** November 6, 2025

---

## Resource Summary

| Service | Resource Count | Purpose |
|---------|----------------|---------|
| IAM Identity Center | 1 instance, 1 group, 1 permission set | User authentication and authorization |
| Lambda | 1 function | Registration and approval workflow |
| S3 | 1 bucket | Static website hosting (registration form) |
| IAM | 1 role, 1 policy | Lambda execution permissions |
| SES | 1 verified identity | Email notifications |

**Total Resource Types:** 5 AWS Services
**Total Individual Resources:** 9 Resources

---

## Detailed Resource Inventory

### 1. IAM Identity Center Resources

#### 1.1 Identity Center Instance
- **Resource Type:** AWS SSO Instance
- **Instance ARN:** `arn:aws:sso:::instance/ssoins-72232e1b5b84475a`
- **Identity Store ID:** `d-9066117351`
- **Owner Account:** 211050572089
- **Region:** us-east-1
- **Status:** ACTIVE
- **Access Portal URL:** https://d-9066117351.awsapps.com/start
- **Purpose:** Central authentication service for CLI access
- **Created:** November 6, 2025
- **Taggable:** No (AWS-managed resource)

#### 1.2 Permission Set
- **Resource Type:** Permission Set
- **Name:** CCA-CLI-Access
- **ARN:** `arn:aws:sso:::permissionSet/ssoins-72232e1b5b84475a/ps-722336e927a8f2d5`
- **Description:** Cloud CLI Access - API only, no console
- **Session Duration:** PT12H (12 hours)
- **Managed Policies:**
  - `arn:aws:iam::aws:policy/PowerUserAccess`
- **Inline Policy:** Console access denial policy (signin:*, console:*)
- **Purpose:** Grant PowerUserAccess without console access
- **Assigned To:** CCA-CLI-Users group
- **Target:** AWS Account 211050572089
- **Taggable:** Yes

#### 1.3 User Group
- **Resource Type:** Identity Store Group
- **Group Name:** CCA-CLI-Users
- **Group ID:** `f4a854b8-7001-7012-d86c-5fef774ad505`
- **Identity Store ID:** d-9066117351
- **Description:** Users with Cloud CLI Access
- **Purpose:** Manage users with CLI-only access
- **Members:** Dynamically added via Lambda function
- **Taggable:** No

#### 1.4 Account Assignment
- **Resource Type:** Account Assignment
- **Principal:** Group (CCA-CLI-Users)
- **Principal ID:** f4a854b8-7001-7012-d86c-5fef774ad505
- **Target:** AWS_ACCOUNT
- **Target ID:** 211050572089
- **Permission Set ARN:** arn:aws:sso:::permissionSet/ssoins-72232e1b5b84475a/ps-722336e927a8f2d5
- **Status:** Provisioned
- **Purpose:** Grant group members access to AWS account
- **Taggable:** No

---

### 2. Lambda Resources

#### 2.1 Lambda Function
- **Resource Type:** AWS Lambda Function
- **Function Name:** cca-registration
- **Function ARN:** `arn:aws:lambda:us-east-1:211050572089:function:cca-registration`
- **Runtime:** python3.11
- **Handler:** lambda_function.lambda_handler
- **Role ARN:** `arn:aws:iam::211050572089:role/CCA-Lambda-Role`
- **Memory:** 256 MB
- **Timeout:** 30 seconds
- **Code Size:** 4,579 bytes
- **Code SHA256:** tHaWCyOlNC40UQT+4razu7NQbNXVQcQDNSyifbXJdqE=
- **Last Modified:** 2025-11-06T20:58:30.201+0000
- **State:** Active
- **Package Type:** Zip
- **Architecture:** x86_64
- **Purpose:** Handle user registration, admin approval/denial, and Identity Center user creation
- **Log Group:** /aws/lambda/cca-registration
- **Taggable:** Yes

**Environment Variables:**
- IDENTITY_STORE_ID: d-9066117351
- CLI_GROUP_ID: f4a854b8-7001-7012-d86c-5fef774ad505
- SSO_START_URL: https://d-9066117351.awsapps.com/start
- ADMIN_EMAIL: info@2112-lab.com
- FROM_EMAIL: info@2112-lab.com
- SECRET_KEY: [REDACTED]

#### 2.2 Lambda Function URL
- **Resource Type:** Lambda Function URL Configuration
- **Function URL:** `https://kmfuod67kbaeombcknzrjbtrmi0qqncd.lambda-url.us-east-1.on.aws/`
- **Function ARN:** arn:aws:lambda:us-east-1:211050572089:function:cca-registration
- **Auth Type:** NONE (public access)
- **CORS Configuration:**
  - Allow Origins: *
  - Allow Methods: GET, POST
  - Allow Headers: *
- **Created:** 2025-11-06T20:58:52.172825133Z
- **Purpose:** Public HTTPS endpoint for registration form
- **Taggable:** No (part of function resource)

#### 2.3 Lambda Resource Policy
- **Resource Type:** Lambda Permission
- **Statement ID:** FunctionURLAllowPublicAccess
- **Effect:** Allow
- **Principal:** *
- **Action:** lambda:InvokeFunctionUrl
- **Resource:** arn:aws:lambda:us-east-1:211050572089:function:cca-registration
- **Condition:** FunctionUrlAuthType = NONE
- **Purpose:** Allow public invocation via Function URL
- **Taggable:** No (part of function resource)

---

### 3. IAM Resources

#### 3.1 IAM Role
- **Resource Type:** IAM Role
- **Role Name:** CCA-Lambda-Role
- **Role ARN:** `arn:aws:iam::211050572089:role/CCA-Lambda-Role`
- **Role ID:** AROATCI4YFE4S5GNCUXY7
- **Path:** /
- **Created:** 2025-11-06T20:48:17+00:00
- **Purpose:** Execution role for cca-registration Lambda function
- **Assume Role Policy:** Trust policy allowing lambda.amazonaws.com service
- **Attached Policies:**
  - Inline Policy: CCA-Lambda-Policy
- **Taggable:** Yes

**Trust Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "lambda.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

#### 3.2 IAM Role Inline Policy
- **Resource Type:** IAM Role Policy
- **Policy Name:** CCA-Lambda-Policy
- **Role Name:** CCA-Lambda-Role
- **Purpose:** Grant Lambda permissions for CloudWatch Logs, SES, and Identity Store
- **Taggable:** No (part of role resource)

**Policy Permissions:**
- **CloudWatch Logs:**
  - logs:CreateLogGroup
  - logs:CreateLogStream
  - logs:PutLogEvents
  - Resource: arn:aws:logs:*:*:*

- **SES:**
  - ses:SendEmail
  - ses:SendRawEmail
  - Resource: *

- **Identity Store:**
  - identitystore:CreateUser
  - identitystore:ListUsers
  - identitystore:CreateGroupMembership
  - Resource: *

---

### 4. S3 Resources

#### 4.1 S3 Bucket
- **Resource Type:** S3 Bucket
- **Bucket Name:** `cca-registration-1762463059`
- **Region:** us-east-1
- **ARN:** `arn:aws:s3:::cca-registration-1762463059`
- **Created:** November 6, 2025
- **Purpose:** Host static registration HTML form
- **Website Hosting:** Enabled
- **Website URL:** http://cca-registration-1762463059.s3-website-us-east-1.amazonaws.com
- **Index Document:** registration.html
- **Public Access:** Enabled (via bucket policy)
- **Versioning:** Disabled
- **Encryption:** Default (SSE-S3)
- **Taggable:** Yes

#### 4.2 S3 Bucket Policy
- **Resource Type:** S3 Bucket Policy
- **Bucket:** cca-registration-1762463059
- **Purpose:** Allow public read access to registration.html
- **Taggable:** No (part of bucket resource)

**Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicReadGetObject",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::cca-registration-1762463059/*"
  }]
}
```

#### 4.3 S3 Object
- **Resource Type:** S3 Object
- **Key:** registration.html
- **Bucket:** cca-registration-1762463059
- **Size:** 6,246 bytes (6.1 KB)
- **Content-Type:** text/html
- **Purpose:** Self-service user registration form
- **Public URL:** http://cca-registration-1762463059.s3-website-us-east-1.amazonaws.com/registration.html
- **Taggable:** Yes

---

### 5. SES Resources

#### 5.1 SES Email Identity
- **Resource Type:** SES Email Identity
- **Email Address:** info@2112-lab.com
- **ARN:** `arn:aws:ses:us-east-1:211050572089:identity/info@2112-lab.com`
- **Verification Status:** Success
- **Purpose:** Send registration approval emails and notifications
- **Used For:**
  - Admin approval request emails
  - User welcome emails
  - User denial notification emails
- **Taggable:** Yes

---

### 6. CloudWatch Logs Resources

#### 6.1 CloudWatch Log Group
- **Resource Type:** CloudWatch Logs Log Group
- **Log Group Name:** `/aws/lambda/cca-registration`
- **ARN:** `arn:aws:logs:us-east-1:211050572089:log-group:/aws/lambda/cca-registration`
- **Retention:** Never Expire (default)
- **Created:** Automatically by Lambda service
- **Purpose:** Store Lambda function execution logs
- **Taggable:** Yes

---

## Resource Dependencies

```
IAM Identity Center Instance
    └── Permission Set (CCA-CLI-Access)
        └── Account Assignment
            └── Group (CCA-CLI-Users)

IAM Role (CCA-Lambda-Role)
    └── IAM Policy (CCA-Lambda-Policy)
        └── Lambda Function (cca-registration)
            ├── Function URL
            └── Log Group (/aws/lambda/cca-registration)

S3 Bucket (cca-registration-1762463059)
    ├── Bucket Policy
    └── Object (registration.html)

SES Email Identity (info@2112-lab.com)
```

---

## Resource Costs

### Monthly Cost Estimate (Low Usage)

| Resource | Pricing Model | Estimated Cost |
|----------|--------------|----------------|
| IAM Identity Center | Free | $0.00 |
| Lambda | Free tier: 1M requests/month | $0.00 |
| Lambda Function URL | Free | $0.00 |
| S3 Bucket | $0.023/GB storage + requests | $0.01 |
| S3 Static Website | Included in S3 pricing | $0.00 |
| CloudWatch Logs | Free tier: 5GB/month | $0.00 |
| SES | Free tier: 62,000 emails/month | $0.00 |
| **Total Monthly Cost** | | **~$0.01** |

### Scaling Costs (1000 users/month)

| Resource | Usage | Estimated Cost |
|----------|-------|----------------|
| Lambda Invocations | ~3,000 requests | $0.20 |
| Lambda Duration | ~300 seconds total | $0.05 |
| S3 Requests | ~1,000 GET requests | $0.01 |
| SES | ~3,000 emails | $0.10 |
| **Total Monthly Cost** | | **~$0.36** |

---

## Security Considerations

### Resource-Level Security

1. **IAM Identity Center:**
   - Console access explicitly denied
   - MFA can be enforced at Identity Center level
   - Session duration limited to 12 hours

2. **Lambda Function:**
   - Environment variables stored encrypted at rest
   - Execution role follows least privilege principle
   - Function URL is public but validates JWT tokens

3. **S3 Bucket:**
   - Public read only for specific objects
   - No write access from public
   - Can be enhanced with CloudFront and WAF

4. **SES:**
   - Email address verification required
   - Sending rate limits enforced by AWS
   - Can be moved out of sandbox for higher limits

---

## Backup and Recovery

### Stateful Resources

1. **IAM Identity Center Users:**
   - Backed up: User data stored in AWS-managed Identity Store
   - Recovery: Manual recreation via console or API
   - Export: Use `aws identitystore list-users` for backup

2. **S3 Bucket:**
   - Backed up: registration.html stored in CCA/tmp/
   - Recovery: Re-upload from local copy
   - Versioning: Can be enabled for automatic backups

3. **Lambda Function:**
   - Backed up: Source code in CCA/lambda/
   - Recovery: Redeploy from local copy
   - Versions: Lambda versioning not enabled

### Resource Identifiers

All resource ARNs, IDs, and configuration stored in:
- `CCA/tmp/cca-config.env` (environment variables)
- `CCA/docs/cca-deployment-summary.md` (documentation)

---

## Maintenance Commands

### List All Resources

```bash
# IAM Identity Center
aws sso-admin list-instances
aws identitystore list-users --identity-store-id d-9066117351
aws identitystore list-groups --identity-store-id d-9066117351

# Lambda
aws lambda list-functions --query "Functions[?FunctionName=='cca-registration']"
aws lambda get-function-url-config --function-name cca-registration

# S3
aws s3 ls s3://cca-registration-1762463059
aws s3api get-bucket-website --bucket cca-registration-1762463059

# IAM
aws iam get-role --role-name CCA-Lambda-Role
aws iam get-role-policy --role-name CCA-Lambda-Role --policy-name CCA-Lambda-Policy

# SES
aws ses get-identity-verification-attributes --identities info@2112-lab.com

# CloudWatch Logs
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/cca-registration
```

### Monitor Resources

```bash
# Lambda metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=cca-registration \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum

# Lambda logs (real-time)
aws logs tail /aws/lambda/cca-registration --follow

# S3 bucket size
aws cloudwatch get-metric-statistics \
  --namespace AWS/S3 \
  --metric-name BucketSizeBytes \
  --dimensions Name=BucketName,Value=cca-registration-1762463059,Name=StorageType,Value=StandardStorage \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Average
```

---

## Cleanup Commands

**WARNING:** These commands will permanently delete all CCA resources.

```bash
# 1. Delete Lambda function and Function URL
aws lambda delete-function-url-config --function-name cca-registration
aws lambda delete-function --function-name cca-registration

# 2. Delete S3 bucket and contents
aws s3 rm s3://cca-registration-1762463059 --recursive
aws s3 rb s3://cca-registration-1762463059

# 3. Delete IAM role and policy
aws iam delete-role-policy --role-name CCA-Lambda-Role --policy-name CCA-Lambda-Policy
aws iam delete-role --role-name CCA-Lambda-Role

# 4. Delete CloudWatch log group
aws logs delete-log-group --log-group-name /aws/lambda/cca-registration

# 5. Delete Identity Center resources (CAREFUL - affects users)
# Delete account assignment
aws sso-admin delete-account-assignment \
  --instance-arn arn:aws:sso:::instance/ssoins-72232e1b5b84475a \
  --target-id 211050572089 \
  --target-type AWS_ACCOUNT \
  --permission-set-arn arn:aws:sso:::permissionSet/ssoins-72232e1b5b84475a/ps-722336e927a8f2d5 \
  --principal-type GROUP \
  --principal-id f4a854b8-7001-7012-d86c-5fef774ad505

# Delete permission set
aws sso-admin delete-permission-set \
  --instance-arn arn:aws:sso:::instance/ssoins-72232e1b5b84475a \
  --permission-set-arn arn:aws:sso:::permissionSet/ssoins-72232e1b5b84475a/ps-722336e927a8f2d5

# Delete group (removes all members)
aws identitystore delete-group \
  --identity-store-id d-9066117351 \
  --group-id f4a854b8-7001-7012-d86c-5fef774ad505

# 6. SES Email Identity (optional)
# aws ses delete-identity --identity info@2112-lab.com
```

---

## Next Steps

1. **Tag all resources** (See Task 4) with `project=CCA`
2. **Enable CloudWatch alarms** for Lambda errors
3. **Set up cost alerts** for unexpected charges
4. **Document disaster recovery** procedures
5. **Create CloudFormation template** for infrastructure as code

---

**Document Version:** 1.0
**Last Updated:** November 6, 2025
**Maintained By:** CCA Project Team
