# CCA User Management Guide

Quick reference for managing CCA users in AWS IAM Identity Center.

---

## 1. Viewing Registered Users

### AWS Console

**Navigation:**
1. Go to: https://console.aws.amazon.com/singlesignon
2. OR Search for "IAM Identity Center" in AWS Console
3. Click "Users" in the left sidebar

**Direct Link:**
```
https://us-east-1.console.aws.amazon.com/singlesignon/identity/home?region=us-east-1#!/users
```

**What You'll See:**
- Username
- Display Name
- Email Address
- Status (Enabled/Disabled)
- Group Memberships
- Last Sign-In

### AWS CLI

**List All Users:**
```bash
aws identitystore list-users \
  --identity-store-id d-9066117351 \
  --region us-east-1 \
  --query 'Users[*].[UserName,DisplayName,Emails[0].Value]' \
  --output table
```

**List Users in CCA-CLI-Users Group:**
```bash
# Get group members
aws identitystore list-group-memberships \
  --identity-store-id d-9066117351 \
  --group-id f4a854b8-7001-7012-d86c-5fef774ad505 \
  --region us-east-1
```

**Search for Specific User:**
```bash
aws identitystore list-users \
  --identity-store-id d-9066117351 \
  --region us-east-1 \
  --filters AttributePath=UserName,AttributeValue=USERNAME_HERE
```

---

## 2. Deleting Users

### Important Notes

⚠️ **Deleting a user:**
- Removes them from all groups
- Revokes all permissions
- Cannot be undone
- Does NOT remove approval emails or registration history

### AWS Console

**Steps:**
1. Navigate to IAM Identity Center → Users
2. Click on the user you want to delete
3. Click "Delete user" button (top right)
4. Type the username to confirm
5. Click "Delete"

### AWS CLI

**Method 1: Delete by Username**

```bash
# Step 1: Get the user ID
USER_ID=$(aws identitystore list-users \
  --identity-store-id d-9066117351 \
  --region us-east-1 \
  --filters AttributePath=UserName,AttributeValue=test \
  --query 'Users[0].UserId' \
  --output text)

# Step 2: Delete the user
aws identitystore delete-user \
  --identity-store-id d-9066117351 \
  --user-id $USER_ID \
  --region us-east-1

echo "User deleted successfully"
```

**Method 2: Delete by User ID (if known)**

```bash
aws identitystore delete-user \
  --identity-store-id d-9066117351 \
  --user-id 9408a4a8-0001-7023-19f0-596de28d8b05 \
  --region us-east-1
```

**Bulk Delete Script:**

```bash
#!/bin/bash
# Delete multiple users

USERS_TO_DELETE=("user1" "user2" "user3")

for username in "${USERS_TO_DELETE[@]}"; do
    echo "Deleting user: $username"

    USER_ID=$(aws identitystore list-users \
        --identity-store-id d-9066117351 \
        --region us-east-1 \
        --filters AttributePath=UserName,AttributeValue=$username \
        --query 'Users[0].UserId' \
        --output text)

    if [ "$USER_ID" != "None" ] && [ -n "$USER_ID" ]; then
        aws identitystore delete-user \
            --identity-store-id d-9066117351 \
            --user-id $USER_ID \
            --region us-east-1
        echo "✓ Deleted: $username"
    else
        echo "✗ User not found: $username"
    fi
done
```

---

## 3. Duplicate User Prevention

### How It Works

The CCA Lambda function includes **built-in duplicate prevention** to ensure users cannot be created twice.

**Code Location:** `lambda/lambda_function.py` lines 136-152

### Duplicate Check Logic

```python
# During approval process
def handle_approval(event):
    # ... token verification ...

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

    # Only create user if it doesn't exist
    create_identity_center_user(user_data)
```

### When Duplicate Check Runs

| Stage | Duplicate Check | Why |
|-------|----------------|-----|
| **Registration** | ❌ No | Allows users to resubmit if they don't receive email |
| **Approval** | ✅ Yes | Prevents duplicate users in Identity Center |
| **User Creation** | ✅ Yes | Identity Center also validates uniqueness |

### What Happens With Duplicates

**Scenario 1: User Registers Twice**
- ✅ Allowed
- Both submissions create separate approval emails
- Admin receives two emails
- Approving either email works
- Approving both shows "User Already Exists" for second

**Scenario 2: Admin Clicks Approve Twice**
- First click: User created ✅
- Second click: "User Already Exists" message ✅
- No duplicate user created
- **Idempotent operation**

**Scenario 3: Different Users, Same Username**
- First user approved: Created ✅
- Second user with same username: Registration fails at approval ✅
- Admin sees "User Already Exists" message
- **Usernames must be unique across Identity Center**

### Testing Duplicate Prevention

**Manual Test:**
```bash
# 1. Register a user
curl -X POST https://kmfuod67kbaeombcknzrjbtrmi0qqncd.lambda-url.us-east-1.on.aws/register \
  -H "Content-Type: application/json" \
  -d '{"username":"duplicate-test","email":"test@example.com","first_name":"Test","last_name":"Dup"}'

# 2. Click approve link from email
# 3. Click approve link AGAIN
# 4. You'll see "User Already Exists" message
```

**Check Logs:**
```bash
# View Lambda logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/cca-registration \
  --region us-east-1 \
  --filter-pattern "already exists" \
  --max-items 10
```

---

## 4. User Information Reference

### Current Environment

**IAM Identity Center:**
- Identity Store ID: `d-9066117351`
- SSO Start URL: `https://d-9066117351.awsapps.com/start`
- Region: `us-east-1`

**Group:**
- Name: `CCA-CLI-Users`
- Group ID: `f4a854b8-7001-7012-d86c-5fef774ad505`

**Permission Set:**
- Name: `CCA-CLI-Access`
- Policy: PowerUserAccess (no Console access)

**Lambda Function:**
- Name: `cca-registration`
- Function URL: `https://kmfuod67kbaeombcknzrjbtrmi0qqncd.lambda-url.us-east-1.on.aws`

### Current Registered Users

```
+------+------------+----------------------+----------------------------------------+
| test | Test User  | andre@2112-lab.com   | 9408a4a8-0001-7023-19f0-596de28d8b05   |
+------+------------+----------------------+----------------------------------------+
```

---

## 5. Common User Management Tasks

### Disable a User (Without Deleting)

**Console:**
1. Navigate to user
2. Click "Disable user"

**CLI:**
```bash
# This feature requires disabling at the permission set assignment level
# OR removing from group
aws identitystore delete-group-membership \
  --identity-store-id d-9066117351 \
  --membership-id MEMBERSHIP_ID \
  --region us-east-1
```

### Reset User Password

Users can reset passwords themselves at:
```
https://d-9066117351.awsapps.com/start
```

**Admin can also trigger password reset:**
1. Console → Users → Select User
2. Click "Reset password"
3. User receives email with reset link

### Check User's Last Sign-In

**Console:**
1. Navigate to user details
2. View "Last sign-in" timestamp

**CLI:**
```bash
# Identity Center doesn't expose last sign-in via API
# Must use CloudTrail for detailed login history
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=test \
  --region us-east-1 \
  --max-results 10
```

### Add User to Additional Groups

```bash
# Create group membership
aws identitystore create-group-membership \
  --identity-store-id d-9066117351 \
  --group-id GROUP_ID_HERE \
  --member-id UserId=USER_ID_HERE \
  --region us-east-1
```

### Remove User from Group

```bash
# List memberships first
aws identitystore list-group-memberships-for-member \
  --identity-store-id d-9066117351 \
  --member-id UserId=USER_ID_HERE \
  --region us-east-1

# Delete specific membership
aws identitystore delete-group-membership \
  --identity-store-id d-9066117351 \
  --membership-id MEMBERSHIP_ID \
  --region us-east-1
```

---

## 6. Monitoring and Auditing

### View Registration Requests (CloudWatch)

```bash
# View recent Lambda invocations
aws logs filter-log-events \
  --log-group-name /aws/lambda/cca-registration \
  --region us-east-1 \
  --start-time $(date -d '1 day ago' +%s)000 \
  --filter-pattern "Registration submitted"
```

### View Approved Users

```bash
# View approval events
aws logs filter-log-events \
  --log-group-name /aws/lambda/cca-registration \
  --region us-east-1 \
  --start-time $(date -d '1 day ago' +%s)000 \
  --filter-pattern "Registration Approved"
```

### View Denied Users

```bash
# View denial events
aws logs filter-log-events \
  --log-group-name /aws/lambda/cca-registration \
  --region us-east-1 \
  --start-time $(date -d '1 day ago' +%s)000 \
  --filter-pattern "Registration Denied"
```

### Export User List

```bash
# Export to CSV
aws identitystore list-users \
  --identity-store-id d-9066117351 \
  --region us-east-1 \
  --query 'Users[*].[UserName,DisplayName,Emails[0].Value,UserId]' \
  --output text > cca-users.csv

echo "Username,DisplayName,Email,UserId" > cca-users-with-header.csv
cat cca-users.csv >> cca-users-with-header.csv
```

---

## 7. Troubleshooting

### User Cannot Login

**Check:**
1. User exists in Identity Center
2. User is in CCA-CLI-Users group
3. User has set their password
4. Permission set is assigned to group
5. Account assignment is provisioned

**Verify:**
```bash
# Check user exists
aws identitystore list-users \
  --identity-store-id d-9066117351 \
  --filters AttributePath=UserName,AttributeValue=USERNAME \
  --region us-east-1

# Check group membership
aws identitystore list-group-memberships-for-member \
  --identity-store-id d-9066117351 \
  --member-id UserId=USER_ID \
  --region us-east-1
```

### User Approved But No Password Email

**Possible Causes:**
1. Email in spam folder
2. Email address typo
3. SES email not sent (check CloudWatch logs)

**Solution:**
Admin can manually trigger password reset from console

### Duplicate Error When Approving

**This is normal!** The user was already approved.

Check if user exists:
```bash
aws identitystore list-users \
  --identity-store-id d-9066117351 \
  --filters AttributePath=UserName,AttributeValue=USERNAME \
  --region us-east-1
```

---

## Quick Reference Commands

```bash
# List all users
aws identitystore list-users --identity-store-id d-9066117351 --region us-east-1

# Get specific user
aws identitystore list-users --identity-store-id d-9066117351 --region us-east-1 \
  --filters AttributePath=UserName,AttributeValue=USERNAME

# Delete user
aws identitystore delete-user --identity-store-id d-9066117351 --user-id USER_ID --region us-east-1

# List group members
aws identitystore list-group-memberships --identity-store-id d-9066117351 \
  --group-id f4a854b8-7001-7012-d86c-5fef774ad505 --region us-east-1

# Check Lambda logs
aws logs tail /aws/lambda/cca-registration --region us-east-1 --follow
```

---

**For more information, see:**
- [CCA Deployment Summary](./docs/CCA%20-%20Deployment%20Summary.md)
- [AWS Resources Inventory](./docs/AWS%20Resources%20Inventory.md)
- [Test Results](./TEST-RESULTS.md)
