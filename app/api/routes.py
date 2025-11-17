from flask import jsonify, request
from flask_login import login_required, current_user
from app.models import Product, Cart
from app import db
from . import api_bp


@api_bp.route("/cart/add", methods=["POST"])
@login_required
def api_add_to_cart():
    """AJAX: Добавить товар в корзину"""
    try:
        data = request.get_json()
        product_id = int(data.get("product_id"))
        quantity = int(data.get("quantity", 1))

        if quantity <= 0:
            return jsonify({"success": False, "error": "Неверное количество"}), 400

        product = Product.query.get_or_404(product_id)

        if product.in_stock < quantity:
            return jsonify({"success": False, "error": "Нет в наличии"}), 400

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

        cart_count = sum(item.quantity for item in current_user.cart_items.all())
        return jsonify(
            {
                "success": True,
                "message": f"Добавлено: {product.name}",
                "cart_count": cart_count,
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/cart/remove", methods=["POST"])
@login_required
def api_remove_from_cart():
    """AJAX: Удалить товар из корзины"""
    try:
        data = request.get_json()
        product_id = int(data.get("product_id"))

        cart_item = Cart.query.filter_by(
            user_id=current_user.id, product_id=product_id
        ).first()

        if cart_item:
            db.session.delete(cart_item)
            db.session.commit()

        cart_count = sum(item.quantity for item in current_user.cart_items.all())
        return jsonify({"success": True, "cart_count": cart_count})

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/cart/update", methods=["POST"])
@login_required
def api_update_cart():
    """AJAX: Обновить количество товара"""
    try:
        data = request.get_json()
        product_id = int(data.get("product_id"))
        quantity = int(data.get("quantity"))

        if quantity <= 0:
            # Если количество 0 или меньше, удаляем товар
            cart_item = Cart.query.filter_by(
                user_id=current_user.id, product_id=product_id
            ).first()
            if cart_item:
                db.session.delete(cart_item)
                db.session.commit()
        else:
            product = Product.query.get_or_404(product_id)
            if product.in_stock < quantity:
                return jsonify({"success": False, "error": "Недостаточно товара"}), 400

            cart_item = Cart.query.filter_by(
                user_id=current_user.id, product_id=product_id
            ).first()
            if cart_item:
                cart_item.quantity = quantity
                db.session.commit()

        total_price = sum(
            item.product.price * item.quantity for item in current_user.cart_items.all()
        )
        cart_count = sum(item.quantity for item in current_user.cart_items.all())

        return jsonify(
            {
                "success": True,
                "total_price": float(total_price),
                "cart_count": cart_count,
            }
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
