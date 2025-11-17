from flask_admin import AdminIndexView, expose
from flask_login import login_required, current_user
from app.models import Order, Product, User, OrderItem, db
from flask import flash, redirect, url_for
from datetime import datetime, timedelta
from sqlalchemy import func

class CustomAdminIndexView(AdminIndexView):
    @expose('/')
    @login_required
    def index(self):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Доступ запрещен. Требуются права администратора.', 'danger')
            return redirect(url_for('login', next=url_for('admin.index')))
        
        # Статистика
        total_orders = Order.query.count()
        total_products = Product.query.count()
        total_users = User.query.count()
        
        # Заказы за последние 30 дней
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_orders = Order.query.filter(Order.created_at >= thirty_days_ago).count()
        
        # Выручка за последние 30 дней
        revenue = db.session.query(func.sum(Order.total_amount)).filter(
            Order.created_at >= thirty_days_ago,
            Order.status == 'Paid'
        ).scalar() or 0
        
        # Последние 5 заказов
        latest_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
        
        # Популярные товары
        popular_products = db.session.query(
            Product.name, 
            func.sum(OrderItem.quantity).label('total_sold')
        ).join(OrderItem).group_by(Product.id).order_by(func.sum(OrderItem.quantity).desc()).limit(5).all()
        
        # Данные для графика (заказы по дням за последнюю неделю)
        days = []
        order_counts = []
        for i in range(7):
            day = datetime.utcnow() - timedelta(days=6-i)
            next_day = day + timedelta(days=1)
            count = Order.query.filter(
                Order.created_at >= day,
                Order.created_at < next_day
            ).count()
            days.append(day.strftime('%d.%m'))
            order_counts.append(count)
        
        return self.render('admin/index.html',
                         total_orders=total_orders,
                         total_products=total_products,
                         total_users=total_users,
                         recent_orders=recent_orders,
                         revenue=round(float(revenue), 2),
                         latest_orders=latest_orders,
                         popular_products=popular_products,
                         days=days,
                         order_counts=order_counts)