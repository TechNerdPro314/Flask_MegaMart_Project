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


def create_admin_user(email=None, name=None, password=None):
    """Создает нового пользователя с правами администратора с заданными параметрами"""
    app = create_app()
    
    with app.app_context():
        print("=== Создание администратора для MegaMart ===\n")
        
        # Если параметры не заданы, используем значения по умолчанию
        if email is None:
            email = input("Введите email для администратора (по умолчанию admin@admin.com): ").strip()
            if not email:
                email = "admin@admin.com"
        
        if name is None:
            name_input = input("Введите имя администратора (по умолчанию Admin User): ").strip()
            if not name_input:
                name = "Admin User"
            else:
                name = name_input
        
        if password is None:
            import getpass
            password_input = getpass.getpass("Введите пароль для администратора (по умолчанию admin123): ")
            if not password_input:
                password = "admin123"
            else:
                password = password_input
        
        # Проверяем, существует ли уже пользователь с таким email
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            print(f"Предупреждение: Пользователь с email '{email}' уже существует")
            print(f"ID существующего пользователя: {existing_user.id}")
            print(f"Имя: {existing_user.name}")
            print(f"Статус администратора: {'Да' if existing_user.is_admin else 'Нет'}")
            
            update_choice = input(f"\nХотите сделать этого пользователя администратором? (y/n): ").lower()
            if update_choice == 'y':
                existing_user.is_admin = True
                try:
                    db.session.commit()
                    print(f"✓ Пользователь {email} теперь администратор!")
                    return True
                except Exception as e:
                    db.session.rollback()
                    print(f"Ошибка при обновлении прав администратора: {str(e)}")
                    return False
            else:
                print("Создание нового администратора отменено.")
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
            print(f"ID: {admin_user.id}")
            print(f"Права администратора: {'Да' if admin_user.is_admin else 'Нет'}")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Ошибка при создании администратора: {str(e)}")
            return False


def list_all_users():
    """Выводит список всех пользователей"""
    app = create_app()
    
    with app.app_context():
        users = User.query.all()
        if not users:
            print("Нет зарегистрированных пользователей.")
            return
        
        print("\n=== Список всех пользователей ===")
        for user in users:
            print(f"ID: {user.id}, Email: {user.email}, Имя: {user.name}, "
                  f"Админ: {'Да' if user.is_admin else 'Нет'}")


def reset_admin_password(email):
    """Сброс пароля для пользователя с правами администратора"""
    app = create_app()
    
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"Пользователь с email '{email}' не найден")
            return False
        
        import getpass
        new_password = getpass.getpass(f"Введите новый пароль для {email}: ")
        if not new_password:
            print("Пароль не может быть пустым")
            return False
        
        user.set_password(new_password)
        
        try:
            db.session.commit()
            print(f"✓ Пароль для {email} успешно изменен!")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Ошибка при изменении пароля: {str(e)}")
            return False


if __name__ == "__main__":
    print("Выберите действие:")
    print("1. Создать нового администратора")
    print("2. Просмотреть всех пользователей")
    print("3. Сбросить пароль администратора")
    
    choice = input("\nВведите номер действия (1-3): ").strip()
    
    if choice == "1":
        create_admin_user()
    elif choice == "2":
        list_all_users()
    elif choice == "3":
        email = input("Введите email пользователя: ").strip()
        if email:
            reset_admin_password(email)
        else:
            print("Email не может быть пустым")
    else:
        print("Неверный выбор. Пожалуйста, выберите 1, 2 или 3.")