"""Main CLI interface for CCC"""
import sys
from datetime import datetime, timezone

import click
import boto3
from botocore.exceptions import ClientError
from colorama import Fore, Style, init

from .config import config
from .auth import CCCAuthenticator

# Initialize colorama
init(autoreset=True)


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """
    CCC (Cloud CLI Client) - Cloud CLI Access Framework

    Authenticate with AWS IAM Identity Center to get temporary credentials.
    """
    pass


@cli.command()
@click.option('--sso-start-url', envvar='CCC_SSO_START_URL',
              help='SSO start URL')
@click.option('--sso-region', envvar='CCC_SSO_REGION', default='us-east-1',
              help='SSO region (default: us-east-1)')
@click.option('--account-id', envvar='CCC_ACCOUNT_ID',
              help='AWS account ID')
@click.option('--role-name', envvar='CCC_ROLE_NAME', default='CCA-CLI-Access',
              help='IAM role name (default: CCA-CLI-Access)')
def configure(sso_start_url, sso_region, account_id, role_name):
    """Configure CCC with your AWS SSO details"""
    if not sso_start_url:
        sso_start_url = click.prompt('SSO start URL')

    if not account_id:
        account_id = click.prompt('AWS Account ID')

    config.set('sso_start_url', sso_start_url)
    config.set('sso_region', sso_region)
    config.set('account_id', account_id)
    config.set('role_name', role_name)

    print(f"\n{Fore.GREEN}Configuration saved{Style.RESET_ALL}")
    print(f"\n{Fore.CYAN}Configuration:{Style.RESET_ALL}")
    print(f"  SSO Start URL: {sso_start_url}")
    print(f"  SSO Region: {sso_region}")
    print(f"  Account ID: {account_id}")
    print(f"  Role Name: {role_name}")
    print(f"\n{Fore.YELLOW}Next step: Run 'ccc login' to authenticate{Style.RESET_ALL}\n")


@cli.command()
def login():
    """Authenticate and obtain AWS credentials"""
    # Check configuration
    sso_start_url = config.get('sso_start_url')
    sso_region = config.get('sso_region')
    account_id = config.get('account_id')
    role_name = config.get('role_name')

    if not all([sso_start_url, sso_region, account_id, role_name]):
        print(f"{Fore.RED}CCC not configured{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Run 'ccc configure' first{Style.RESET_ALL}\n")
        sys.exit(1)

    # Perform authentication
    try:
        authenticator = CCCAuthenticator(
            sso_start_url=sso_start_url,
            sso_region=sso_region,
            account_id=account_id,
            role_name=role_name
        )

        credentials = authenticator.login()

        print(f"{Fore.GREEN}Login successful!{Style.RESET_ALL}")
        print(f"\n{Fore.CYAN}You can now use CCC commands that require AWS access{Style.RESET_ALL}\n")

    except Exception as e:
        print(f"\n{Fore.RED}Login failed: {e}{Style.RESET_ALL}\n")
        sys.exit(1)


@cli.command()
def logout():
    """Clear cached credentials"""
    CCCAuthenticator.logout()


@cli.command()
def status():
    """Show authentication status and credential expiration"""
    cached = config.get_credentials()

    if not cached:
        print(f"{Fore.YELLOW}Not logged in{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Run 'ccc login' to authenticate{Style.RESET_ALL}\n")
        return

    creds = cached['credentials']
    expiration = datetime.fromtimestamp(creds['expiration'] / 1000, tz=timezone.utc)
    cached_at = datetime.fromisoformat(cached['cached_at'])

    now = datetime.now(timezone.utc)
    is_expired = now >= expiration

    print(f"\n{Fore.CYAN}Authentication Status:{Style.RESET_ALL}")
    print(f"  Status: {Fore.GREEN}Authenticated{Style.RESET_ALL}" if not is_expired
          else f"  Status: {Fore.RED}Expired{Style.RESET_ALL}")
    print(f"  SSO Start URL: {cached['sso_start_url']}")
    print(f"  Account ID: {cached['account_id']}")
    print(f"  Role Name: {cached['role_name']}")
    print(f"  Cached: {cached_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  Expires: {expiration.strftime('%Y-%m-%d %H:%M:%S UTC')}")

    if not is_expired:
        time_remaining = expiration - now
        hours, remainder = divmod(time_remaining.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        print(f"  Time Remaining: {hours}h {minutes}m")

    print()


@cli.command()
def test():
    """Test AWS credentials by calling AWS APIs"""
    print(f"{Fore.CYAN}Testing Cloud CLI Access credentials...{Style.RESET_ALL}\n")

    # Get cached credentials
    creds = CCCAuthenticator.get_cached_credentials()

    if not creds:
        print(f"{Fore.RED}Not logged in or credentials expired{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Run 'ccc login' first{Style.RESET_ALL}\n")
        sys.exit(1)

    # Create AWS session with cached credentials
    session = boto3.Session(
        aws_access_key_id=creds['accessKeyId'],
        aws_secret_access_key=creds['secretAccessKey'],
        aws_session_token=creds['sessionToken']
    )

    # Test 1: STS GetCallerIdentity
    print(f"{Fore.CYAN}Test 1: STS GetCallerIdentity{Style.RESET_ALL}")
    try:
        sts = session.client('sts')
        identity = sts.get_caller_identity()
        print(f"  {Fore.GREEN}Success{Style.RESET_ALL}")
        print(f"    User ARN: {identity['Arn']}")
        print(f"    Account: {identity['Account']}")
    except Exception as e:
        print(f"  {Fore.RED}Failed: {e}{Style.RESET_ALL}")

    # Test 2: S3 List Buckets
    print(f"\n{Fore.CYAN}Test 2: S3 ListBuckets{Style.RESET_ALL}")
    try:
        s3 = session.client('s3')
        response = s3.list_buckets()
        bucket_count = len(response['Buckets'])
        print(f"  {Fore.GREEN}Success{Style.RESET_ALL}")
        print(f"    Buckets: {bucket_count}")
    except Exception as e:
        print(f"  {Fore.RED}Failed: {e}{Style.RESET_ALL}")

    # Test 3: EC2 Describe Regions
    print(f"\n{Fore.CYAN}Test 3: EC2 DescribeRegions{Style.RESET_ALL}")
    try:
        ec2 = session.client('ec2')
        response = ec2.describe_regions()
        region_count = len(response['Regions'])
        print(f"  {Fore.GREEN}Success{Style.RESET_ALL}")
        print(f"    Regions available: {region_count}")
    except Exception as e:
        print(f"  {Fore.RED}Failed: {e}{Style.RESET_ALL}")

    print(f"\n{Fore.GREEN}All tests completed{Style.RESET_ALL}\n")


def main():
    """Entry point for CCC CLI"""
    try:
        cli()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Operation cancelled{Style.RESET_ALL}\n")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Fore.RED}Unexpected error: {e}{Style.RESET_ALL}\n")
        sys.exit(1)


if __name__ == '__main__':
    main()
