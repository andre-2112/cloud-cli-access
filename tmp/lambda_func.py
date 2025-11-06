import json
import boto3
import hmac
import hashlib
import base64
import os
from datetime import datetime, timedelta

ses = boto3.client('ses')
identitystore = boto3.client('identitystore')

IDENTITY_STORE_ID = os.environ['IDENTITY_STORE_ID']
CLI_GROUP_ID = os.environ['CLI_GROUP_ID']
SSO_START_URL = os.environ['SSO_START_URL']
FROM_EMAIL = os.environ['FROM_EMAIL']
ADMIN_EMAIL = os.environ['ADMIN_EMAIL']
SECRET_KEY = os.environ['SECRET_KEY']
