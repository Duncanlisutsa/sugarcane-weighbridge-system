import ssl
import urllib3
import threading

# Fix SSL compatibility issue with Python 3.14 on Windows
ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings()


import africastalking
import requests
import json
from django.conf import settings


def send_sms(phone_number, message):
    """
    Send SMS using Africa's Talking API directly
    with SSL verification disabled for compatibility.
    """
    try:
        # Format phone number
        if phone_number.startswith('0'):
            phone_number = '+254' + phone_number[1:]
        elif not phone_number.startswith('+'):
            phone_number = '+254' + phone_number

        # API endpoint
        url = 'https://api.sandbox.africastalking.com/version1/messaging'

        # Headers
        headers = {
            'Accept':       'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
            'apiKey':        settings.AFRICASTALKING_API_KEY,
        }

        # Payload
        payload = {
            'username': settings.AFRICASTALKING_USERNAME,
            'to':       phone_number,
            'message':  message,
        }

        # Send request with SSL verification disabled
        response = requests.post(
            url,
            headers=headers,
            data=payload,
            verify=False
        )

        print(f"SMS response: {response.status_code} — {response.text}")

        if response.status_code == 201:
            return True
        else:
            return False

    except Exception as e:
        print(f"SMS failed: {e}")
        return False


def send_gross_weight_sms(transaction):
    """
    Send gross weight notification to farmer
    after gross weight is recorded.
    """
    farmer  = transaction.farmer
    phone   = farmer.phone

    message = (
        f"Dear {farmer.full_name}, your sugarcane delivery "
        f"has been received at the weighbridge.\n"
        f"Gross weight recorded: {transaction.gross_weight_kg} kg\n"
        f"Time: {transaction.gross_time.strftime('%I:%M %p on %d/%m/%Y')}\n"
        f"Receipt No: {transaction.receipt_number}\n"
        f"Keep this message as proof. "
        f"- Weighbridge System"
    )

    return send_sms(phone, message)


def send_completion_sms(transaction):
    """
    Send final net weight notification to farmer
    after transaction is complete.
    """
    farmer  = transaction.farmer
    phone   = farmer.phone

    message = (
        f"Dear {farmer.full_name}, your weighing is complete.\n"
        f"Gross: {transaction.gross_weight_kg} kg\n"
        f"Tare:  {transaction.tare_weight_kg} kg\n"
        f"NET WEIGHT: {transaction.net_weight_kg} kg\n"
        f"Receipt No: {transaction.receipt_number}\n"
        f"Date: {transaction.gross_time.strftime('%d/%m/%Y')}\n"
        f"- Weighbridge System"
    )

    return send_sms(phone, message)


def send_gross_weight_sms_async(transaction):
    """
    Fire-and-forget version: runs the (slow, network-dependent) SMS send
    on a background thread so the request/response cycle doesn't wait
    on it. Use this from views instead of calling send_gross_weight_sms
    directly.
    """
    threading.Thread(
        target=send_gross_weight_sms,
        args=(transaction,),
        daemon=True
    ).start()


def send_completion_sms_async(transaction):
    """
    Fire-and-forget version of send_completion_sms — see
    send_gross_weight_sms_async for why.
    """
    threading.Thread(
        target=send_completion_sms,
        args=(transaction,),
        daemon=True
    ).start()