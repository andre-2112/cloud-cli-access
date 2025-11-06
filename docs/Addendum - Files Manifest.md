# CCA Project - Local Files Manifest

## Directory Structure

```
CCA/
├── docs/
│   ├── CCA-1.md                    # Original implementation guide
│   ├── CCA-2.md                    # Post-deployment tasks
│   └── cca-deployment-summary.md   # Complete deployment summary
├── tmp/                             # Build artifacts and configs
│   ├── bucket-policy.json          # S3 bucket policy
│   ├── cca-config.env              # Environment variables (all configs)
│   ├── cli-group.json              # Identity Center group creation response
│   ├── cli-permission-set.json     # Permission set inline policy
│   ├── function-url.json           # Lambda Function URL config
│   ├── group-id.txt                # CLI group ID
│   ├── lambda_func.py              # Partial Lambda code
│   ├── lambda-function.json        # Lambda function creation response
│   ├── lambda-policy.json          # Lambda IAM policy
│   ├── lambda-role.json            # Lambda IAM role creation response
│   ├── lambda-role-arn.txt         # Lambda role ARN
│   ├── lambda-trust-policy.json    # Lambda trust policy
│   ├── permission-set.json         # Permission set creation response
│   ├── ps-arn.txt                  # Permission set ARN
│   ├── registration.html           # Registration form (S3 hosted)
│   └── secret-key.txt              # JWT secret key
├── lambda/                          # Lambda function code
│   ├── lambda_function.py          # Complete Lambda function
│   └── lambda_function.zip         # Packaged Lambda deployment
└── ccc-cli/                         # Cloud CLI Client tool
    ├── ccc/                         # Python package
    │   ├── __init__.py             # Package initializer
    │   ├── __main__.py             # CLI entry point
    │   ├── auth.py                 # Authentication module
    │   ├── cli.py                  # CLI commands
    │   └── config.py               # Configuration management
    ├── ccc_cli.egg-info/           # Package metadata
    ├── requirements.txt            # Python dependencies
    └── setup.py                    # Package setup script
```

## File Descriptions

### Configuration Files
- **cca-config.env**: Complete environment configuration with all AWS resource IDs
- **secret-key.txt**: JWT signing secret (keep secure!)

### Lambda Function
- **lambda_function.py**: Complete Lambda handler (registration, approval, denial)
- **lambda_function.zip**: Deployment package for AWS Lambda

### CCC CLI Tool
- Complete Python CLI application for IAM Identity Center authentication
- Supports configure, login, logout, status, and test commands
- Installed with: `pip3 install -e .`

### Documentation
- **CCA-1.md**: Step-by-step implementation guide (77KB)
- **CCA-2.md**: Post-deployment tasks checklist
- **cca-deployment-summary.md**: Complete deployment summary with URLs and configs

## Original Locations

### /tmp Directory (C:\Users\Admin\AppData\Local\Temp)
All files from /tmp/ have been copied to CCA/tmp/

### ~/ccc-cli Directory
Complete CCC CLI tool has been copied to CCA/ccc-cli/

### Home Directory
Deployment summary copied to CCA/docs/

## Important Notes

1. **Security**: The secret-key.txt and cca-config.env contain sensitive data
2. **Installation**: CCC CLI is still installed from ~/ccc-cli (editable mode)
3. **Backups**: All original files remain in their original locations
4. **Git**: Consider adding tmp/*.txt and tmp/*.env to .gitignore

## Quick Commands

### View Configuration
```bash
cat ~/Documents/Workspace/CCA/tmp/cca-config.env
```

### Reinstall CCC CLI
```bash
cd ~/Documents/Workspace/CCA/ccc-cli
pip3 install -e .
```

### Deploy Lambda Updates
```bash
cd ~/Documents/Workspace/CCA/lambda
# Update lambda_function.py
python3 -m zipfile -c lambda_function.zip lambda_function.py
aws lambda update-function-code --function-name cca-registration --zip-file fileb://lambda_function.zip
```
