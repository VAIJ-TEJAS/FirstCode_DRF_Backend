from __future__ import annotations

import os

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.mail.backends.smtp import EmailBackend
from django.template.loader import render_to_string


def _is_non_smtp_backend() -> bool:
    backend = str(getattr(settings, "EMAIL_BACKEND", "") or "")
    # Common local/dev backends: console, filebased, locmem
    return any(
        token in backend.lower()
        for token in [
            "consoleemailbackend",
            "filebasedemailbackend",
            "locmememailbackend",
            "dummyemailbackend",
        ]
    )


def send_email_with_dynamic_sender(
    subject,
    message,
    from_email,
    recipient_list,
    template,
    context,
    fail_silently=False,
):
    """
    Send email while allowing per-sender SMTP config in production.

    In local/docker environments (console backend), we intentionally respect
    Django's configured EMAIL_BACKEND so OTP/reset flows work without SMTP.
    """

    # Allow explicit override to disable SMTP and always use configured backend.
    if _is_non_smtp_backend() or os.getenv("DISABLE_SMTP_SENDING", "").strip().lower() in {"1", "true", "yes", "on"}:
        connection = get_connection()  # Uses settings.EMAIL_BACKEND
    else:
        # Per-sender SMTP settings are read from environment variables.
        # If not provided, fall back to the project's configured email backend.
        if from_email == "noreply@firstcode.in":
            host = os.getenv("NOREPLY_EMAIL_HOST")
            port = int(os.getenv("NOREPLY_EMAIL_PORT", "465"))
            username = os.getenv("NOREPLY_EMAIL_USER")
            password = os.getenv("NOREPLY_EMAIL_PASSWORD")
            use_ssl = os.getenv("NOREPLY_EMAIL_USE_SSL", "true").lower() in {"1", "true", "yes", "on"}
            use_tls = os.getenv("NOREPLY_EMAIL_USE_TLS", "false").lower() in {"1", "true", "yes", "on"}
        elif from_email == "updates@firstcode.in":
            host = os.getenv("UPDATES_EMAIL_HOST")
            port = int(os.getenv("UPDATES_EMAIL_PORT", "465"))
            username = os.getenv("UPDATES_EMAIL_USER")
            password = os.getenv("UPDATES_EMAIL_PASSWORD")
            use_ssl = os.getenv("UPDATES_EMAIL_USE_SSL", "true").lower() in {"1", "true", "yes", "on"}
            use_tls = os.getenv("UPDATES_EMAIL_USE_TLS", "false").lower() in {"1", "true", "yes", "on"}
        else:
            host = username = password = None
            port = 465
            use_ssl = True
            use_tls = False

        if host and username and password:
            connection = EmailBackend(
                host=host,
                port=port,
                username=username,
                password=password,
                use_tls=use_tls,
                use_ssl=use_ssl,
            )
        else:
            connection = get_connection()

    html_content = render_to_string(template, context)

    email = EmailMultiAlternatives(
        subject=subject,
        body=message,
        from_email=from_email,
        to=recipient_list,
        connection=connection,
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=fail_silently)
