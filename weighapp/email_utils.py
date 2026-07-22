from django.conf import settings
from django.core.mail import send_mail
import threading


def send_email(to_email, subject, message):
    """
    Send an email notification using Django's configured
    SMTP backend (see EMAIL_* settings in weighbridge/settings.py).
    """
    if not to_email:
        return False

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [to_email],
            fail_silently=False,
        )
        return True

    except Exception as e:
        print(f"Email failed: {e}")
        return False


def send_gross_weight_email(transaction):
    """
    Send gross weight notification to farmer's email
    after gross weight is recorded (mirrors send_gross_weight_sms).
    """
    farmer = transaction.farmer

    if not farmer.email:
        return False

    subject = f"Delivery Received — Receipt {transaction.receipt_number}"
    message = (
        f"Dear {farmer.full_name},\n\n"
        f"Your sugarcane delivery has been received at the weighbridge.\n"
        f"Gross weight recorded: {transaction.gross_weight_kg} kg\n"
        f"Time: {transaction.gross_time.strftime('%I:%M %p on %d/%m/%Y')}\n"
        f"Receipt No: {transaction.receipt_number}\n\n"
        f"Keep this message as proof.\n"
        f"- Weighbridge System"
    )

    return send_email(farmer.email, subject, message)


def send_completion_email(transaction):
    """
    Send final net weight notification to farmer's email
    after transaction is complete (mirrors send_completion_sms).
    """
    farmer = transaction.farmer

    if not farmer.email:
        return False

    subject = f"Weighing Complete — Receipt {transaction.receipt_number}"
    message = (
        f"Dear {farmer.full_name},\n\n"
        f"Your weighing is complete.\n"
        f"Gross: {transaction.gross_weight_kg} kg\n"
        f"Tare:  {transaction.tare_weight_kg} kg\n"
        f"NET WEIGHT: {transaction.net_weight_kg} kg\n"
        f"Receipt No: {transaction.receipt_number}\n"
        f"Date: {transaction.gross_time.strftime('%d/%m/%Y')}\n\n"
        f"- Weighbridge System"
    )

    return send_email(farmer.email, subject, message)


def send_gross_weight_email_async(transaction):
    """
    Fire-and-forget version: runs the (slow, SMTP-dependent) email send
    on a background thread so the request/response cycle doesn't wait
    on it. Use this from views instead of calling send_gross_weight_email
    directly.
    """
    threading.Thread(
        target=send_gross_weight_email,
        args=(transaction,),
        daemon=True
    ).start()


def send_completion_email_async(transaction):
    """
    Fire-and-forget version of send_completion_email — see
    send_gross_weight_email_async for why.
    """
    threading.Thread(
        target=send_completion_email,
        args=(transaction,),
        daemon=True
    ).start()
