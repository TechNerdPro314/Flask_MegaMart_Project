from flask import render_template, redirect, url_for, flash, request, session
from flask_login import current_user, login_required
from app import db
from app.models import Order, OrderItem, Product, Cart
from app.services.cart_service import CartService
from . import cart_app
from decimal import Decimal


def merge_session_cart_to_db():
    """
    Объединяет содержимое корзины из сессии с корзиной в базе данных.
    Вызывается при входе пользователя в систему.
    """
    if 'cart' in session:
        for item_data in session['cart']:
            product_id = item_data['product_id']
            quantity = item_data['quantity']

            # Проверяем, есть ли уже такой товар в корзине пользователя
            existing_item = Cart.query.filter_by(
                user_id=current_user.id,
                product_id=product_id
            ).first()

            if existing_item:
                # Обновляем количество
                existing_item.quantity += quantity
            else:
                # Добавляем новый товар в корзину
                new_item = Cart(
                    user_id=current_user.id,
                    product_id=product_id,
                    quantity=quantity
                )
                db.session.add(new_item)

        # Очищаем корзину из сессии после объединения
        session.pop('cart', None)
        db.session.commit()

@cart_app.route("/")
def cart_view():
    # Используем сервис для получения данных без N+1
    cart_items, total_price = CartService.get_cart_items(current_user)

    # Логика промокодов (упрощено для краткости)
    discount = Decimal("0.00")
    final_price = total_price

    return render_template(
        "cart.html",
        cart_items=cart_items,
        total_price=total_price,
        discount_amount=discount,
        final_price=final_price
    )

@cart_app.route("/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    qty = int(request.form.get("quantity", 1))
    success, message = CartService.add_item(current_user, product_id, qty)

    flash(message, "success" if success else "danger")
    return redirect(request.referrer or url_for("main.index"))

@cart_app.route("/checkout", methods=["POST"])
@login_required
def checkout():
    """Безопасное оформление заказа с использованием транзакций БД."""
    try:
        # Используем транзакцию
        with db.session.begin_nested():
            # 1. Получаем корзину
            cart_items = Cart.query.filter_by(user_id=current_user.id).all()
            if not cart_items:
                flash("Корзина пуста", "warning")
                return redirect(url_for("main.catalog"))

            total_amount = Decimal("0.00")

            # Создаем объект заказа
            order = Order(
                user_id=current_user.id,
                status="Pending",
                shipping_address=current_user.address,
                total_amount=0, # Обновим позже
                final_amount=0
            )
            db.session.add(order)
            db.session.flush() # Получаем ID заказа

            for item in cart_items:
                # 2. БЛОКИРУЕМ СТРОКУ ТОВАРА (Anti-Race Condition)
                # Это гарантирует, что никто не купит товар, пока мы обрабатываем транзакцию
                product = Product.query.with_for_update().get(item.product_id)

                if product.in_stock < item.quantity:
                    raise Exception(f"Товар {product.name} закончился, пока вы оформляли заказ")

                # 3. Списываем остатки
                product.in_stock -= item.quantity

                # 4. Создаем элемент заказа
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=item.quantity,
                    price=product.price
                )
                db.session.add(order_item)
                total_amount += product.price * item.quantity

            order.total_amount = total_amount
            order.final_amount = total_amount # С учетом возможных скидок

            # 5. Очищаем корзину
            Cart.query.filter_by(user_id=current_user.id).delete()

        db.session.commit()
        flash(f"Заказ #{order.id} успешно оформлен!", "success")
        return redirect(url_for("auth.profile"))

    except Exception as e:
        db.session.rollback()
        flash(f"Ошибка оформления: {str(e)}", "danger")
        return redirect(url_for("cart_app.cart_view"))