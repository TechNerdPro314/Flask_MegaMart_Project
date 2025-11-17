from flask import session, redirect, url_for, flash, request, render_template, jsonify
from flask_login import current_user, login_required
from app.models import Product, Cart, ProductImage, Order, OrderItem
from app import db
from . import cart_bp
import uuid
from yookassa import Configuration, Payment
from flask import current_app as app


# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def get_session_cart():
    if "cart" not in session:
        session["cart"] = {}
    return session["cart"]


def get_session_cart_total():
    cart = get_session_cart()
    total_price = 0
    for item in cart.values():
        total_price += item["price"] * item["quantity"]
    return total_price


def merge_session_cart_to_db():
    if "cart" in session and current_user.is_authenticated:
        session_cart = session["cart"]
        for product_id, item in session_cart.items():
            product_id = int(product_id)
            quantity = item["quantity"]

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
        session.pop("cart", None)


# --- МАРШРУТЫ ---
@cart_bp.route("/")
def cart_view():
    if current_user.is_authenticated:
        cart_items = current_user.cart_items.all()
        for item in cart_items:
            first_image = (
                ProductImage.query.filter_by(product_id=item.product_id)
                .order_by(ProductImage.sort_order)
                .first()
            )
            item.product.first_image = (
                first_image.image_url if first_image else "default_product.png"
            )
        total_price = sum(item.product.price * item.quantity for item in cart_items)
    else:
        cart_items = list(
            get_session_cart().values()
        )  # Преобразуем в список для шаблона
        total_price = get_session_cart_total()

    return render_template(
        "cart.html", title="Корзина", cart_items=cart_items, total_price=total_price
    )


@cart_bp.route("/add/<int:product_id>", methods=["POST"])
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


@cart_bp.route("/remove/<int:product_id>")
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
    return redirect(
        url_for(".cart_view")
    )  # .cart_view - относительная ссылка внутри blueprint


@cart_bp.route("/update/<int:product_id>", methods=["POST"])
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


@cart_bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart_items = current_user.cart_items.all()
    if not cart_items:
        flash("Ваша корзина пуста. Нечего оформлять.", "warning")
        return redirect(url_for("main.catalog"))

    total_price = sum(item.product.price * item.quantity for item in cart_items)
    cart_values = [
        {
            "id": item.product.id,
            "name": item.product.name,
            "price": item.product.price,
            "quantity": item.quantity,
        }
        for item in cart_items
    ]

    if request.method == "POST":
        phone = request.form.get("phone")
        address = request.form.get("address")

        if not phone or not address:
            flash("Пожалуйста, укажите телефон и адрес доставки.", "danger")
            return redirect(url_for(".checkout"))

        new_order = Order(
            user_id=current_user.id,
            total_amount=total_price,
            shipping_address=address,
            status="Pending",
        )
        db.session.add(new_order)
        db.session.commit()  # Commit to get order ID

        for item in cart_values:
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=item["id"],
                quantity=item["quantity"],
                price=item["price"],
            )
            db.session.add(order_item)

        current_user.phone = phone
        current_user.address = address
        db.session.commit()

        Configuration.account_id = app.config["YOOKASSA_SHOP_ID"]
        Configuration.secret_key = app.config["YOOKASSA_SECRET_KEY"]
        idempotency_key = str(uuid.uuid4())

        try:
            payment = Payment.create(
                {
                    "amount": {"value": f"{total_price:.2f}", "currency": "RUB"},
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
            Cart.query.filter_by(user_id=current_user.id).delete()
            db.session.commit()
            return redirect(payment.confirmation.confirmation_url)

        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при создании платежа: {e}", "danger")
            return redirect(url_for(".checkout"))

    return render_template(
        "checkout.html",
        title="Оформление заказа",
        cart_items=cart_values,
        total_price=total_price,
        user_phone=current_user.phone,
        user_address=current_user.address,
    )


@cart_bp.route("/order_success/<int:order_id>")
@login_required
def order_success(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()

    if order.status == "Paid":
        flash("Ваш заказ успешно оплачен!", "success")
    elif order.status == "Failed":
        flash(
            "Ошибка оплаты. Пожалуйста, повторите попытку или свяжитесь с нами.",
            "danger",
        )
    else:
        flash("Платеж в обработке. Статус заказа скоро обновится.", "info")

    return render_template("order_success.html", title="Статус заказа", order=order)


@cart_bp.route("/order/<int:order_id>")
@login_required
def order_details(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()
    return render_template("order.html", title=f"Заказ №{order.id}", order=order)


@cart_bp.route("/pay_order/<int:order_id>")
@login_required
def pay_order(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first_or_404()

    if order.status == "Paid":
        flash("Этот заказ уже оплачен.", "warning")
        return redirect(url_for("auth.profile"))

    Configuration.account_id = app.config["YOOKASSA_SHOP_ID"]
    Configuration.secret_key = app.config["YOOKASSA_SECRET_KEY"]

    idempotency_key = str(uuid.uuid4())
    total_price = order.total_amount

    try:
        payment = Payment.create(
            {
                "amount": {"value": f"{total_price:.2f}", "currency": "RUB"},
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


@cart_bp.route("/yookassa-webhook", methods=["POST"])
def yookassa_webhook():
    event_json = request.json
    Configuration.account_id = app.config["YOOKASSA_SHOP_ID"]
    Configuration.secret_key = app.config["YOOKASSA_SECRET_KEY"]

    try:
        event = event_json.get("event")
        payment = event_json.get("object")

        if event == "payment.succeeded":
            order_id = int(payment["metadata"]["order_id"])
            order = Order.query.get(order_id)
            if order and order.status != "Paid":
                order.status = "Paid"
                db.session.commit()

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
