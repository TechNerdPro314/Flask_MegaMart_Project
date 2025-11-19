from app import create_app, db
from app.models import User, Category, Brand, Product, ProductImage, Review, Order, OrderItem, Cart, PromoCode
import random
from datetime import datetime, timedelta
from datetime import timezone

app = create_app()
app.app_context().push()

# Создание таблиц
db.create_all()

# Очистка старых данных
print("Очистка старых данных...")
db.session.query(Cart).delete()
db.session.query(OrderItem).delete()
db.session.query(Order).delete()
db.session.query(Review).delete()
db.session.query(ProductImage).delete()
db.session.query(PromoCode).delete()
db.session.query(Product).delete()
db.session.query(Category).delete()
db.session.query(Brand).delete()
db.session.query(User).delete()
db.session.commit()

print("Создание тестовых данных...")

# Администратор
admin = User(
    email="admin@megamart.ru",
    name="Администратор",
    is_admin=True
)
admin.set_password("admin123")
db.session.add(admin)

# Обычные пользователи
users = []
user_emails = [
    "user1@example.com", "user2@example.com", "user3@example.com",
    "ivanov@example.com", "petrov@example.com", "smirnov@example.com"
]
user_names = [
    "Иван Иванов", "Петр Петров", "Сидор Сидоров",
    "Александр Иванов", "Михаил Петров", "Дмитрий Смирнов"
]

for i in range(len(user_emails)):
    user = User(
        email=user_emails[i],
        name=user_names[i],
        phone=f"+790012345{i:02d}",
        address=f"г. Москва, ул. Примерная, д. {i+1}"
    )
    user.set_password("password123")
    db.session.add(user)
    users.append(user)

db.session.flush()

# Категории (с подкатегориями)
categories_data = [
    "Смесители", "Ванны", "Унитазы", "Душевые кабины",
    "Аксессуары", "Раковины", "Трубы и фитинги"
]

categories = {}
for name in categories_data:
    cat = Category(name=name)
    db.session.add(cat)
    categories[name] = cat

db.session.flush()

# Бренды
brands_data = ["Grohe", "Hansgrohe", "Roca", "Cersanit", "Jacob Delafon", "Vitra", "Kolo", "AlcaPlast"]

brands = {}
for name in brands_data:
    brand = Brand(name=name)
    db.session.add(brand)
    brands[name] = brand

db.session.flush()

# Товары
product_names = {
    "Смесители": ["Кухонный смеситель", "Смеситель для ванны", "Душевой смеситель", "Смеситель для биде"],
    "Ванны": ["Акриловая ванна", "Стальная ванна", "Чугунная ванна", "Корнерная ванна"],
    "Унитазы": ["Напольный унитаз", "Подвесной унитаз", "Унитаз-компакт", "Биде"],
    "Душевые кабины": ["Душевая кабина 90x90", "Душевой уголок", "Душевой поддон", "Квадратная кабина"],
    "Аксессуары": ["Мыльница", "Держатель для полотенец", "Вешалка для ванной", "Дозатор для мыла"],
    "Раковины": ["Подвесная раковина", "Тумба с раковиной", "Подстольная раковина", "Раковина для биде"],
    "Трубы и фитинги": ["Полипропиленовая труба", "Металлопластик", "Фитинги для воды", "Фитинги для канализации"]
}

# Создание товаров
products = []
for category_name, products_list in product_names.items():
    for i, product_name in enumerate(products_list):
        price = random.randint(3000, 80000)
        old_price = price + random.randint(1000, 15000)

        product = Product(
            name=f"{product_name} {i+1}",
            description=f"Описание {product_name.lower()} с отличными характеристиками и высоким качеством. Подходит для современных ванных комнат.",
            price=price,
            old_price=old_price,
            sku=f"SKU-{category_name[:3].upper()}-{i+1:03d}",
            in_stock=random.randint(0, 30),
            category_id=categories[category_name].id,
            brand_id=random.choice(list(brands.values())).id
        )
        db.session.add(product)
        products.append(product)

db.session.flush()

# Добавление изображений к товарам
image_urls = [
    "https://example.com/images/sanitary_1.jpg",
    "https://example.com/images/sanitary_2.jpg",
    "https://example.com/images/sanitary_3.jpg",
    "https://example.com/images/sanitary_4.jpg",
    "https://example.com/images/sanitary_5.jpg"
]

for product in products:
    # Добавляем 1-3 изображения для каждого товара
    num_images = random.randint(1, 3)
    for j in range(num_images):
        img = ProductImage(
            product_id=product.id,
            image_url=random.choice(image_urls),
            sort_order=j
        )
        db.session.add(img)

# Добавление промокодов
promo_codes = [
    {"code": "WELCOME10", "type": "percent", "value": 10, "max_uses": 100},
    {"code": "SALE20", "type": "percent", "value": 20, "max_uses": 50},
    {"code": "NEWYEAR", "type": "fixed", "value": 1000, "max_uses": 20},
    {"code": "SUMMER25", "type": "percent", "value": 25, "max_uses": 30},
    {"code": "FREESHIP", "type": "fixed", "value": 500, "max_uses": 100}
]

for promo_data in promo_codes:
    promo = PromoCode(
        code=promo_data["code"],
        discount_type=promo_data["type"],
        value=promo_data["value"],
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        is_active=True,
        max_uses=promo_data["max_uses"],
        times_used=0
    )
    db.session.add(promo)

# Добавление отзывов
for product in products[:20]:  # Только для первых 20 товаров
    for _ in range(random.randint(0, 3)):  # 0-3 отзыва на товар
        user = random.choice(users)
        review = Review(
            rating=random.randint(3, 5),
            comment=f"Отличный товар! Очень доволен покупкой. Рекомендую к приобретению.",
            user_id=user.id,
            product_id=product.id,
            created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))
        )
        db.session.add(review)

# Добавление товаров в корзины пользователей
for user in users:
    for _ in range(random.randint(0, 5)):  # 0-5 товаров в корзине
        product = random.choice(products)
        # Проверяем, что товара еще нет в корзине у пользователя
        existing_cart = Cart.query.filter_by(user_id=user.id, product_id=product.id).first()
        if not existing_cart:
            cart_item = Cart(
                user_id=user.id,
                product_id=product.id,
                quantity=random.randint(1, 3)
            )
            db.session.add(cart_item)

db.session.flush()

# Добавление заказов
for user in users[:4]:  # Создаем заказы для первых 4 пользователей
    for _ in range(random.randint(1, 3)):  # 1-3 заказа на пользователя
        # Выбираем несколько товаров для заказа
        order_products = random.sample(products, random.randint(1, 4))

        # Рассчитываем общую сумму заказа
        total_amount = sum(float(product.price) * random.randint(1, 3) for product in order_products)

        # Случайно выбираем промокод (в 30% случаев)
        promo_code = None
        if random.random() < 0.3 and promo_codes:
            promo_code = random.choice(promo_codes)["code"]

        # Рассчитываем скидку и итоговую сумму
        discount_amount = 0
        if promo_code:
            promo = PromoCode.query.filter_by(code=promo_code).first()
            if promo and promo.is_valid()[0]:
                if promo.discount_type == "percent":
                    discount_amount = total_amount * float(promo.value / 100)
                elif promo.discount_type == "fixed":
                    discount_amount = min(float(promo.value), total_amount)

        final_amount = total_amount - discount_amount

        order = Order(
            total_amount=total_amount,
            discount_amount=discount_amount,
            final_amount=final_amount,
            promo_code=promo_code,
            status=random.choice(["Pending", "Processing", "Shipped", "Delivered", "Cancelled"]),
            shipping_address=f"г. Москва, ул. Примерная, д. {random.randint(1, 20)}, кв. {random.randint(1, 100)}",
            user_id=user.id,
            created_at=datetime.now(timezone.utc) - timedelta(days=random.randint(1, 60))
        )
        db.session.add(order)

        # Нужно выполнить flush, чтобы получить ID заказа перед добавлением элементов
        db.session.flush()

        # Добавляем элементы заказа
        for product in order_products:
            quantity = random.randint(1, 3)
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                price=float(product.price)
            )
            db.session.add(order_item)

try:
    db.session.commit()
    print("Данные успешно созданы!")
    print(f"  Админ: admin@megamart.ru / admin123")
    print(f"  Пользователей: {len(users) + 1}")  # +1 для администратора
    print(f"  Товаров: {len(products)}")
    print(f"  Категорий: {len(categories)}")
    print(f"  Брендов: {len(brands)}")
    print(f"  Промокодов: {len(promo_codes)}")
    print(f"  Заказов: {len(Order.query.all())}")
    print(f"  Отзывов: {len(Review.query.all())}")
    print(f"  Элементов корзины: {len(Cart.query.all())}")
except Exception as e:
    db.session.rollback()
    print(f"Ошибка: {e}")