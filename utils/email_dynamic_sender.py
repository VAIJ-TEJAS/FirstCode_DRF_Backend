from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.core.mail.backends.smtp import EmailBackend

def send_email_with_dynamic_sender(subject, message, from_email, recipient_list, template, context, fail_silently=False):
    # Define your email settings for each sender email
    email_settings = {
        "noreply@firstcode.in": {
            "EMAIL_HOST": 'smtp.zoho.in',
            "EMAIL_PORT": 465,
            "EMAIL_HOST_USER": 'noreply@firstcode.in',
            "EMAIL_HOST_PASSWORD": 't2x_wdw~ekD_e_+',
            "EMAIL_USE_SSL": True,
        },
        "updates@firstcode.in": {
            "EMAIL_HOST": 'smtp.zoho.in',
            "EMAIL_PORT": 465,
            "EMAIL_HOST_USER": 'updates@firstcode.in',
            "EMAIL_HOST_PASSWORD": 'u2x_wdw~ekD_e_+',
            "EMAIL_USE_SSL": True,
        },
    }

    # Select the email settings based on the `from_email` argument
    selected_settings = email_settings.get(from_email)


    # Create an email backend instance with the selected settings
    email_backend = EmailBackend(
        host=selected_settings["EMAIL_HOST"],
        port=selected_settings["EMAIL_PORT"],
        username=selected_settings["EMAIL_HOST_USER"],
        password=selected_settings["EMAIL_HOST_PASSWORD"],
        use_tls=selected_settings.get("EMAIL_USE_TLS", False),
        use_ssl=selected_settings.get("EMAIL_USE_SSL", False)
    )

    # Render the HTML template with the context
    html_content = render_to_string(template, context)

    # Send the email using the configured backend
    email = EmailMultiAlternatives(
        subject=subject,
        body=message,  # Fallback message for non-HTML email clients
        from_email=from_email,
        to=recipient_list,
        connection=email_backend
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=fail_silently)
