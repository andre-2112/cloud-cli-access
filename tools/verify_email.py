#!/usr/bin/env python3
"""
Email Verification Tool for CCA
Checks if emails were sent via SES and displays delivery status
"""

import boto3
import sys
from datetime import datetime, timedelta
import json

def check_ses_statistics(hours=1):
    """Check SES sending statistics"""
    ses = boto3.client('ses', region_name='us-east-1')
    cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')

    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)

    print(f"\n{'='*70}")
    print(f"SES Email Verification Report")
    print(f"Time Range: {start_time.strftime('%Y-%m-%d %H:%M:%S')} to {end_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"{'='*70}\n")

    # Get SES send quota
    quota = ses.get_send_quota()
    print("[*] SES Account Status:")
    print(f"  - Max 24 Hour Send: {quota['Max24HourSend']}")
    print(f"  - Sent Last 24 Hours: {quota['SentLast24Hours']}")
    print(f"  - Max Send Rate: {quota['MaxSendRate']}/sec")

    # Get CloudWatch metrics for email sends
    print(f"\n[*] Email Delivery Metrics (last {hours} hour(s)):")

    metrics = ['Send', 'Delivery', 'Bounce', 'Complaint', 'Reject']

    for metric_name in metrics:
        try:
            response = cloudwatch.get_metric_statistics(
                Namespace='AWS/SES',
                MetricName=metric_name,
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1 hour
                Statistics=['Sum']
            )

            total = sum([dp['Sum'] for dp in response['Datapoints']])

            if total > 0:
                icon = "[+]" if metric_name in ['Send', 'Delivery'] else "[-]"
                print(f"  {icon} {metric_name}: {int(total)}")
        except Exception as e:
            print(f"  [!] {metric_name}: Unable to retrieve ({str(e)})")

    print(f"\n{'='*70}")

def check_lambda_logs_for_email(email_address, hours=1):
    """Check Lambda logs for specific email address"""
    logs = boto3.client('logs', region_name='us-east-1')

    end_time = int(datetime.utcnow().timestamp() * 1000)
    start_time = int((datetime.utcnow() - timedelta(hours=hours)).timestamp() * 1000)

    print(f"\n[*] Lambda Logs Search for: {email_address}")
    print(f"{'='*70}")

    try:
        # Search for registration logs
        response = logs.filter_log_events(
            logGroupName='/aws/lambda/cca-registration',
            startTime=start_time,
            endTime=end_time,
            filterPattern=f'"{email_address}"'
        )

        events = response.get('events', [])

        if not events:
            print(f"[-] No logs found for {email_address}")
            return

        print(f"[+] Found {len(events)} log entries:\n")

        for event in events:
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
            message = event['message'].strip()

            # Highlight important log lines
            if 'email sent successfully' in message.lower():
                icon = "[+]"
            elif 'error' in message.lower():
                icon = "[-]"
            elif 'creating user' in message.lower():
                icon = "[USER]"
            elif 'processing registration' in message.lower():
                icon = "[REG]"
            else:
                icon = "[i]"

            print(f"{icon} [{timestamp}] {message}")

        print(f"\n{'='*70}")

    except Exception as e:
        print(f"[-] Error checking logs: {e}")

def check_ses_suppression_list(email_address):
    """Check if email is in SES suppression list"""
    sesv2 = boto3.client('sesv2', region_name='us-east-1')

    print(f"\n[*] SES Suppression List Check for: {email_address}")
    print(f"{'='*70}")

    try:
        response = sesv2.get_suppressed_destination(
            EmailAddress=email_address
        )

        print(f"[!] EMAIL IS SUPPRESSED!")
        print(f"  - Reason: {response['SuppressedDestination']['Reason']}")
        print(f"  - Suppressed Since: {response['SuppressedDestination']['LastUpdateTime']}")
        print(f"\nTo remove from suppression list, run:")
        print(f"aws sesv2 delete-suppressed-destination --email-address {email_address} --region us-east-1")

    except sesv2.exceptions.NotFoundException:
        print(f"[+] Email is NOT in suppression list (can receive emails)")
    except Exception as e:
        print(f"[!] Error checking suppression list: {e}")

    print(f"{'='*70}")

def verify_email_identity(email_address):
    """Check if email is verified in SES"""
    ses = boto3.client('ses', region_name='us-east-1')

    print(f"\n[*] SES Email Verification Status")
    print(f"{'='*70}")

    try:
        response = ses.get_identity_verification_attributes(
            Identities=[email_address]
        )

        attrs = response.get('VerificationAttributes', {})

        if email_address in attrs:
            status = attrs[email_address].get('VerificationStatus')
            if status == 'Success':
                print(f"[+] {email_address} is VERIFIED and can receive emails")
            else:
                print(f"[-] {email_address} verification status: {status}")
        else:
            print(f"[!] {email_address} is NOT verified in SES")
            print(f"\nNOTE: If SES is in sandbox mode, only verified addresses can receive emails.")
            print(f"To verify, run:")
            print(f"aws ses verify-email-identity --email-address {email_address} --region us-east-1")

    except Exception as e:
        print(f"[-] Error checking verification: {e}")

    print(f"{'='*70}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python verify_email.py <email_address> [hours]")
        print("Example: python verify_email.py andre.philippi@gmail.com 2")
        sys.exit(1)

    email = sys.argv[1]
    hours = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    # Run all checks
    check_ses_statistics(hours)
    check_lambda_logs_for_email(email, hours)
    verify_email_identity(email)
    check_ses_suppression_list(email)

    print("\n[*] Verification complete!\n")
