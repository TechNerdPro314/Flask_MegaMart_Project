from app import cache
from app.models import Product, Category, Brand, db
from sqlalchemy import func

def get_cached_categories():
    """Возвращает все категории с кэшированием или без кэширования при ошибке."""
    try:
        # Попробуем получить закэшированные данные
        cached_result = cache.get('cached_categories')
        if cached_result is None:
            # Если данных в кэше нет, получаем их из БД и сохраняем в кэш
            categories = Category.query.all()
            try:
                cache.set('cached_categories', categories, timeout=300)
            except:
                pass  # Игнорируем ошибку сохранения в кэш
            return categories
        return cached_result
    except:
        # Если кэш недоступен, получаем данные напрямую
        return Category.query.all()

def get_cached_brands():
    """Возвращает все бренды с кэшированием или без кэширования при ошибке."""
    try:
        # Попробуем получить закэшированные данные
        cached_result = cache.get('cached_brands')
        if cached_result is None:
            # Если данных в кэше нет, получаем их из БД и сохраняем в кэш
            brands = Brand.query.all()
            try:
                cache.set('cached_brands', brands, timeout=300)
            except:
                pass  # Игнорируем ошибку сохранения в кэш
            return brands
        return cached_result
    except:
        # Если кэш недоступен, получаем данные напрямую
        return Brand.query.all()

def get_category_filters(category_id):
    """Собирает доступные фильтры для категории (без изменений)."""
    products = Product.query.filter_by(category_id=category_id).all()
    filters = {}
    for product in products:
        if not product.specifications: continue
        for group, attrs in product.specifications.items():
            if group not in filters: filters[group] = {}
            for k, v in attrs.items():
                if k not in filters[group]: filters[group][k] = set()
                filters[group][k].add(v)
    for g in filters:
        for k in filters[g]: filters[g][k] = sorted(list(filters[g][k]))
    return filters

def filter_products_by_specs(query, request_args):
    """
    ПРОДАКШЕН ФИЛЬТРАЦИЯ:
    Использует MySQL JSON_EXTRACT для фильтрации на стороне сервера БД.
    """
    for param, values in request_args.lists():
        if param.startswith("spec__"):
            parts = param.split("__")
            if len(parts) == 3:
                group, key = parts[1], parts[2]

                # Формируем JSON путь для MySQL: $.Group.Key
                json_path = f'$.\"{group}\".\"{key}\"'

                # Используем JSON_EXTRACT и фильтруем через оператор IN
                # Мы используем func.json_unquote, чтобы убрать лишние кавычки при сравнении
                query = query.filter(
                    func.json_unquote(func.json_extract(Product.specifications, json_path)).in_(values)
                )
    return query