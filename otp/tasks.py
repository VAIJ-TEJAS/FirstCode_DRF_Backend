from celery import shared_task
from django.core.mail import send_mail

@shared_task
def send_welcome_email(email, username):
    subject = "Welcome to Our Service!"
    message = (
        f"Dear {username},\n\n"
        "Thank you for signing up with us! We're excited to have you on board.\n"
        "If you have any questions, feel free to reach out.\n\n"
        "Best regards,\nYour Company Name"
    )
    
    from_email = "noreply@firstcode.in" 
    recipient_list = [email]
    
    send_mail(subject, message, from_email, recipient_list)
