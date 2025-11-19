from flask import current_app, render_template
from flask_mail import Message
from app import mail, celery


@celery.task
def send_async_email(to, subject, template, **kwargs):
    """Фоновая задача Celery для отправки email."""
    app = current_app
    msg = Message(subject, recipients=[to], sender=app.config["MAIL_DEFAULT_SENDER"])
    msg.html = render_template(template, **kwargs)
    with app.app_context():
        mail.send(msg)


def send_email(to, subject, template, **kwargs):
    """Отправляет задачу на отправку email в очередь Celery."""
    send_async_email.delay(to, subject, template, **kwargs)


def send_welcome_email(user, password=None):
    """Отправляет приветственное письмо."""
    send_email(
        user.email,
        "Добро пожаловать в MegaMart!",
        "email/welcome.html",
        user=user,
        password=password,
    )


def send_order_confirmation_email(order):
    user = order.customer
    send_email(
        user.email,
        f"Ваш заказ #{order.id} в MegaMart успешно оплачен!",
        "email/order_confirmation.html",
        order=order,
    )
