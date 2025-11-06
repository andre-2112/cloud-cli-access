# AWS Console Navigation Guide - Finding IAM Identity Center Users

## Issue: "I don't see any users at the IAM Identity Center console"

---

## Quick Solution

**Direct Link (Copy and paste this):**
```
https://us-east-1.console.aws.amazon.com/singlesignon/home?region=us-east-1#!/users
```

---

## Step-by-Step Navigation

### Step 1: Check Your Region (CRITICAL!)

**Look at the top-right corner of AWS Console**

```
┌─────────────────────────────────────────────────┐
│  AWS Console                    [N. Virginia ▼] │  ← Must say "N. Virginia"
└─────────────────────────────────────────────────┘
```

If it says anything else (like "US West", "EU", etc.), click it and select:
- **US East (N. Virginia)**
- or **us-east-1**

⚠️ **If you're in the wrong region, you will see ZERO users!**

---

### Step 2: Navigate to IAM Identity Center

**Option A: Search Bar (Recommended)**

1. Click the search bar at the top of the AWS Console
2. Type: `IAM Identity Center`
3. Click on **"IAM Identity Center"** (with the orange icon)
   - **NOT** "IAM" (the blue one)
   - **NOT** "IAM Roles Anywhere"

**Option B: Services Menu**

1. Click "Services" in top-left
2. Under "Security, Identity, & Compliance"
3. Click "IAM Identity Center"

---

### Step 3: Navigate to Users

Once you're in IAM Identity Center, you should see:

```
┌────────────────────────────────────────────────────────────┐
│  IAM Identity Center                        [us-east-1]     │
├───────────────┬────────────────────────────────────────────┤
│               │                                             │
│  Dashboard    │   Welcome to IAM Identity Center           │
│  Settings     │                                             │
│               │   Instance ARN:                            │
│  Directory    │   arn:aws:sso:::instance/ssoins-...       │
│  ┣ Users  ←   │                                             │
│  ┗ Groups     │                                             │
│               │                                             │
│  Applications │                                             │
│               │                                             │
└───────────────┴────────────────────────────────────────────┘
```

**Click "Users" in the left sidebar** (under "Directory" section)

---

### Step 4: You Should See

```
┌────────────────────────────────────────────────────────────┐
│  Users                                      [+ Add user]    │
├────────────────────────────────────────────────────────────┤
│  🔍 Search users                                [⟳ Refresh]│
├──────────┬──────────────┬────────────────────┬────────────┤
│ Username │ Display name │ Email              │ Status     │
├──────────┼──────────────┼────────────────────┼────────────┤
│ test     │ Test User    │ andre@2112-lab.com │ Enabled    │
└──────────┴──────────────┴────────────────────┴────────────┘
```

---

## Still Don't See Users? Try These:

### Fix 1: Hard Refresh the Console

**Windows:** Press `Ctrl + F5`
**Mac:** Press `Cmd + Shift + R`

Console pages sometimes cache empty results.

---

### Fix 2: Check Console Permissions

Verify your AWS credentials have permissions to view IAM Identity Center:

**Required Permissions:**
- `identitystore:ListUsers`
- `sso:ListInstances`
- `sso:DescribeInstance`

**Quick Test:**
```bash
# If this works, you have CLI permissions
aws identitystore list-users \
  --identity-store-id d-9066117351 \
  --region us-east-1
```

If CLI works but Console doesn't, your IAM user/role might have different permissions for Console vs CLI.

---

### Fix 3: Check Identity Store ID

Your Identity Store ID should be: **d-9066117351**

Verify in console:
1. IAM Identity Center → Dashboard
2. Look for "Identity source"
3. Should show: "Identity Center directory"
4. Click "Settings" in sidebar
5. Check "Identity source" section

**Identity Store ARN should be:**
```
arn:aws:identitystore:::identitystore/d-9066117351
```

---

### Fix 4: Try Alternative Navigation

Sometimes the console has different entry points:

**Path 1: Via SSO Console**
```
Services → IAM Identity Center → Directory → Users
```

**Path 2: Via Security Hub**
```
Services → Security, Identity & Compliance → IAM Identity Center → Users
```

**Path 3: Via AWS Home**
```
AWS Home → Recently visited services → IAM Identity Center → Users
```

---

## Verify User Exists (CLI Method)

If console still doesn't work, verify user exists via CLI:

```bash
# List all users
aws identitystore list-users \
  --identity-store-id d-9066117351 \
  --region us-east-1 \
  --query 'Users[*].[UserName,DisplayName,Emails[0].Value]' \
  --output table
```

**Expected Output:**
```
+------+------------+----------------------+
| test | Test User  | andre@2112-lab.com   |
+------+------------+----------------------+
```

If you see the user via CLI but NOT in console, it's a console permission or caching issue.

---

## Common Mistakes

### ❌ Wrong: Looking at IAM (not IAM Identity Center)

```
Services → IAM (blue icon) → Users
```
This shows IAM users, NOT Identity Center users. **Wrong place!**

### ✅ Correct: IAM Identity Center

```
Services → IAM Identity Center (orange icon) → Users
```
This shows Identity Center users. **Correct place!**

---

### ❌ Wrong: Wrong Region

```
Console shows: US West (Oregon)
Your Identity Center: us-east-1 (N. Virginia)
Result: Empty users list
```

### ✅ Correct: Correct Region

```
Console shows: US East (N. Virginia)
Your Identity Center: us-east-1
Result: Users visible ✓
```

---

## Your Identity Center Details

**Instance Information:**
- **Status:** ACTIVE ✅
- **Identity Store ID:** d-9066117351
- **Instance ARN:** arn:aws:sso:::instance/ssoins-72232e1b5b84475a
- **Region:** us-east-1 (N. Virginia)
- **SSO Portal:** https://d-9066117351.awsapps.com/start

**Current Users:**
- Username: test
- User ID: 9408a4a8-0001-7023-19f0-596de28d8b05
- Email: andre@2112-lab.com
- Status: Enabled
- Groups: CCA-CLI-Users

---

## Alternative: Manage Users via CLI

If console access continues to be problematic, you can manage everything via CLI:

**List Users:**
```bash
aws identitystore list-users --identity-store-id d-9066117351 --region us-east-1
```

**Get Specific User:**
```bash
aws identitystore list-users \
  --identity-store-id d-9066117351 \
  --region us-east-1 \
  --filters AttributePath=UserName,AttributeValue=test
```

**Delete User:**
```bash
aws identitystore delete-user \
  --identity-store-id d-9066117351 \
  --user-id 9408a4a8-0001-7023-19f0-596de28d8b05 \
  --region us-east-1
```

---

## Still Having Issues?

### Check Browser Console for Errors

1. Press F12 (or right-click → Inspect)
2. Click "Console" tab
3. Refresh the Users page
4. Look for red error messages
5. Share any errors you see

### Check CloudTrail for Console Access

```bash
# Check if console is making API calls
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=ListUsers \
  --region us-east-1 \
  --max-results 10
```

If no events appear, the console isn't even trying to fetch users (permissions issue).

---

## Screenshot Reference

When you're on the correct page, the URL should look like:
```
https://us-east-1.console.aws.amazon.com/singlesignon/home?region=us-east-1#!/users
```

The breadcrumb should show:
```
IAM Identity Center > Users
```

The page title should say:
```
Users
```

And there should be an "Add user" button in the top-right.

---

## Contact Information

If none of these solutions work, there may be an AWS console issue. Try:
1. Different browser (Chrome, Firefox, Edge)
2. Incognito/Private mode
3. Different network
4. Different AWS account credentials

**Verified Working:**
- ✅ CLI access works (user exists)
- ✅ Identity Center is ACTIVE
- ✅ User created successfully
- ⚠️ Console display issue

---

## Quick Diagnostic Commands

Run these to verify everything is working:

```bash
# 1. Check Identity Center is active
aws sso-admin list-instances --region us-east-1

# 2. Check user exists
aws identitystore list-users --identity-store-id d-9066117351 --region us-east-1

# 3. Check group membership
aws identitystore list-group-memberships \
  --identity-store-id d-9066117351 \
  --group-id f4a854b8-7001-7012-d86c-5fef774ad505 \
  --region us-east-1

# 4. Check your permissions
aws sts get-caller-identity
```

All four should return successful results.

---

**TL;DR - Most Common Issue:**
🔴 **Wrong region selected in console (not us-east-1)**
🔴 **Looking at IAM users instead of IAM Identity Center users**

**Solution:**
1. Switch to us-east-1 (N. Virginia) region
2. Go to IAM Identity Center (NOT IAM)
3. Click Users in left sidebar
4. Press Ctrl+F5 to refresh
