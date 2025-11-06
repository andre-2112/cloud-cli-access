# CCA Framework - Custom Domain Setup

**Document Version:** 1.0
**Last Updated:** November 6, 2025
**Purpose:** Configure custom domains for registration form and Identity Center access portal

---

## Overview

This document provides step-by-step instructions to set up custom domains for:

1. **Registration Form** - Currently at: http://cca-registration-1762463059.s3-website-us-east-1.amazonaws.com/registration.html
   - Target: https://register.example.com

2. **Identity Center Access Portal** - Currently at: https://d-9066117351.awsapps.com/start
   - Target: https://sso.example.com

---

## Part 1: Custom Domain for S3 Registration Form

### Architecture

```
┌─────────────────┐         ┌──────────────────┐
│    Route 53     │         │   CloudFront     │
│  (DNS)          │────────►│   (CDN)          │
│                 │         │   SSL/TLS        │
│ register.       │         │   Caching        │
│ example.com     │         └────────┬─────────┘
└─────────────────┘                  │
                                     │
                            ┌────────▼─────────┐
                            │   S3 Bucket      │
                            │   (Origin)       │
                            │                  │
                            │ registration.html│
                            └──────────────────┘
```

### Prerequisites

- [x] Domain registered (e.g., example.com)
- [x] Access to DNS management (Route 53 or other provider)
- [x] AWS Certificate Manager (ACM) access
- [x] CloudFront distribution permissions

---

### Step 1: Request SSL Certificate (ACM)

SSL certificates for CloudFront must be in **us-east-1** region.

```bash
# 1. Request certificate
aws acm request-certificate \
  --domain-name "register.example.com" \
  --validation-method DNS \
  --subject-alternative-names "www.register.example.com" \
  --region us-east-1 \
  --tags Key=project,Value=CCA Key=component,Value=registration-form \
  --output json > /tmp/certificate-request.json

# Get certificate ARN
export CERT_ARN=$(cat /tmp/certificate-request.json | jq -r '.CertificateArn')
echo "Certificate ARN: $CERT_ARN"

# 2. Get DNS validation records
aws acm describe-certificate \
  --certificate-arn "$CERT_ARN" \
  --region us-east-1 \
  --query 'Certificate.DomainValidationOptions[0].ResourceRecord' \
  --output json

# Response will show DNS records to create:
# {
#   "Name": "_abc123.register.example.com",
#   "Type": "CNAME",
#   "Value": "_xyz456.acm-validations.aws."
# }
```

### Step 2: Create DNS Validation Records

#### If using Route 53:

```bash
# 1. Get Hosted Zone ID
export HOSTED_ZONE_ID=$(aws route53 list-hosted-zones \
  --query "HostedZones[?Name=='example.com.'].Id" \
  --output text | cut -d'/' -f3)

echo "Hosted Zone ID: $HOSTED_ZONE_ID"

# 2. Get validation record details
export VALIDATION_NAME=$(aws acm describe-certificate \
  --certificate-arn "$CERT_ARN" \
  --region us-east-1 \
  --query 'Certificate.DomainValidationOptions[0].ResourceRecord.Name' \
  --output text)

export VALIDATION_VALUE=$(aws acm describe-certificate \
  --certificate-arn "$CERT_ARN" \
  --region us-east-1 \
  --query 'Certificate.DomainValidationOptions[0].ResourceRecord.Value' \
  --output text)

# 3. Create validation record
cat > /tmp/validation-record.json <<EOF
{
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "${VALIDATION_NAME}",
      "Type": "CNAME",
      "TTL": 300,
      "ResourceRecords": [{"Value": "${VALIDATION_VALUE}"}]
    }
  }]
}
EOF

aws route53 change-resource-record-sets \
  --hosted-zone-id "$HOSTED_ZONE_ID" \
  --change-batch file:///tmp/validation-record.json

# 4. Wait for validation (can take 5-30 minutes)
echo "Waiting for certificate validation..."
aws acm wait certificate-validated \
  --certificate-arn "$CERT_ARN" \
  --region us-east-1

echo "✅ Certificate validated!"
```

#### If using external DNS provider:

1. Log into your DNS provider (GoDaddy, Namecheap, etc.)
2. Add CNAME record:
   - **Name:** `_abc123.register.example.com` (from ACM response)
   - **Value:** `_xyz456.acm-validations.aws.` (from ACM response)
   - **TTL:** 300 seconds
3. Wait for validation (5-30 minutes)

### Step 3: Create CloudFront Distribution

```bash
# 1. Create CloudFront distribution configuration
cat > /tmp/cloudfront-config.json <<EOF
{
  "CallerReference": "cca-registration-$(date +%s)",
  "Comment": "CCA Registration Form - Custom Domain",
  "Enabled": true,
  "DefaultRootObject": "registration.html",
  "Aliases": {
    "Quantity": 1,
    "Items": ["register.example.com"]
  },
  "ViewerCertificate": {
    "ACMCertificateArn": "${CERT_ARN}",
    "SSLSupportMethod": "sni-only",
    "MinimumProtocolVersion": "TLSv1.2_2021"
  },
  "Origins": {
    "Quantity": 1,
    "Items": [{
      "Id": "S3-cca-registration",
      "DomainName": "cca-registration-1762463059.s3-website-us-east-1.amazonaws.com",
      "CustomOriginConfig": {
        "HTTPPort": 80,
        "HTTPSPort": 443,
        "OriginProtocolPolicy": "http-only",
        "OriginSslProtocols": {
          "Quantity": 1,
          "Items": ["TLSv1.2"]
        }
      }
    }]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "S3-cca-registration",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": {
      "Quantity": 2,
      "Items": ["GET", "HEAD"]
    },
    "CachedMethods": {
      "Quantity": 2,
      "Items": ["GET", "HEAD"]
    },
    "ForwardedValues": {
      "QueryString": false,
      "Cookies": {
        "Forward": "none"
      }
    },
    "MinTTL": 0,
    "DefaultTTL": 86400,
    "MaxTTL": 31536000,
    "Compress": true
  },
  "PriceClass": "PriceClass_100",
  "CustomErrorResponses": {
    "Quantity": 2,
    "Items": [
      {
        "ErrorCode": 403,
        "ResponsePagePath": "/registration.html",
        "ResponseCode": "200",
        "ErrorCachingMinTTL": 300
      },
      {
        "ErrorCode": 404,
        "ResponsePagePath": "/registration.html",
        "ResponseCode": "200",
        "ErrorCachingMinTTL": 300
      }
    ]
  }
}
EOF

# 2. Create distribution
aws cloudfront create-distribution \
  --distribution-config file:///tmp/cloudfront-config.json \
  --output json > /tmp/cloudfront-distribution.json

# 3. Get distribution details
export DISTRIBUTION_ID=$(cat /tmp/cloudfront-distribution.json | jq -r '.Distribution.Id')
export CLOUDFRONT_DOMAIN=$(cat /tmp/cloudfront-distribution.json | jq -r '.Distribution.DomainName')

echo "Distribution ID: $DISTRIBUTION_ID"
echo "CloudFront Domain: $CLOUDFRONT_DOMAIN"

# 4. Wait for distribution deployment (can take 15-30 minutes)
echo "Waiting for CloudFront distribution to deploy..."
aws cloudfront wait distribution-deployed \
  --id "$DISTRIBUTION_ID"

echo "✅ CloudFront distribution deployed!"
```

### Step 4: Create DNS Record for Custom Domain

```bash
# Create Route 53 record pointing to CloudFront
cat > /tmp/custom-domain-record.json <<EOF
{
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "register.example.com",
      "Type": "A",
      "AliasTarget": {
        "HostedZoneId": "Z2FDTNDATAQYW2",
        "DNSName": "${CLOUDFRONT_DOMAIN}",
        "EvaluateTargetHealth": false
      }
    }
  }]
}
EOF

aws route53 change-resource-record-sets \
  --hosted-zone-id "$HOSTED_ZONE_ID" \
  --change-batch file:///tmp/custom-domain-record.json

echo "✅ DNS record created!"
echo ""
echo "Your registration form is now available at:"
echo "https://register.example.com"
```

### Step 5: Update Lambda Function Environment Variables

Update the Lambda function to reference the new custom domain:

```bash
# Update REGISTRATION_URL in Lambda environment
aws lambda update-function-configuration \
  --function-name cca-registration \
  --environment "Variables={
    IDENTITY_STORE_ID=d-9066117351,
    CLI_GROUP_ID=f4a854b8-7001-7012-d86c-5fef774ad505,
    SSO_START_URL=https://d-9066117351.awsapps.com/start,
    FROM_EMAIL=info@2112-lab.com,
    ADMIN_EMAIL=info@2112-lab.com,
    SECRET_KEY=cd00daddf99d8bec982759905ba9caec0b45237b8beb2ce6dec6c947555f58a9,
    REGISTRATION_URL=https://register.example.com
  }"

echo "✅ Lambda environment updated!"
```

### Step 6: Test Custom Domain

```bash
# Test HTTPS access
curl -I https://register.example.com

# Should return:
# HTTP/2 200
# content-type: text/html
# x-cache: Hit from cloudfront

# Test registration form loads
curl https://register.example.com | grep -i "Cloud CLI Access"

echo "✅ Custom domain working!"
```

---

## Part 2: Custom Domain for Identity Center Access Portal

### Architecture

```
┌─────────────────┐         ┌──────────────────┐
│    Route 53     │         │  IAM Identity    │
│  (DNS)          │────────►│   Center         │
│                 │  CNAME  │   Access Portal  │
│ sso.            │         │                  │
│ example.com     │         │ d-9066117351     │
└─────────────────┘         └──────────────────┘
```

### Important Notes

⚠️ **Limited Customization:** AWS IAM Identity Center has limited support for custom domains on the access portal URL.

**Current Options:**

1. **Custom Domain Redirect** (Recommended for now)
2. **AWS Private Link** (Enterprise feature)
3. **Reverse Proxy** (Complex, not recommended)

---

### Option 1: Custom Domain Redirect (Recommended)

Create a simple redirect from your custom domain to the IAM Identity Center portal.

#### Step 1: Create Redirect Page on S3

```bash
# 1. Create a simple HTML redirect page
cat > /tmp/sso-redirect.html <<'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="0;url=https://d-9066117351.awsapps.com/start">
    <title>Redirecting to SSO Login...</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .container {
            text-align: center;
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Cloud CLI Access</h1>
        <div class="spinner"></div>
        <p>Redirecting to login...</p>
        <p><a href="https://d-9066117351.awsapps.com/start">Click here if not redirected automatically</a></p>
    </div>
    <script>
        // Immediate redirect
        window.location.href = "https://d-9066117351.awsapps.com/start";
    </script>
</body>
</html>
EOF

# 2. Create S3 bucket for SSO redirect
export SSO_REDIRECT_BUCKET="cca-sso-redirect-$(date +%s)"
aws s3 mb s3://$SSO_REDIRECT_BUCKET

# 3. Enable website hosting
aws s3 website s3://$SSO_REDIRECT_BUCKET --index-document index.html

# 4. Upload redirect page
aws s3 cp /tmp/sso-redirect.html s3://$SSO_REDIRECT_BUCKET/index.html \
  --content-type text/html \
  --cache-control "max-age=60"

# 5. Make bucket public
aws s3api put-public-access-block \
  --bucket $SSO_REDIRECT_BUCKET \
  --public-access-block-configuration \
    "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

cat > /tmp/sso-bucket-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicReadGetObject",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::${SSO_REDIRECT_BUCKET}/*"
  }]
}
EOF

aws s3api put-bucket-policy \
  --bucket $SSO_REDIRECT_BUCKET \
  --policy file:///tmp/sso-bucket-policy.json

echo "✅ SSO redirect bucket created"
```

#### Step 2: Request SSL Certificate for SSO Domain

```bash
# Request certificate for sso.example.com
aws acm request-certificate \
  --domain-name "sso.example.com" \
  --validation-method DNS \
  --region us-east-1 \
  --tags Key=project,Value=CCA Key=component,Value=sso-redirect \
  --output json > /tmp/sso-certificate.json

export SSO_CERT_ARN=$(cat /tmp/sso-certificate.json | jq -r '.CertificateArn')
echo "SSO Certificate ARN: $SSO_CERT_ARN"

# Get validation records
aws acm describe-certificate \
  --certificate-arn "$SSO_CERT_ARN" \
  --region us-east-1 \
  --query 'Certificate.DomainValidationOptions[0].ResourceRecord'

# Create validation records in Route 53 (similar to Step 2 above)
export SSO_VALIDATION_NAME=$(aws acm describe-certificate \
  --certificate-arn "$SSO_CERT_ARN" \
  --region us-east-1 \
  --query 'Certificate.DomainValidationOptions[0].ResourceRecord.Name' \
  --output text)

export SSO_VALIDATION_VALUE=$(aws acm describe-certificate \
  --certificate-arn "$SSO_CERT_ARN" \
  --region us-east-1 \
  --query 'Certificate.DomainValidationOptions[0].ResourceRecord.Value' \
  --output text)

cat > /tmp/sso-validation-record.json <<EOF
{
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "${SSO_VALIDATION_NAME}",
      "Type": "CNAME",
      "TTL": 300,
      "ResourceRecords": [{"Value": "${SSO_VALIDATION_VALUE}"}]
    }
  }]
}
EOF

aws route53 change-resource-record-sets \
  --hosted-zone-id "$HOSTED_ZONE_ID" \
  --change-batch file:///tmp/sso-validation-record.json

# Wait for validation
aws acm wait certificate-validated \
  --certificate-arn "$SSO_CERT_ARN" \
  --region us-east-1

echo "✅ SSO certificate validated!"
```

#### Step 3: Create CloudFront for SSO Redirect

```bash
# Create CloudFront distribution for SSO redirect
cat > /tmp/sso-cloudfront-config.json <<EOF
{
  "CallerReference": "cca-sso-$(date +%s)",
  "Comment": "CCA SSO Redirect - Custom Domain",
  "Enabled": true,
  "DefaultRootObject": "index.html",
  "Aliases": {
    "Quantity": 1,
    "Items": ["sso.example.com"]
  },
  "ViewerCertificate": {
    "ACMCertificateArn": "${SSO_CERT_ARN}",
    "SSLSupportMethod": "sni-only",
    "MinimumProtocolVersion": "TLSv1.2_2021"
  },
  "Origins": {
    "Quantity": 1,
    "Items": [{
      "Id": "S3-sso-redirect",
      "DomainName": "${SSO_REDIRECT_BUCKET}.s3-website-us-east-1.amazonaws.com",
      "CustomOriginConfig": {
        "HTTPPort": 80,
        "HTTPSPort": 443,
        "OriginProtocolPolicy": "http-only"
      }
    }]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "S3-sso-redirect",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": {
      "Quantity": 2,
      "Items": ["GET", "HEAD"]
    },
    "ForwardedValues": {
      "QueryString": false,
      "Cookies": {"Forward": "none"}
    },
    "MinTTL": 0,
    "DefaultTTL": 60,
    "MaxTTL": 3600,
    "Compress": true
  },
  "PriceClass": "PriceClass_100"
}
EOF

aws cloudfront create-distribution \
  --distribution-config file:///tmp/sso-cloudfront-config.json \
  --output json > /tmp/sso-cloudfront-distribution.json

export SSO_DISTRIBUTION_ID=$(cat /tmp/sso-cloudfront-distribution.json | jq -r '.Distribution.Id')
export SSO_CLOUDFRONT_DOMAIN=$(cat /tmp/sso-cloudfront-distribution.json | jq -r '.Distribution.DomainName')

echo "SSO Distribution ID: $SSO_DISTRIBUTION_ID"
echo "SSO CloudFront Domain: $SSO_CLOUDFRONT_DOMAIN"

# Wait for deployment
aws cloudfront wait distribution-deployed --id "$SSO_DISTRIBUTION_ID"
echo "✅ SSO CloudFront distribution deployed!"
```

#### Step 4: Create DNS Record for SSO Custom Domain

```bash
# Create Route 53 record for sso.example.com
cat > /tmp/sso-domain-record.json <<EOF
{
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "sso.example.com",
      "Type": "A",
      "AliasTarget": {
        "HostedZoneId": "Z2FDTNDATAQYW2",
        "DNSName": "${SSO_CLOUDFRONT_DOMAIN}",
        "EvaluateTargetHealth": false
      }
    }
  }]
}
EOF

aws route53 change-resource-record-sets \
  --hosted-zone-id "$HOSTED_ZONE_ID" \
  --change-batch file:///tmp/sso-domain-record.json

echo "✅ SSO DNS record created!"
echo ""
echo "Your SSO portal is now accessible via:"
echo "https://sso.example.com"
echo "(Will redirect to https://d-9066117351.awsapps.com/start)"
```

#### Step 5: Update Documentation and CCC CLI

Update CCC CLI configuration to use custom domain:

```bash
# Users can now use the custom domain
ccc configure \
  --sso-start-url "https://sso.example.com" \
  --sso-region "us-east-1" \
  --account-id "211050572089" \
  --role-name "CCA-CLI-Access"

# CCC CLI will follow the redirect automatically
```

---

### Option 2: AWS Private Link (Enterprise)

For organizations with AWS Enterprise Support, you can request a custom domain for Identity Center through AWS Support.

**Requirements:**
- AWS Enterprise Support plan
- Custom domain (e.g., sso.example.com)
- SSL certificate in ACM
- AWS PrivateLink setup

**Process:**
1. Open AWS Support case
2. Request custom domain for Identity Center
3. Provide domain and certificate details
4. AWS will configure the custom domain
5. Update DNS records as instructed

**Timeline:** 2-4 weeks

**Cost:** Included with Enterprise Support

---

## Complete Deployment Summary

### Final URLs

| Resource | Original URL | Custom URL |
|----------|-------------|------------|
| Registration Form | http://cca-registration-1762463059.s3-website-us-east-1.amazonaws.com/registration.html | https://register.example.com |
| SSO Portal | https://d-9066117351.awsapps.com/start | https://sso.example.com (redirect) |
| Lambda Function | https://kmfuod67kbaeombcknzrjbtrmi0qqncd.lambda-url.us-east-1.on.aws/ | (No custom domain needed) |

### DNS Records Created

```
example.com. (Hosted Zone)
  ├── register.example.com → CloudFront (ALIAS)
  │   └── _abc123.register.example.com → ACM validation (CNAME)
  ├── sso.example.com → CloudFront (ALIAS)
  │   └── _xyz456.sso.example.com → ACM validation (CNAME)
```

### AWS Resources Created

- 2 ACM Certificates (register.example.com, sso.example.com)
- 2 CloudFront Distributions
- 1 Additional S3 Bucket (SSO redirect)
- 4 Route 53 DNS Records

---

## Cost Estimate

### Monthly Costs with Custom Domains

| Service | Usage | Cost |
|---------|-------|------|
| Route 53 Hosted Zone | 1 zone | $0.50 |
| Route 53 Queries | ~1M queries | $0.40 |
| ACM Certificates | 2 certs | Free |
| CloudFront | ~10GB data transfer | $0.85 |
| CloudFront Requests | ~1M requests | $0.01 |
| S3 Storage | ~1MB | $0.00 |
| S3 Requests | ~100 requests | $0.00 |
| **Total** | | **~$1.76/month** |

**Scaling (100,000 users/month):**
- CloudFront: ~$8-15
- Route 53: ~$0.80
- **Total: ~$10-20/month**

---

## Testing

### Test Registration Form Custom Domain

```bash
# Test HTTPS
curl -I https://register.example.com

# Test SSL certificate
openssl s_client -connect register.example.com:443 -servername register.example.com < /dev/null

# Test form loads
curl -s https://register.example.com | grep "Cloud CLI Access"

# Test from browser
open https://register.example.com
```

### Test SSO Portal Custom Domain

```bash
# Test redirect
curl -I https://sso.example.com

# Should return:
# HTTP/2 200
# location: https://d-9066117351.awsapps.com/start

# Test SSL certificate
openssl s_client -connect sso.example.com:443 -servername sso.example.com < /dev/null

# Test from browser
open https://sso.example.com
```

### Test End-to-End Workflow

```bash
# 1. User visits registration form
open https://register.example.com

# 2. User fills form and submits
# (Check admin email for approval)

# 3. Admin approves user
# (User gets password setup email)

# 4. User configures CCC CLI with custom domain
ccc configure \
  --sso-start-url "https://sso.example.com" \
  --sso-region "us-east-1" \
  --account-id "211050572089" \
  --role-name "CCA-CLI-Access"

# 5. User logs in
ccc login
# (Browser opens https://sso.example.com, redirects to Identity Center)

# 6. User authenticates
# (Gets AWS credentials)

# 7. User tests access
ccc test
```

---

## Troubleshooting

### Issue: SSL Certificate Validation Stuck

**Symptoms:** Certificate stays in "Pending Validation" status

**Solutions:**
```bash
# 1. Verify DNS record exists
dig _abc123.register.example.com CNAME

# 2. Check DNS propagation
nslookup -type=CNAME _abc123.register.example.com 8.8.8.8

# 3. Delete and recreate DNS record
aws route53 change-resource-record-sets \
  --hosted-zone-id "$HOSTED_ZONE_ID" \
  --change-batch '{"Changes":[{"Action":"DELETE",...}]}'

# Wait 5 minutes, then recreate
```

### Issue: CloudFront Shows "InvalidViewerCertificate"

**Symptoms:** CloudFront distribution fails to deploy

**Solution:**
```bash
# Certificate must be in us-east-1 region
aws acm list-certificates --region us-east-1

# If certificate is in wrong region, request new one in us-east-1
```

### Issue: Custom Domain Not Resolving

**Symptoms:** `nslookup sso.example.com` fails

**Solutions:**
```bash
# 1. Check DNS propagation (can take up to 48 hours)
dig sso.example.com

# 2. Verify Route 53 record exists
aws route53 list-resource-record-sets \
  --hosted-zone-id "$HOSTED_ZONE_ID" \
  --query "ResourceRecordSets[?Name=='sso.example.com.']"

# 3. Clear local DNS cache
# macOS:
sudo dscacheutil -flushcache

# Windows:
ipconfig /flushdns

# Linux:
sudo systemd-resolve --flush-caches
```

### Issue: Browser Shows "Not Secure" Warning

**Symptoms:** SSL error in browser

**Solutions:**
```bash
# 1. Verify certificate is deployed to CloudFront
aws cloudfront get-distribution --id $DISTRIBUTION_ID \
  --query 'Distribution.DistributionConfig.ViewerCertificate'

# 2. Check certificate status
aws acm describe-certificate \
  --certificate-arn "$CERT_ARN" \
  --region us-east-1 \
  --query 'Certificate.Status'

# 3. Verify domain matches certificate
# Certificate must include exact domain or wildcard
```

---

## Maintenance

### Update SSL Certificates (Before Expiry)

ACM certificates auto-renew if DNS validation records remain in place:

```bash
# Check certificate expiry
aws acm describe-certificate \
  --certificate-arn "$CERT_ARN" \
  --region us-east-1 \
  --query 'Certificate.NotAfter'

# ACM will email reminders 45 days before expiry
# Auto-renewal requires DNS records to remain
```

### Update S3 Content

```bash
# Update registration form
aws s3 cp ./registration.html s3://cca-registration-1762463059/ \
  --content-type text/html

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id "$DISTRIBUTION_ID" \
  --paths "/*"
```

### Monitor Custom Domains

```bash
# Set up Route 53 health check
aws route53 create-health-check \
  --type HTTPS \
  --resource-path "/" \
  --fully-qualified-domain-name "register.example.com" \
  --port 443 \
  --request-interval 30

# Set up CloudWatch alarm
aws cloudwatch put-metric-alarm \
  --alarm-name custom-domain-down \
  --alarm-description "Alert if custom domain is down" \
  --metric-name HealthCheckStatus \
  --namespace AWS/Route53 \
  --statistic Minimum \
  --period 60 \
  --evaluation-periods 2 \
  --threshold 1 \
  --comparison-operator LessThanThreshold
```

---

## Security Considerations

### 1. SSL/TLS Configuration

✅ **Use TLS 1.2+** - Configured in CloudFront
✅ **Enable HSTS** - Consider adding to CloudFront response headers
✅ **Disable legacy protocols** - TLS 1.0/1.1 disabled by default

### 2. CloudFront Security Headers

Add security headers to CloudFront responses:

```javascript
// CloudFront Function (Lambda@Edge alternative)
function handler(event) {
    var response = event.response;
    var headers = response.headers;

    // Security headers
    headers['strict-transport-security'] = { value: 'max-age=31536000; includeSubDomains'};
    headers['content-security-policy'] = { value: "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"};
    headers['x-content-type-options'] = { value: 'nosniff'};
    headers['x-frame-options'] = { value: 'DENY'};
    headers['x-xss-protection'] = { value: '1; mode=block'};
    headers['referrer-policy'] = { value: 'strict-origin-when-cross-origin'};

    return response;
}
```

### 3. Access Logging

Enable CloudFront access logs:

```bash
# Create S3 bucket for logs
aws s3 mb s3://cca-cloudfront-logs-$(date +%s)

# Update CloudFront distribution to enable logging
aws cloudfront update-distribution \
  --id "$DISTRIBUTION_ID" \
  --distribution-config '{...,"Logging":{"Enabled":true,"Bucket":"cca-cloudfront-logs.s3.amazonaws.com","Prefix":"register/","IncludeCookies":false}...}'
```

---

## Summary

✅ **Custom Domain for Registration Form**
- Domain: https://register.example.com
- Requires: ACM certificate, CloudFront, Route 53
- Setup time: 30-60 minutes
- Cost: ~$1-2/month

✅ **Custom Domain for SSO Portal**
- Domain: https://sso.example.com (redirect)
- Requires: ACM certificate, CloudFront, Route 53, S3
- Setup time: 30-60 minutes
- Cost: ~$0.50-1/month
- Note: Full custom SSO domain requires AWS Enterprise Support

✅ **Benefits:**
- Professional appearance
- Consistent branding
- Better user experience
- Improved security (HTTPS)
- CloudFront caching and performance

✅ **Total Additional Cost:** ~$2-3/month (minimal scaling)

---

**Next Steps:**

1. Purchase/verify domain ownership
2. Request SSL certificates in ACM
3. Create CloudFront distributions
4. Configure DNS records
5. Test end-to-end workflows
6. Update documentation and user guides
7. Monitor performance and costs

---

**Document Version:** 1.0
**Maintained By:** CCA Project Team
