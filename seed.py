from app import create_app, db
from app.models import User, Category, Brand, Product, ProductImage
import random

app = create_app()
app.app_context().push()

# --- 1. Очистка старых данных ---
print("Очистка старых данных...")
db.session.query(ProductImage).delete()
db.session.query(Product).delete()
db.session.query(Category).delete()
db.session.query(Brand).delete()
db.session.query(User).delete()
db.session.commit()

print("Создание новой структуры данных по ТЗ...")

# --- 2. Администратор ---
admin = User(
    email="admin@megamart.ru",
    name="Администратор",
    is_admin=True
)
admin.set_password("admin123")
db.session.add(admin)

# --- 3. Категории из ТЗ (16 шт) ---
categories_config = {
    "Унитазы": "fa-toilet",
    "Раковины": "fa-sink",
    "Смесители": "fa-faucet",
    "Душевые программы": "fa-shower",
    "Душевые кабины и ограждения": "fa-dungeon",
    "Ванны": "fa-bath",
    "Инсталляции": "fa-wrench",
    "Комплекты с унитазом": "fa-layer-group",
    "Кухонные мойки": "fa-utensils",
    "Фильтры и аксессуары": "fa-filter",
    "Полотенцесушители": "fa-hot-tub-person",
    "Слив и канализация": "fa-arrow-down",
    "Водонагреватели": "fa-temperature-high",
    "Теплые полы": "fa-border-all",
    "Биде": "fa-tint",
    "Писсуары": "fa-restroom"
}

categories = {}
for name, icon in categories_config.items():
    cat = Category(name=name)
    db.session.add(cat)
    categories[name] = cat

# --- 4. Бренды ---
# Расширенный список брендов для покрытия всех категорий
brands_data = [
    "Grohe", "Hansgrohe", "Roca", "Cersanit", "Jacob Delafon", "Vitra", 
    "Geberit", "Laufen", "STWORKI", "Ravak", "Wasserkraft", "Aquaton", 
    "Thermex", "Electrolux", "Viega", "AlcaPlast", "Omoikiri", "Franke"
]
brands = {}
for name in brands_data:
    brand = Brand(name=name)
    db.session.add(brand)
    brands[name] = brand

db.session.flush()

# --- 5. Генераторы Характеристик (SPEC GENERATORS) ---

def get_toilet_specs(subtype):
    is_hanging = "Подвесной" in subtype
    return {
        "Размеры": {
            "Длина, см": str(random.randint(48, 60)),
            "Ширина, см": str(random.randint(34, 37)),
            "Высота, см": str(random.randint(35, 42) if is_hanging else random.randint(75, 85))
        },
        "Исполнение": {
            "Монтаж": "Подвесной" if is_hanging else "Напольный",
            "Выпуск": "Горизонтальный",
            "Безободковый": "Да" if random.choice([True, False]) else "Нет"
        },
        "Внешний вид": {
            "Цвет": "Белый",
            "Поверхность": "Глянцевая",
            "Стилистика": "Современный"
        },
        "Материал": {"Материал": "Санфарфор"},
        "Особенности": {"Сиденье с микролифтом": "Да", "Антивсплеск": "Есть"}
    }

def get_sink_specs(subtype):
    width = random.choice([50, 60, 70, 80, 100])
    return {
        "Размеры": {"Ширина, см": str(width), "Глубина, см": str(random.randint(35, 50))},
        "Монтаж": {"Тип установки": subtype.replace("Раковина ", "").capitalize()},
        "Материал": {"Материал": random.choice(["Санфарфор", "Фаянс", "Искусственный камень"])},
        "Внешний вид": {"Форма": random.choice(["Прямоугольная", "Овальная", "Круглая"])}
    }

def get_mixer_specs(subtype):
    color = random.choice(["Хром", "Черный матовый", "Белый", "Золото"])
    return {
        "Исполнение": {
            "Назначение": subtype,
            "Управление": random.choice(["Рычажное", "Двухвентильное", "Сенсорное"]),
            "Материал": "Латунь"
        },
        "Внешний вид": {"Цвет": color, "Поверхность": "Матовая" if "матовый" in color else "Глянцевая"},
        "Размеры": {"Высота излива, см": str(random.randint(10, 25))},
        "Монтаж": {"Стандарт подводки": "1/2\"", "Отверстия": "1"}
    }

def get_bath_specs(material):
    length = random.choice([150, 160, 170, 180])
    return {
        "Габариты": {"Длина, см": str(length), "Ширина, см": str(random.choice([70, 75, 80])), "Объем, л": str(random.randint(180, 260))},
        "Материал": {"Материал": material, "Толщина": "4-6 мм" if material == "Акрил" else "8-10 мм"},
        "Функции": {"Гидромассаж": "Есть" if random.random() > 0.7 else "Нет"}
    }

def get_shower_program_specs(subtype):
    return {
        "Характеристики": {
            "Тип": subtype, # Душевая стойка / Панель
            "Тропический душ": "Есть",
            "Ручной душ": "3 режима",
            "Смеситель": "Термостатический" if random.random() > 0.5 else "Механический"
        },
        "Материал": {"Материал штанги": "Нержавеющая сталь", "Покрытие": "Хром"},
        "Монтаж": {"Установка": "Настенная"}
    }

def get_shower_cabin_specs():
    size = random.choice(["90x90", "100x100", "120x80"])
    return {
        "Габариты": {"Размер, см": size, "Высота, см": "215"},
        "Конструкция": {
            "Форма": random.choice(["Четверть круга", "Квадратная", "Прямоугольная"]),
            "Поддон": random.choice(["Низкий", "Средний", "Высокий"]),
            "Двери": "Раздвижные"
        },
        "Стекло": {"Тип стекла": "Закаленное", "Исполнение": random.choice(["Прозрачное", "Матовое", "Тонированное"])},
        "Функции": {"Тропический душ": "Есть"}
    }

def get_installation_specs():
    return {
        "Назначение": {"Для": "Подвесного унитаза"},
        "Габариты": {"Ширина, см": "50", "Глубина, см": "12-20", "Высота, см": "112"},
        "Комплектация": {
            "Кнопка смыва": "В комплекте" if random.random() > 0.3 else "Приобретается отдельно",
            "Крепеж": "Есть",
            "Звукоизоляция": "Есть"
        },
        "Характеристики": {"Режим смыва": "Двойной (3/6 л)", "Механизм": "Механический"}
    }

def get_kitchen_sink_specs():
    return {
        "Габариты": {"Ширина шкафа, см": random.choice(["45", "50", "60"]), "Длина мойки, см": str(random.randint(40, 80))},
        "Материал": {"Материал": random.choice(["Нержавеющая сталь", "Искусственный гранит", "Керамика"])},
        "Конструкция": {
            "Количество чаш": random.choice(["1 основная", "1.5 чаши", "2 чаши"]),
            "Крыло": "Есть" if random.random() > 0.5 else "Нет",
            "Форма": random.choice(["Прямоугольная", "Круглая", "Квадратная"])
        },
        "Цвет": {"Цвет": random.choice(["Сталь", "Черный", "Бежевый", "Серый"])}
    }

def get_towel_warmer_specs():
    type_ = random.choice(["Водяной", "Электрический"])
    return {
        "Основные": {"Тип": type_, "Форма": random.choice(["Лесенка", "М-образный", "Фокстрот"])},
        "Размеры": {
            "Высота, см": str(random.choice([50, 60, 80, 100])),
            "Ширина, см": str(random.choice([40, 50, 60]))
        },
        "Материал": {"Материал": "Нержавеющая сталь AISI 304"},
        "Подключение": {"Тип подключения": "Нижнее" if type_ == "Водяной" else "Скрытое/Вилка"}
    }

def get_water_heater_specs():
    volume = random.choice([30, 50, 80, 100])
    return {
        "Основные": {
            "Тип": "Накопительный",
            "Объем, л": str(volume),
            "Установка": random.choice(["Вертикальная", "Горизонтальная"])
        },
        "Нагрев": {
            "Мощность, кВт": "1.5" if volume < 50 else "2.0",
            "Время нагрева 45°C": f"{volume + 20} мин"
        },
        "Бак": {"Покрытие бака": random.choice(["Биостеклофарфор", "Нержавеющая сталь", "Эмаль"])},
        "Управление": {"Тип": random.choice(["Механическое", "Электронное"])}
    }

def get_floor_heating_specs():
    area = random.choice([1.0, 1.5, 2.0, 3.0, 5.0])
    return {
        "Основные": {
            "Тип системы": random.choice(["Нагревательный мат", "Кабель в стяжку"]),
            "Площадь обогрева, м2": str(area),
            "Мощность, Вт": str(int(area * 150))
        },
        "Монтаж": {"Покрытие": "Под плитку / керамогранит"}
    }

def get_bidet_specs():
    install = random.choice(["Подвесное", "Напольное"])
    return {
        "Основные": {"Тип": "Биде", "Монтаж": install},
        "Размеры": {"Длина, см": "54", "Ширина, см": "36", "Высота, см": "40"},
        "Внешний вид": {"Цвет": "Белый", "Поверхность": "Глянцевая"},
        "Отверстие под смеситель": {"Количество": "1", "Расположение": "По центру"}
    }

def get_urinal_specs():
    return {
        "Основные": {"Тип": "Писсуар", "Монтаж": "Подвесной"},
        "Управление": {"Смыв": random.choice(["Сенсорный (ИК)", "Механическая кнопка", "Наружный кран"])},
        "Подвод воды": {"Тип": random.choice(["Скрытый", "Наружный"])},
        "Материал": {"Материал": "Санфарфор"}
    }

def get_drain_specs(subtype):
    return {
        "Назначение": {"Для": subtype},
        "Материал": {"Материал": random.choice(["Пластик", "Латунь/Хром"])},
        "Конструкция": {"Тип": "Бутылочный" if "раковин" in subtype else "Обвязка"},
        "Размеры": {"Диаметр слива": "1 1/4\"" if "раковин" in subtype else "1 1/2\""}
    }

def get_filter_specs():
    return {
        "Основные": {
            "Тип": random.choice(["Магистральный фильтр", "Фильтр под мойку", "Сменный картридж"]),
            "Назначение": "Очистка воды"
        },
        "Очистка": {"Ступени очистки": random.choice(["1", "3", "5"])},
        "Характеристики": {"Производительность": "3 л/мин", "Ресурс": "10000 л"}
    }

# --- 6. Генерация Товаров ---

# Словарь: Категория -> Функция генерации + Данные для названия
generators = {
    "Унитазы": (get_toilet_specs, ["Подвесной унитаз", "Напольный унитаз", "Унитаз-компакт", "Безободковый унитаз"]),
    "Раковины": (get_sink_specs, ["Раковина подвесная", "Раковина накладная", "Раковина врезная", "Раковина мебельная"]),
    "Смесители": (get_mixer_specs, ["Смеситель для раковины", "Смеситель для ванны", "Смеситель для кухни", "Смеситель для душа"]),
    "Душевые программы": (get_shower_program_specs, ["Душевая стойка", "Душевая панель", "Душевой гарнитур"]),
    "Душевые кабины и ограждения": (get_shower_cabin_specs, ["Душевая кабина"]), # Без подтипов
    "Ванны": (None, ["Ванна"]), # Спец логика
    "Инсталляции": (get_installation_specs, ["Инсталляция для унитаза"]),
    "Комплекты с унитазом": (None, ["Комплект 4в1"]), # Спец логика (Инсталляция + Унитаз)
    "Кухонные мойки": (get_kitchen_sink_specs, ["Кухонная мойка"]),
    "Фильтры и аксессуары": (get_filter_specs, ["Фильтр"]),
    "Полотенцесушители": (get_towel_warmer_specs, ["Полотенцесушитель"]),
    "Слив и канализация": (None, ["Сифон"]), # Спец логика
    "Водонагреватели": (get_water_heater_specs, ["Водонагреватель"]),
    "Теплые полы": (get_floor_heating_specs, ["Теплый пол"]),
    "Биде": (get_bidet_specs, ["Биде"]),
    "Писсуары": (get_urinal_specs, ["Писсуар"])
}

print("Генерация товаров по категориям...")

total_products = 0

for cat_name, cat_obj in categories.items():
    # Определяем сколько товаров создавать (популярные категории больше)
    count = 15 if cat_name in ["Унитазы", "Смесители", "Раковины", "Ванны"] else 7
    
    # Получаем генератор и список типов
    if cat_name in generators:
        gen_func, types = generators[cat_name]
    else:
        continue # Should not happen based on categories_config

    for i in range(count):
        brand_obj = random.choice(list(brands.values()))
        
        # --- СПЕЦИАЛЬНАЯ ЛОГИКА ДЛЯ НЕКОТОРЫХ КАТЕГОРИЙ ---
        
        # 1. Ванны (нужен материал в аргументах)
        if cat_name == "Ванны":
            material = random.choice(["Акриловая", "Чугунная", "Стальная"])
            specs = get_bath_specs(material)
            size = f"{specs['Габариты']['Длина, см']}x{specs['Габариты']['Ширина, см']}"
            name = f"{material} ванна {brand_obj.name} {size}"
            
        # 2. Комплекты (нужно собрать specs из унитаза + инсталляции)
        elif cat_name == "Комплекты с унитазом":
            specs_toilet = get_toilet_specs("Подвесной")
            specs_install = get_installation_specs()
            # Объединяем словари
            specs = {**specs_toilet, "Инсталляция": specs_install["Габариты"]}
            name = f"Комплект 4в1 {brand_obj.name} (Унитаз + Инсталляция + Кнопка)"
            
        # 3. Слив и канализация
        elif cat_name == "Слив и канализация":
            type_for = random.choice(["для раковины", "для ванны"])
            specs = get_drain_specs(type_for)
            name = f"Сифон {brand_obj.name} {type_for} {specs['Материал']['Материал']}"
            
        # 4. Стандартная логика для остальных
        else:
            subtype = random.choice(types)
            specs = gen_func(subtype) if gen_func.__code__.co_argcount > 0 else gen_func()
            
            # Формируем красивое название из характеристик
            extra_info = ""
            
            if "Размеры" in specs and "Ширина, см" in specs["Размеры"]:
                extra_info = f"{specs['Размеры']['Ширина, см']} см"
            elif "Габариты" in specs and "Размер, см" in specs["Габариты"]:
                extra_info = specs["Габариты"]["Размер, см"]
            elif "Основные" in specs and "Объем, л" in specs["Основные"]:
                extra_info = f"{specs['Основные']['Объем, л']} л"
            elif "Внешний вид" in specs and "Цвет" in specs["Внешний вид"]:
                extra_info = specs["Внешний вид"]["Цвет"]
            
            series = random.choice(["Base", "Pro", "Style", "Soft", "Grand", "Unit", "Eco"])
            name = f"{subtype} {brand_obj.name} {series} {extra_info}"

        # Создание объекта
        p = Product(
            name=name.strip(),
            description=f"Высококачественный товар из категории {cat_name}. Надежность и долговечность от бренда {brand_obj.name}.",
            price=random.randint(1500, 80000),
            old_price=random.randint(85000, 100000) if random.random() > 0.8 else None,
            sku=f"SKU-{cat_name[:3].upper()}-{random.randint(10000, 99999)}",
            in_stock=random.randint(5, 50),
            category=cat_obj,
            brand=brand_obj,
            country=random.choice(["Германия", "Чехия", "Испания", "Россия", "Китай"]),
            warranty=random.choice(["1 год", "2 года", "5 лет", "10 лет"]),
            specifications=specs
        )
        db.session.add(p)
        
        # Добавляем изображение
        img = ProductImage(product=p, image_url="default_product.png", sort_order=0)
        db.session.add(img)
        
        total_products += 1

try:
    db.session.commit()
    print("------------------------------------------------")
    print(f"БД успешно обновлена!")
    print(f"Категорий: {Category.query.count()} (Все 16 из ТЗ)")
    print(f"Брендов: {Brand.query.count()}")
    print(f"Товаров: {Product.query.count()}")
    print("------------------------------------------------")
except Exception as e:
    db.session.rollback()
    print(f"Ошибка при сохранении: {e}")