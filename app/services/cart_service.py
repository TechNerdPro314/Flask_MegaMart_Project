from flask import session
from app.models import Cart, Product, ProductImage, db
from decimal import Decimal
from sqlalchemy.orm import joinedload

class CartService:
    @staticmethod
    def get_cart_items(user):
        """
        Возвращает стандартизированный список элементов корзины и общую сумму.
        Устраняет проблему N+1 с помощью joinedload.
        """
        total_price = Decimal("0.00")
        standardized_items = []

        if user.is_authenticated:
            # Оптимизированный запрос: загружаем продукт и его картинки за один раз
            db_items = Cart.query.filter_by(user_id=user.id).options(
                joinedload(Cart.product).joinedload(Product.images)
            ).all()

            for item in db_items:
                main_img = next((img.image_url for img in item.product.images if img.sort_order == 0), "default_product.png")
                standardized_items.append({
                    "product": item.product,
                    "quantity": item.quantity,
                    "price": item.product.price,
                    "image_url": main_img,
                    "subtotal": item.product.price * item.quantity
                })
                total_price += item.product.price * item.quantity
        else:
            # Логика для анонимных пользователей (сессии)
            session_cart = session.get("cart", {})
            if session_cart:
                # Загружаем продукты из сессии одним запросом
                product_ids = [int(p_id) for p_id in session_cart.keys()]
                products = Product.query.filter(Product.id.in_(product_ids)).options(joinedload(Product.images)).all()
                
                for product in products:
                    qty = session_cart[str(product.id)]["quantity"]
                    main_img = next((img.image_url for img in product.images if img.sort_order == 0), "default_product.png")
                    subtotal = product.price * qty
                    standardized_items.append({
                        "product": product,
                        "quantity": qty,
                        "price": product.price,
                        "image_url": main_img,
                        "subtotal": subtotal
                    })
                    total_price += subtotal
                    
        return standardized_items, total_price

    @staticmethod
    def add_item(user, product_id, quantity):
        """Добавляет товар в корзину с проверкой остатков."""
        product = Product.query.get_or_404(product_id)
        if product.in_stock < quantity:
            return False, f"Недостаточно товара {product.name} (в наличии: {product.in_stock})"

        if user.is_authenticated:
            item = Cart.query.filter_by(user_id=user.id, product_id=product_id).first()
            if item:
                item.quantity += quantity
            else:
                item = Cart(user_id=user.id, product_id=product_id, quantity=quantity)
                db.session.add(item)
            db.session.commit()
        else:
            cart = session.get("cart", {})
            p_id_str = str(product_id)
            if p_id_str in cart:
                cart[p_id_str]["quantity"] += quantity
            else:
                cart[p_id_str] = {"quantity": quantity}
            session["cart"] = cart
            session.modified = True
            
        return True, "Успешно добавлено"