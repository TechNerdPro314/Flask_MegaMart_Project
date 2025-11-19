from flask_admin import AdminIndexView, expose, BaseView
from flask_login import login_required, current_user
from app.models import Order, Product, User, OrderItem, db, Category, Brand
from flask import flash, redirect, url_for, Response, request
from datetime import datetime, timedelta
from sqlalchemy import func
import csv
import io


class CustomAdminIndexView(AdminIndexView):
    @expose("/")
    @login_required
    def index(self):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Доступ запрещен. Требуются права администратора.", "danger")
            return redirect(url_for("login", next=url_for("admin.index")))
        total_orders = Order.query.count()
        total_products = Product.query.count()
        total_users = User.query.count()
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_orders = Order.query.filter(Order.created_at >= thirty_days_ago).count()
        revenue = (
            db.session.query(func.sum(Order.final_amount))
            .filter(Order.created_at >= thirty_days_ago, Order.status == "Paid")
            .scalar()
            or 0
        )
        latest_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
        popular_products = (
            db.session.query(
                Product.name, func.sum(OrderItem.quantity).label("total_sold")
            )
            .join(OrderItem)
            .group_by(Product.id)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(5)
            .all()
        )
        days = []
        order_counts = []
        for i in range(7):
            day = datetime.utcnow() - timedelta(days=6 - i)
            next_day = day + timedelta(days=1)
            count = Order.query.filter(
                Order.created_at >= day, Order.created_at < next_day
            ).count()
            days.append(day.strftime("%d.%m"))
            order_counts.append(count)
        return self.render(
            "admin/index.html",
            total_orders=total_orders,
            total_products=total_products,
            total_users=total_users,
            recent_orders=recent_orders,
            revenue=round(float(revenue), 2),
            latest_orders=latest_orders,
            popular_products=popular_products,
            days=days,
            order_counts=order_counts,
        )


class ImportExportView(BaseView):
    @expose("/")
    def index(self):
        return self.render("admin/import_export.html")

    @expose("/export")
    def export(self):
        output = io.StringIO()
        writer = csv.writer(output)
        headers = [
            "id",
            "name",
            "slug",
            "description",
            "price",
            "old_price",
            "sku",
            "in_stock",
            "category_name",
            "brand_name",
            "meta_title",
            "meta_description",
        ]
        writer.writerow(headers)
        products = Product.query.all()
        for product in products:
            row = [
                product.id,
                product.name,
                product.slug,
                product.description,
                product.price,
                product.old_price,
                product.sku,
                product.in_stock,
                product.category.name if product.category else "",
                product.brand.name if product.brand else "",
                product.meta_title,
                product.meta_description,
            ]
            writer.writerow(row)
        output.seek(0)
        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=products_export.csv"},
        )

    @expose("/import", methods=["POST"])
    def import_csv(self):
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("Файл не был выбран.", "danger")
            return redirect(url_for(".index"))
        if not file.filename.endswith(".csv"):
            flash("Пожалуйста, загрузите файл в формате CSV.", "danger")
            return redirect(url_for(".index"))
        try:
            stream = io.StringIO(file.stream.read().decode("UTF-8"), newline=None)
            csv_reader = csv.reader(stream)
            headers = next(csv_reader)
            created_count, updated_count = 0, 0
            for row in csv_reader:
                row_data = dict(zip(headers, row))
                product_id = row_data.get("id")
                product = Product.query.get(product_id) if product_id else None
                if not product:
                    product = Product()
                    created_count += 1
                else:
                    updated_count += 1
                product.name = row_data.get("name")
                product.slug = row_data.get("slug") or None
                product.description = row_data.get("description")
                product.price = row_data.get("price")
                product.old_price = row_data.get("old_price") or None
                product.sku = row_data.get("sku")
                product.in_stock = int(row_data.get("in_stock", 0))
                product.meta_title = row_data.get("meta_title")
                product.meta_description = row_data.get("meta_description")
                category_name = row_data.get("category_name")
                if category_name:
                    category = Category.query.filter_by(name=category_name).first()
                    if not category:
                        category = Category(name=category_name)
                        db.session.add(category)
                    product.category = category
                brand_name = row_data.get("brand_name")
                if brand_name:
                    brand = Brand.query.filter_by(name=brand_name).first()
                    if not brand:
                        brand = Brand(name=brand_name)
                        db.session.add(brand)
                    product.brand = brand
                db.session.add(product)
            db.session.commit()
            flash(
                f"Импорт завершен! Создано: {created_count}, обновлено: {updated_count} товаров.",
                "success",
            )
        except Exception as e:
            db.session.rollback()
            flash(f"Произошла ошибка при импорте: {e}", "danger")
        return redirect(url_for(".index"))
