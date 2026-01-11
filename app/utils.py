from app.models import Product
from sqlalchemy import func

def get_category_filters(category_id):
    """
    Сканирует все товары в категории и собирает доступные характеристики для фильтрации.
    Возвращает структуру:
    {
        "Исполнение": {
            "Монтаж": ["Подвесной", "Напольный"],
            "Материал": ["Латунь", "Нержавеющая сталь"]
        },
        ...
    }
    """
    products = Product.query.filter_by(category_id=category_id).all()
    
    filters = {}
    
    for product in products:
        if not product.specifications:
            continue
            
        for group_name, attributes in product.specifications.items():
            if group_name not in filters:
                filters[group_name] = {}
            
            for key, value in attributes.items():
                if key not in filters[group_name]:
                    filters[group_name][key] = set()
                
                # Добавляем значение в множество (чтобы были уникальные)
                filters[group_name][key].add(value)
    
    # Преобразуем множества в сортированные списки для шаблона
    for group in filters:
        for key in filters[group]:
            filters[group][key] = sorted(list(filters[group][key]))
            
    return filters

def filter_products_by_specs(query, request_args):
    """
    Применяет фильтрацию по JSON-характеристикам.
    Поскольку JSON в разных БД работает по-разному,
    для максимальной совместимости (SQLite/MySQL) сделаем фильтрацию на уровне Python
    после основного запроса (для небольших магазинов это ОК).
    """
    # Собираем параметры спецификаций из запроса
    # Ожидаем формат: spec__Группа__Ключ = Значение
    spec_filters = {}
    for param, value in request_args.items():
        if param.startswith("spec__"):
            # Разбираем строку "spec__Исполнение__Монтаж"
            parts = param.split("__")
            if len(parts) == 3:
                group = parts[1]
                key = parts[2]
                
                if group not in spec_filters:
                    spec_filters[group] = {}
                if key not in spec_filters[group]:
                    spec_filters[group][key] = []
                
                spec_filters[group][key].append(value)

    if not spec_filters:
        return query

    # Получаем все товары из предварительного запроса (цена, бренд уже отфильтрованы SQL)
    products = query.all()
    filtered_products = []

    for product in products:
        if not product.specifications:
            continue
            
        match = True
        for group, keys in spec_filters.items():
            # Если группы нет в товаре - не подходит
            if group not in product.specifications:
                match = False
                break
                
            for key, target_values in keys.items():
                # Если ключа нет или значение не совпадает ни с одним из выбранных
                prod_val = product.specifications[group].get(key)
                if prod_val not in target_values:
                    match = False
                    break
            if not match:
                break
        
        if match:
            filtered_products.append(product)

    # Возвращаем список ID, чтобы SQLAlchemy могла построить новый запрос
    # (Это нужно для сохранения пагинации)
    if not filtered_products:
        return query.filter(Product.id == -1) # Пустой результат
        
    ids = [p.id for p in filtered_products]
    return query.filter(Product.id.in_(ids))