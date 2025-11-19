from flask import session, redirect, url_for, flash, request, render_template, jsonify
from flask_login import current_user, login_required, login_user
from app.models import Product, Cart, ProductImage, Order, OrderItem, PromoCode, User
from app import db
from . import cart_app
import uuid
from yookassa import Configuration, Payment
from flask import current_app as app
from decimal import Decimal
from app.email import send_order_confirmation_email, send_welcome_email
import random
import string


def get_session_cart():
    if "cart" not in session:
        session["cart"] = {}
    return session["cart"]


def get_session_cart_total():
    cart = get_session_cart()
    total_price = Decimal("0.00")
    for item in cart.values():
        total_price += Decimal(item["price"]) * item["quantity"]
    return total_price


def merge_session_cart_to_db():
    if "cart" in session and current_user.is_authenticated:
        session_cart = session["cart"]
        for product_id, item in session_cart.items():
            product_id_int = int(product_id)
            quantity = item["quantity"]
            cart_item = Cart.query.filter_by(
                user_id=current_user.id, product_id=product_id_int
            ).first()
            if cart_item:
                cart_item.quantity += quantity
            else:
                cart_item = Cart(
                    user_id=current_user.id,
                    product_id=product_id_int,
                    quantity=quantity,
                )
                db.session.add(cart_item)
        try:
            db.session.commit()
            session.pop("cart", None)
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error merging session cart to DB: {e}")


@cart_app.route("/")
def cart_view():
    total_price = Decimal("0.00")
    cart_items = []
    if current_user.is_authenticated:
        cart_db_items = current_user.cart_items.all()
        for item in cart_db_items:
            first_image = (
                ProductImage.query.filter_by(product_id=item.product_id)
                .order_by(ProductImage.sort_order)
                .first()
            )
            item.product.first_image = (
                first_image.image_url if first_image else "default_product.png"
            )
        cart_items = cart_db_items
        total_price = sum(item.product.price * item.quantity for item in cart_items)
    else:
        cart_items = list(get_session_cart().values())
        total_price = get_session_cart_total()
    discount_amount = Decimal("0.00")
    final_price = total_price
    promo_code_info = session.get("promo_code")
    if promo_code_info:
        promo_code = PromoCode.query.get(promo_code_info["id"])
        if promo_code:
            is_valid, message = promo_code.is_valid()
            if is_valid:
                if promo_code.discount_type == "percent":
                    discount_amount = (total_price * promo_code.value) / 100
                else:
                    discount_amount = promo_code.value
                final_price = total_price - discount_amount
            else:
                session.pop("promo_code", None)
                flash(message, "warning")
        else:
            session.pop("promo_code", None)
    final_price = max(final_price, Decimal("0.00"))
    return render_template(
        "cart.html",
        title="Корзина",
        cart_items=cart_items,
        total_price=total_price,
        discount_amount=discount_amount,
        final_price=final_price,
        promo_code_info=promo_code_info,
    )


@cart_app.route("/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    quantity = 1
    if request.method == "POST":
        try:
            quantity = int(request.form.get("quantity", 1))
            if quantity <= 0:
                quantity = 1
        except (ValueError, TypeError):
            quantity = 1
    first_image = (
        ProductImage.query.filter_by(product_id=product_id)
        .order_by(ProductImage.sort_order)
        .first()
    )
    image_url = first_image.image_url if first_image else "default_product.png"
    if not current_user.is_authenticated:
        cart = get_session_cart()
        cart_key = str(product_id)
        if cart_key in cart:
            cart[cart_key]["quantity"] += quantity
        else:
            cart[cart_key] = {
                "id": product.id,
                "name": product.name,
                "price": float(product.price),
                "quantity": quantity,
                "image_url": image_url,
            }
        session.modified = True
    else:
        cart_item = Cart.query.filter_by(
            user_id=current_user.id, product_id=product_id
        ).first()
        if cart_item:
            cart_item.quantity += quantity
        else:
            cart_item = Cart(
                user_id=current_user.id, product_id=product_id, quantity=quantity
            )
            db.session.add(cart_item)
        db.session.commit()
    flash(f'"{product.name}" добавлен в корзину', "success")
    return redirect(request.referrer or url_for("main.index"))


@cart_app.route("/remove/<int:product_id>")
def remove_from_cart(product_id):
    if current_user.is_authenticated:
        cart_item = Cart.query.filter_by(
            user_id=current_user.id, product_id=product_id
        ).first()
        if cart_item:
            db.session.delete(cart_item)
            db.session.commit()
    else:
        cart = get_session_cart()
        product_key = str(product_id)
        if product_key in cart:
            del cart[product_key]
            session.modified = True
    flash("Товар удален из корзины.", "info")
    return redirect(url_for(".cart_view"))


@cart_app.route("/update/<int:product_id>", methods=["POST"])
def update_cart(product_id):
    quantity_str = request.form.get("quantity")
    try:
        quantity = int(quantity_str)
    except (ValueError, TypeError):
        flash("Некорректное количество.", "danger")
        return redirect(url_for(".cart_view"))
    if current_user.is_authenticated:
        cart_item = Cart.query.filter_by(
            user_id=current_user.id, product_id=product_id
        ).first()
        if cart_item:
            if quantity > 0:
                cart_item.quantity = quantity
                flash("Количество обновлено.", "success")
            else:
                db.session.delete(cart_item)
                flash("Товар удален из корзины.", "info")
            db.session.commit()
    else:
        cart = get_session_cart()
        product_key = str(product_id)
        if product_key in cart:
            if quantity > 0:
                cart[product_key]["quantity"] = quantity
                flash("Количество обновлено.", "success")
            else:
                del cart[product_key]
                flash("Товар удален из корзины.", "info")
            session.modified = True
    return redirect(url_for(".cart_view"))


@cart_app.route("/checkout", methods=["GET", "POST"])
def checkout():
    user = current_user
    cart_items = []
    if not user.is_authenticated:
        cart_items = list(get_session_cart().values())
        total_price = get_session_cart_total()
    else:
        cart_items = user.cart_items.all()
        total_price = sum(item.product.price * item.quantity for item in cart_items)
    if not cart_items:
        flash("Ваша корзина пуста.", "warning")
        return redirect(url_for("main.catalog"))
    discount_amount = Decimal("0.00")
    final_price = total_price
    promo_code = None
    promo_code_info = session.get("promo_code")
    if promo_code_info:
        promo_code = PromoCode.query.get(promo_code_info["id"])
        if promo_code:
            is_valid, message = promo_code.is_valid()
            if is_valid:
                if promo_code.discount_type == "percent":
                    discount_amount = (total_price * promo_code.value) / 100
                else:
                    discount_amount = promo_code.value
                final_price = total_price - discount_amount
            else:
                promo_code = None
                session.pop("promo_code", None)
                flash(message, "warning")
        else:
            session.pop("promo_code", None)
    final_price = max(final_price, Decimal("0.00"))
    if request.method == "POST":
        phone = request.form.get("phone")
        address = request.form.get("address")
        form_data_for_render = {
            "cart_items": cart_items,
            "total_price": total_price,
            "user_phone": phone,
            "user_address": address,
            "discount_amount": discount_amount,
            "final_price": final_price,
        }
        if not phone or not address:
            flash("Пожалуйста, укажите телефон и адрес доставки.", "danger")
            return render_template(
                "checkout.html", title="Оформление заказа", **form_data_for_render
            )
        if not user.is_authenticated:
            name = request.form.get("name")
            email = request.form.get("email")
            if not name or not email:
                flash("Пожалуйста, укажите ваше имя и email.", "danger")
                return render_template(
                    "checkout.html",
                    title="Оформление заказа",
                    **form_data_for_render,
                    user_name=name,
                    user_email=email,
                )
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash(
                    "Пользователь с таким email уже существует. Пожалуйста, войдите, чтобы продолжить.",
                    "info",
                )
                return redirect(url_for("auth.login", next=url_for(".checkout")))
            try:
                password = "".join(
                    random.choices(string.ascii_letters + string.digits, k=10)
                )
                user = User(
                    email=email,
                    name=name,
                    phone=phone,
                    address=address,
                    password_generated=True,
                )
                user.set_password(password)
                db.session.add(user)
                db.session.flush()
                send_welcome_email(user, password=password)
                login_user(user)
                merge_session_cart_to_db()
                cart_items = user.cart_items.all()
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Error creating guest user: {e}")
                flash(
                    "Произошла ошибка при создании вашего аккаунта. Попробуйте снова.",
                    "danger",
                )
                return redirect(url_for(".checkout"))
        new_order = Order(
            user_id=user.id,
            total_amount=total_price,
            discount_amount=discount_amount,
            final_amount=final_price,
            promo_code=promo_code.code if promo_code else None,
            shipping_address=address,
            status="Pending",
        )
        db.session.add(new_order)
        db.session.flush()
        order_items_data = user.cart_items.all()
        for item in order_items_data:
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=item.product.id,
                quantity=item.quantity,
                price=item.product.price,
            )
            db.session.add(order_item)
        user.phone = phone
        user.address = address
        if promo_code:
            promo_code.times_used += 1
        Configuration.account_id = app.config["YOOKASSA_SHOP_ID"]
        Configuration.secret_key = app.config["YOOKASSA_SECRET_KEY"]
        idempotency_key = str(uuid.uuid4())
        try:
            payment = Payment.create(
                {
                    "amount": {"value": f"{final_price:.2f}", "currency": "RUB"},
                    "confirmation": {
                        "type": "redirect",
                        "return_url": url_for(
                            ".order_success", order_id=new_order.id, _external=True
                        ),
                    },
                    "capture": True,
                    "description": f"Заказ №{new_order.id} в MegaMart",
                    "metadata": {"order_id": new_order.id},
                },
                idempotency_key,
            )
            new_order.payment_id = payment.id
            Cart.query.filter_by(user_id=user.id).delete()
            session.pop("promo_code", None)
            db.session.commit()
            return redirect(payment.confirmation.confirmation_url)
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при создании платежа: {e}", "danger")
            return redirect(url_for(".checkout"))
    return render_template(
        "checkout.html",
        title="Оформление заказа",
        cart_items=cart_items,
        total_price=total_price,
        user_phone=user.phone if user.is_authenticated else "",
        user_address=user.address if user.is_authenticated else "",
        discount_amount=discount_amount,
        final_price=final_price,
    )


@cart_app.route("/order_success/<int:order_id>")
@login_required
def order_success(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    return render_template("order_success.html", title="Статус заказа", order=order)


@cart_app.route("/order/<int:order_id>")
@login_required
def order_details(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    return render_template("order.html", title=f"Заказ №{order.id}", order=order)


@cart_app.route("/pay_order/<int:order_id>")
@login_required
def pay_order(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    if order.status == "Paid":
        flash("Этот заказ уже оплачен.", "warning")
        return redirect(url_for("auth.profile"))
    Configuration.account_id = app.config["YOOKASSA_SHOP_ID"]
    Configuration.secret_key = app.config["YOOKASSA_SECRET_KEY"]
    idempotency_key = str(uuid.uuid4())
    final_price_to_pay = order.final_amount
    try:
        payment = Payment.create(
            {
                "amount": {"value": f"{final_price_to_pay:.2f}", "currency": "RUB"},
                "confirmation": {
                    "type": "redirect",
                    "return_url": url_for(
                        ".order_success", order_id=order.id, _external=True
                    ),
                },
                "capture": True,
                "description": f"Повторная оплата заказа №{order.id} в MegaMart",
                "metadata": {"order_id": order.id},
            },
            idempotency_key,
        )
        order.payment_id = payment.id
        db.session.commit()
        return redirect(payment.confirmation.confirmation_url)
    except Exception as e:
        flash(f"Ошибка при создании платежа: {e}", "danger")
        return redirect(url_for("auth.profile"))


@cart_app.route("/yookassa-webhook", methods=["POST"])
def yookassa_webhook():
    event_json = request.json
    try:
        event = event_json.get("event")
        payment = event_json.get("object")
        if event == "payment.succeeded":
            order_id = int(payment["metadata"]["order_id"])
            order = Order.query.get(order_id)
            if order and order.status != "Paid":
                order.status = "Paid"
                db.session.commit()
                send_order_confirmation_email(order)
        elif event in ["payment.canceled", "payment.failed"]:
            order_id = int(payment["metadata"]["order_id"])
            order = Order.query.get(order_id)
            if order and order.status != "Paid":
                order.status = "Failed"
                db.session.commit()
    except Exception as e:
        app.logger.error(f"Ошибка обработки Webhook YooKassa: {e}")
        return jsonify({"status": "error"}), 500
    return jsonify({"status": "ok"}), 200


@cart_app.route("/apply_promo", methods=["POST"])
def apply_promo():
    code = request.form.get("promo_code", "").strip().upper()
    if not code:
        flash("Пожалуйста, введите промокод.", "warning")
        return redirect(url_for(".cart_view"))
    promo_code = PromoCode.query.filter_by(code=code).first()
    if not promo_code:
        flash("Такой промокод не найден.", "danger")
        return redirect(url_for(".cart_view"))
    is_valid, message = promo_code.is_valid()
    if not is_valid:
        flash(message, "danger")
        return redirect(url_for(".cart_view"))
    session["promo_code"] = {
        "id": promo_code.id,
        "code": promo_code.code,
        "type": promo_code.discount_type,
        "value": float(promo_code.value),
    }
    flash(f'Промокод "{promo_code.code}" успешно применен!', "success")
    return redirect(url_for(".cart_view"))


@cart_app.route("/remove_promo")
def remove_promo():
    if "promo_code" in session:
        session.pop("promo_code")
        flash("Промокод удален.", "info")
    return redirect(url_for(".cart_view"))
