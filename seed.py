from app import create_app, db
from app.models import User, Category, Brand, Product
import random

app = create_app()
app.app_context().push()

# Создание таблиц
db.create_all()

# Очистка старых данных
print("Очистка старых данных...")
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

# Категории
categories_data = [
    "Смесители", "Ванны", "Унитазы", "Душевые кабины", 
    "Аксессуары", "Раковины", "Трубы и фитинги"
]

categories = {}
for name in categories_data:
    cat = Category(name=name)
    db.session.add(cat)
    categories[name] = cat

# Бренды
brands_data = ["Grohe", "Hansgrohe", "Roca", "Cersanit", "Jacob Delafon", "Vitra"]

brands = {}
for name in brands_data:
    brand = Brand(name=name)
    db.session.add(brand)
    brands[name] = brand

db.session.flush()

# Товары
product_names = {
    "Смесители": ["Кухонный смеситель", "Смеситель для ванны", "Душевой смеситель"],
    "Ванны": ["Акриловая ванна", "Стальная ванна", "Чугунная ванна"],
    "Унитазы": ["Напольный унитаз", "Подвесной унитаз", "Унитаз-компакт"],
    "Душевые кабины": ["Душевая кабина 90x90", "Душевой уголок", "Душевой поддон"],
    "Аксессуары": ["Мыльница", "Держатель для полотенец", "Вешалка для ванной"]
}

for category_name, products in product_names.items():
    for i, product_name in enumerate(products):
        price = random.randint(5000, 50000)
        old_price = price + random.randint(1000, 10000)
        
        product = Product(
            name=f"{product_name} {i+1}",
            description=f"Описание {product_name.lower()} с отличными характеристиками",
            price=price,
            old_price=old_price,
            sku=f"SKU-{category_name[:3].upper()}-{i+1:03d}",
            in_stock=random.randint(0, 20),
            category_id=categories[category_name].id,
            brand_id=random.choice(list(brands.values())).id
        )
        db.session.add(product)

try:
    db.session.commit()
    print("✅ Данные успешно созданы!")
    print(f"  Админ: admin@megamart.ru / admin123")
    print(f"  Товаров: {Product.query.count()}")
    print(f"  Категорий: {Category.query.count()}")
    print(f"  Брендов: {Brand.query.count()}")
except Exception as e:
    db.session.rollback()
    print(f"❌ Ошибка: {e}")