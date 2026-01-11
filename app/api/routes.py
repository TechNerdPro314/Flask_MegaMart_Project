from flask import jsonify, request, url_for, current_app
from flask_login import login_required, current_user
from app.models import Product, Cart
from app import db, limiter
from . import api_bp
from .schemas import (
    CartAddItemSchema,
    CartRemoveItemSchema,
    CartUpdateItemSchema,
    WishlistItemSchema,
)


@api_bp.route("/cart/add", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def api_add_to_cart():
    """AJAX: Добавить товар в корзину"""
    data = request.get_json()
    schema = CartAddItemSchema()
    errors = schema.validate(data)
    if errors:
        return jsonify({"success": False, "error": errors}), 400

    try:
        product_id = data["product_id"]
        quantity = data["quantity"]

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
        current_app.logger.error(f"Error in api_add_to_cart: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@api_bp.route("/cart/remove", methods=["POST"])
@login_required
def api_remove_from_cart():
    """AJAX: Удалить товар из корзины"""
    data = request.get_json()
    schema = CartRemoveItemSchema()
    errors = schema.validate(data)
    if errors:
        return jsonify({"success": False, "error": errors}), 400

    try:
        product_id = data["product_id"]
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
        current_app.logger.error(f"Error in api_remove_from_cart: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@api_bp.route("/cart/update", methods=["POST"])
@login_required
def api_update_cart():
    """AJAX: Обновить количество товара"""
    data = request.get_json()
    schema = CartUpdateItemSchema()
    errors = schema.validate(data)
    if errors:
        return jsonify({"success": False, "error": errors}), 400

    try:
        product_id = data["product_id"]
        quantity = data["quantity"]

        if quantity <= 0:
            cart_item = Cart.query.filter_by(
                user_id=current_user.id, product_id=product_id
            ).first()
            if cart_item:
                db.session.delete(cart_item)
        else:
            product = Product.query.get_or_404(product_id)
            if product.in_stock < quantity:
                return jsonify({"success": False, "error": "Недостаточно товара"}), 400

            cart_item = Cart.query.filter_by(
                user_id=current_user.id, product_id=product_id
            ).first()
            if cart_item:
                cart_item.quantity = quantity
            else:
                cart_item = Cart(
                    user_id=current_user.id, product_id=product_id, quantity=quantity
                )
                db.session.add(cart_item)

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
        current_app.logger.error(f"Error in api_update_cart: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@api_bp.route("/search/autocomplete")
def autocomplete():
    """AJAX: Получить подсказки для поиска"""
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return jsonify([])

    products = Product.query.filter(Product.name.ilike(f"%{query}%")).limit(5).all()
    results = [
        {"name": p.name, "url": url_for("main.product", product_id=p.id)}
        for p in products
    ]
    return jsonify(results)


@api_bp.route("/wishlist/toggle", methods=["POST"])
@login_required
def toggle_wishlist():
    """AJAX: Добавить или удалить товар из списка желаний"""
    data = request.get_json()
    schema = WishlistItemSchema()
    errors = schema.validate(data)
    if errors:
        return jsonify({"success": False, "error": errors}), 400

    product_id = data.get("product_id")
    product = Product.query.get_or_404(product_id)

    is_in_wishlist = current_user.wishlist.filter_by(id=product_id).first()

    try:
        if is_in_wishlist:
            current_user.wishlist.remove(product)
            db.session.commit()
            return jsonify(
                {
                    "success": True,
                    "action": "removed",
                    "message": "Удалено из избранного",
                }
            )
        else:
            current_user.wishlist.append(product)
            db.session.commit()
            return jsonify(
                {"success": True, "action": "added", "message": "Добавлено в избранное"}
            )
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in toggle_wishlist: {e}")
        return jsonify({"success": False, "error": "Internal server error"}), 500
