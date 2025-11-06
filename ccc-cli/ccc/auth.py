"""Authentication module for CCC CLI using IAM Identity Center device flow"""
import time
import webbrowser
import json
from datetime import datetime, timezone
from typing import Optional, Dict

import boto3
from botocore.exceptions import ClientError
from colorama import Fore, Style

from .config import config


class CCCAuthenticator:
    """Handles authentication with IAM Identity Center"""

    def __init__(self, sso_start_url: str, sso_region: str,
                 account_id: str, role_name: str):
        self.sso_start_url = sso_start_url
        self.sso_region = sso_region
        self.account_id = account_id
        self.role_name = role_name

        self.oidc_client = boto3.client('sso-oidc', region_name=sso_region)
        self.sso_client = boto3.client('sso', region_name=sso_region)

    def login(self) -> Dict:
        """Perform device flow authentication - Returns AWS credentials"""
        print(f"{Fore.CYAN}Initiating Cloud CLI Access authentication...{Style.RESET_ALL}\n")

        # Step 1: Register client
        print("Registering client...")
        client_registration = self._register_client()
        client_id = client_registration['clientId']
        client_secret = client_registration['clientSecret']

        # Step 2: Start device authorization
        print("Starting device authorization...")
        device_auth = self._start_device_authorization(client_id, client_secret)

        device_code = device_auth['deviceCode']
        user_code = device_auth['userCode']
        verification_uri = device_auth['verificationUri']
        verification_uri_complete = device_auth.get('verificationUriComplete', verification_uri)
        interval = device_auth.get('interval', 5)
        expires_in = device_auth.get('expiresIn', 600)

        # Step 3: Display to user and open browser
        self._display_authentication_instructions(verification_uri, user_code, verification_uri_complete)

        # Step 4: Poll for authorization
        print(f"\n{Fore.YELLOW}Waiting for authentication...{Style.RESET_ALL}")
        access_token = self._poll_for_token(client_id, client_secret, device_code, interval, expires_in)

        print(f"{Fore.GREEN}Authentication successful!{Style.RESET_ALL}\n")

        # Step 5: Exchange token for AWS credentials
        print("Fetching AWS credentials...")
        credentials = self._get_role_credentials(access_token)

        # Step 6: Cache credentials
        self._cache_credentials(credentials, access_token)

        print(f"{Fore.GREEN}Credentials cached successfully{Style.RESET_ALL}")
        expiration = datetime.fromtimestamp(credentials['expiration'] / 1000, tz=timezone.utc)
        print(f"{Fore.CYAN}Valid until: {expiration.isoformat()}{Style.RESET_ALL}\n")

        return credentials

    def _register_client(self) -> Dict:
        """Register the CLI as an OAuth client"""
        try:
            response = self.oidc_client.register_client(
                clientName='CCC-CLI',
                clientType='public'
            )
            return response
        except ClientError as e:
            print(f"{Fore.RED}Failed to register client: {e}{Style.RESET_ALL}")
            raise

    def _start_device_authorization(self, client_id: str, client_secret: str) -> Dict:
        """Start the device authorization flow"""
        try:
            response = self.oidc_client.start_device_authorization(
                clientId=client_id,
                clientSecret=client_secret,
                startUrl=self.sso_start_url
            )
            return response
        except ClientError as e:
            print(f"{Fore.RED}Failed to start device authorization: {e}{Style.RESET_ALL}")
            raise

    def _display_authentication_instructions(self, uri: str, user_code: str, uri_complete: str):
        """Display authentication instructions to user"""
        print("\n" + "=" * 60)
        print(f"{Fore.CYAN}Opening browser for authentication...{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}If browser doesn't open automatically, visit:{Style.RESET_ALL}")
        print(f"{Fore.WHITE}{uri}{Style.RESET_ALL}")
        print(f"\n{Fore.YELLOW}And enter code:{Style.RESET_ALL} {Fore.GREEN}{user_code}{Style.RESET_ALL}")
        print("=" * 60)

        # Auto-open browser
        try:
            webbrowser.open(uri_complete)
            print(f"\n{Fore.GREEN}Browser opened{Style.RESET_ALL}")
        except Exception as e:
            print(f"\n{Fore.YELLOW}Could not open browser automatically: {e}{Style.RESET_ALL}")

    def _poll_for_token(self, client_id: str, client_secret: str,
                       device_code: str, interval: int, expires_in: int) -> str:
        """Poll for authorization token"""
        start_time = time.time()

        while True:
            if time.time() - start_time > expires_in:
                raise TimeoutError("Authentication timeout - please try again")

            time.sleep(interval)

            try:
                response = self.oidc_client.create_token(
                    clientId=client_id,
                    clientSecret=client_secret,
                    grantType='urn:ietf:params:oauth:grant-type:device_code',
                    deviceCode=device_code
                )

                return response['accessToken']

            except ClientError as e:
                error_code = e.response['Error']['Code']

                if error_code == 'AuthorizationPendingException':
                    print(".", end="", flush=True)
                    continue
                elif error_code == 'SlowDownException':
                    interval += 5
                    time.sleep(5)
                    continue
                elif error_code == 'ExpiredTokenException':
                    raise TimeoutError("Authentication expired - please try again")
                else:
                    print(f"\n{Fore.RED}Authentication error: {e}{Style.RESET_ALL}")
                    raise

    def _get_role_credentials(self, access_token: str) -> Dict:
        """Exchange access token for AWS credentials"""
        try:
            response = self.sso_client.get_role_credentials(
                roleName=self.role_name,
                accountId=self.account_id,
                accessToken=access_token
            )

            creds = response['roleCredentials']
            return {
                'accessKeyId': creds['accessKeyId'],
                'secretAccessKey': creds['secretAccessKey'],
                'sessionToken': creds['sessionToken'],
                'expiration': creds['expiration']
            }
        except ClientError as e:
            print(f"{Fore.RED}Failed to get role credentials: {e}{Style.RESET_ALL}")
            raise

    def _cache_credentials(self, credentials: Dict, access_token: str):
        """Cache credentials locally"""
        cache_data = {
            'credentials': credentials,
            'access_token': access_token,
            'cached_at': datetime.now(timezone.utc).isoformat(),
            'sso_start_url': self.sso_start_url,
            'sso_region': self.sso_region,
            'account_id': self.account_id,
            'role_name': self.role_name
        }
        config.save_credentials(cache_data)

    @staticmethod
    def get_cached_credentials() -> Optional[Dict]:
        """Get cached credentials if valid"""
        cached = config.get_credentials()
        if not cached:
            return None

        # Check if expired
        expiration = cached['credentials']['expiration']
        expiration_time = datetime.fromtimestamp(expiration / 1000, tz=timezone.utc)

        if datetime.now(timezone.utc) >= expiration_time:
            print(f"{Fore.YELLOW}Cached credentials expired{Style.RESET_ALL}")
            return None

        return cached['credentials']

    @staticmethod
    def logout():
        """Clear cached credentials"""
        config.clear_credentials()
        print(f"{Fore.GREEN}Logged out successfully{Style.RESET_ALL}")
