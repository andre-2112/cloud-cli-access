# CCC CLI - Installation Guide

**Cloud CLI Client** - A secure CLI authentication tool using AWS IAM Identity Center

---

## Quick Install

```bash
# Clone the repository
git clone https://github.com/YOUR_ORG/cloud-cli-access.git
cd cloud-cli-access/ccc-cli

# Install dependencies and CCC CLI
pip3 install -r requirements.txt
pip3 install -e .

# Verify installation
ccc --version
```

---

## Prerequisites

Before installing CCC CLI, ensure you have:

- **Python 3.8 or higher**
  ```bash
  python3 --version  # Should show 3.8.0 or higher
  ```

- **pip (Python package manager)**
  ```bash
  pip3 --version
  ```

- **Git** (for cloning the repository)
  ```bash
  git --version
  ```

- **AWS IAM Identity Center access** (provided by your administrator)

---

## Installation Methods

### Method 1: Install from Source (Recommended for Development)

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_ORG/cloud-cli-access.git
cd cloud-cli-access/ccc-cli

# 2. Install in editable mode
pip3 install -e .

# 3. Verify installation
ccc --version
ccc --help
```

**Benefits:**
- Easy to modify and test changes
- Automatically reflects code updates
- Best for development and testing

### Method 2: Install from PyPI (When Published)

```bash
# Install directly from PyPI (future)
pip3 install ccc-cli

# Verify installation
ccc --version
```

**Note:** Package not yet published to PyPI. Use Method 1 for now.

### Method 3: Install from Wheel File

```bash
# 1. Build the package
cd cloud-cli-access/ccc-cli
python3 setup.py bdist_wheel

# 2. Install the wheel
pip3 install dist/ccc_cli-1.0.0-py3-none-any.whl

# 3. Verify installation
ccc --version
```

---

## Platform-Specific Instructions

### macOS / Linux

```bash
# Install system-wide (may require sudo)
sudo pip3 install -e .

# Or install for current user only (recommended)
pip3 install --user -e .

# Add to PATH if needed
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Windows

```powershell
# Install in user directory
pip install --user -e .

# Add to PATH if needed (PowerShell)
$env:Path += ";$env:APPDATA\Python\Python311\Scripts"

# Or add permanently through System Properties > Environment Variables
```

### Windows (Git Bash / MinGW)

```bash
# Install normally
pip3 install -e .

# Verify PATH
which ccc

# Add to PATH if needed
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

---

## Configuration

After installation, configure CCC CLI with your organization's settings:

```bash
ccc configure
```

You'll be prompted for:
- **SSO Start URL**: Your Identity Center portal (e.g., https://d-xxxxxxxxxx.awsapps.com/start)
- **AWS Region**: Usually `us-east-1`
- **Account ID**: Your AWS account ID
- **Role Name**: Usually `CCA-CLI-Access`

**Or configure non-interactively:**

```bash
ccc configure \
  --sso-start-url "https://d-xxxxxxxxxx.awsapps.com/start" \
  --sso-region "us-east-1" \
  --account-id "123456789012" \
  --role-name "CCA-CLI-Access"
```

**Configuration is saved to:** `~/.ccc/config.json`

---

## First Login

```bash
# Authenticate with IAM Identity Center
ccc login
```

This will:
1. Open your browser automatically
2. Redirect to Identity Center login page
3. Ask you to authenticate with username/password
4. Return temporary AWS credentials (valid for 12 hours)

**Check authentication status:**

```bash
ccc status
```

**Test AWS access:**

```bash
ccc test
```

---

## Dependencies

CCC CLI requires the following Python packages (automatically installed):

```
boto3>=1.34.0       # AWS SDK
click>=8.1.0        # CLI framework
colorama>=0.4.6     # Terminal colors
python-dateutil>=2.8.2  # Date/time utilities
```

**Install dependencies manually:**

```bash
pip3 install boto3 click colorama python-dateutil
```

---

## Upgrading

### From Source Installation

```bash
cd cloud-cli-access/ccc-cli
git pull origin main
pip3 install -e . --upgrade
```

### From PyPI (When Available)

```bash
pip3 install --upgrade ccc-cli
```

---

## Uninstalling

```bash
# Uninstall the package
pip3 uninstall ccc-cli

# Remove configuration (optional)
rm -rf ~/.ccc

# Remove cloned repository (optional)
rm -rf ~/cloud-cli-access
```

---

## Troubleshooting

### Issue: `ccc: command not found`

**Solution 1:** Add to PATH
```bash
# Find where pip installed it
pip3 show ccc-cli | grep Location

# Add to PATH
export PATH="$HOME/.local/bin:$PATH"
```

**Solution 2:** Use full path
```bash
python3 -m ccc --version
```

**Solution 3:** Reinstall with --user flag
```bash
pip3 install --user -e .
```

### Issue: `ModuleNotFoundError: No module named 'ccc'`

**Solution:** Install dependencies
```bash
pip3 install -r requirements.txt
pip3 install -e .
```

### Issue: `Permission denied` during installation

**Solution:** Install for user only
```bash
pip3 install --user -e .
```

### Issue: Python version too old

**Solution:** Upgrade Python
```bash
# macOS (Homebrew)
brew install python@3.11

# Ubuntu/Debian
sudo apt update
sudo apt install python3.11

# Windows
# Download from https://www.python.org/downloads/
```

### Issue: SSL certificate errors

**Solution:** Upgrade pip and certifi
```bash
pip3 install --upgrade pip certifi
```

---

## Verifying Installation

Run these commands to verify everything works:

```bash
# 1. Check version
ccc --version
# Expected: ccc, version 1.0.0

# 2. Check help
ccc --help
# Should show all available commands

# 3. Check configuration
ccc status
# Should show "Not logged in" if first time

# 4. Test configuration
ccc configure --help
# Should show configuration options
```

---

## Usage Examples

### Basic Workflow

```bash
# 1. Configure (one-time setup)
ccc configure

# 2. Login (authenticate)
ccc login

# 3. Check status
ccc status

# 4. Test AWS access
ccc test

# 5. Use AWS CLI with CCC credentials
# (CCC stores credentials in ~/.ccc/credentials.json)
```

### Advanced Usage

```bash
# Login and immediately test
ccc login && ccc test

# Check credential expiration
ccc status | grep "Expires"

# Force re-authentication
ccc logout && ccc login

# Use with AWS CLI
aws sts get-caller-identity
# (Requires AWS CLI to be configured to use CCC credentials)
```

---

## Integration with AWS CLI

CCC CLI stores credentials in `~/.ccc/credentials.json`. To use with AWS CLI:

**Option 1: Manual credential export**
```bash
# After ccc login, export credentials
export AWS_ACCESS_KEY_ID=$(cat ~/.ccc/credentials.json | jq -r '.credentials.accessKeyId')
export AWS_SECRET_ACCESS_KEY=$(cat ~/.ccc/credentials.json | jq -r '.credentials.secretAccessKey')
export AWS_SESSION_TOKEN=$(cat ~/.ccc/credentials.json | jq -r '.credentials.sessionToken')

# Now use AWS CLI
aws s3 ls
```

**Option 2: Use credential process** (Future enhancement)
```ini
# ~/.aws/config
[profile cca]
credential_process = ccc get-credentials
```

---

## Getting Help

### Command Help

```bash
# General help
ccc --help

# Command-specific help
ccc configure --help
ccc login --help
ccc status --help
ccc test --help
```

### Support

- **Documentation:** See `/docs` directory
- **Issues:** Open an issue on GitHub
- **Administrator:** Contact your CCA administrator for access issues

---

## Next Steps

After installation:

1. **Configure CCC:** Run `ccc configure` with your organization's settings
2. **First Login:** Run `ccc login` to authenticate
3. **Test Access:** Run `ccc test` to verify AWS access
4. **Read Docs:** Check the `/docs` folder for advanced usage

---

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Python | 3.8 | 3.11+ |
| RAM | 512 MB | 1 GB+ |
| Disk Space | 50 MB | 100 MB |
| Network | Internet access required | - |
| OS | Linux, macOS, Windows | Any |

---

## Security Notes

- CCC stores credentials in `~/.ccc/` with 0600 permissions
- Credentials expire after 12 hours (configurable by administrator)
- Console access is disabled by default (CLI/API only)
- Always keep CCC CLI updated to the latest version
- Never share your `~/.ccc/credentials.json` file

---

**Installation Complete!** 🎉

Run `ccc configure` to get started.
