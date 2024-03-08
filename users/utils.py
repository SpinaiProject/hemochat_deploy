import requests
import json
import os
from datetime import datetime
import base64
import hashlib
import hmac


def make_signature(access_key, secret_key, method, uri, timestamp):
    secret_key_bytes = bytes(secret_key, 'UTF-8')

    message = method + " " + uri + "\n" + timestamp + "\n" + access_key
    message_bytes = bytes(message, 'UTF-8')

    signing_key = base64.b64encode(hmac.new(secret_key_bytes, message_bytes, digestmod=hashlib.sha256).digest())

    return signing_key.decode('UTF-8')


def send_sms(phone_number, message):
    access_key = os.environ.get('SENS_ACCESS_KEY')
    secret_key = os.environ.get('SENS_SECRET_KEY')
    service_id = os.environ.get('SENS_SERVICE_ID')
    sender_number = os.environ.get('SENS_SENDER_NUMBER')

    timestamp = str(int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000))
    signature = make_signature(access_key, secret_key, "POST", "/sms/v2/services/{serviceId}/messages", timestamp)

    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "x-ncp-apigw-timestamp": timestamp,
        "x-ncp-iam-access-key": access_key,
        "x-ncp-apigw-signature-v2": signature,
    }
    data = {
        'type': 'SMS',
        'from': sender_number,
        'to': [phone_number],
        'content': message
    }

    try:
        response = requests.post(f'https://sens.apigw.ntruss.com/sms/v2/services/{service_id}/messages',
                                 headers=headers, data=json.dumps(data))
        response.raise_for_status()
        return True, response.json()
    except requests.exceptions.HTTPError as err:
        return False, str(err)
