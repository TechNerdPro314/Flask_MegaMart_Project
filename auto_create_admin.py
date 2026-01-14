#!/usr/bin/env python3
"""
Скрипт для автоматического создания пользователя с правами администратора в MegaMart
"""

import os
import sys

# Добавляем путь к проекту в системный путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User


def create_admin_user(email="admin@example.com", name="Admin User", password="admin123"):
    """Создает нового пользователя с правами администратора с заданными параметрами"""
    app = create_app()
    
    with app.app_context():
        print("=== Создание администратора для MegaMart ===\n")
        
        # Проверяем, существует ли уже пользователь с таким email
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            print(f"Предупреждение: Пользователь с email '{email}' уже существует")
            print(f"Используйте другой email или удалите существующего пользователя")
            return False
        
        # Создаем нового пользователя с правами администратора
        admin_user = User(
            email=email,
            name=name,
            is_admin=True
        )
        admin_user.set_password(password)
        
        try:
            # Сохраняем в базу данных
            db.session.add(admin_user)
            db.session.commit()
            
            print(f"✓ Администратор успешно создан!")
            print(f"Email: {admin_user.email}")
            print(f"Имя: {admin_user.name}")
            print(f"Пароль: {password}")
            print(f"ID: {admin_user.id}")
            print(f"Права администратора: {'Да' if admin_user.is_admin else 'Нет'}")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Ошибка при создании администратора: {str(e)}")
            return False


if __name__ == "__main__":
    # Автоматически создаем администратора с параметрами по умолчанию
    success = create_admin_user()
    
    if success:
        print("\n✓ Администратор успешно создан!")
        print("Теперь вы можете войти в админ-панель с этими учетными данными.")
    else:
        print("\n✗ Не удалось создать администратора.")
        sys.exit(1)