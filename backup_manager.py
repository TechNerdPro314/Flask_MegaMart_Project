#!/usr/bin/env python3
"""
Скрипт резервного копирования базы данных MySQL.
Поддерживает хранение локально и загрузку в S3 (опционально).
"""
import os
import sys
import datetime
import gzip
import boto3
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Конфигурация
BACKUP_DIR = os.environ.get("BACKUP_DIR", "/app/backups")
KEEP_DAILY = int(os.environ.get("KEEP_DAILY", 7))
KEEP_WEEKLY = int(os.environ.get("KEEP_WEEKLY", 4))
KEEP_MONTHLY = int(os.environ.get("KEEP_MONTHLY", 12))

# Настройки MySQL
MYSQL_HOST = os.environ.get("MYSQL_HOST", "db")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
MYSQL_USER = os.environ.get("MYSQL_USER")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD")
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE")

# S3 настройки (опционально)
S3_BUCKET = os.environ.get("S3_BACKUP_BUCKET")
S3_PREFIX = os.environ.get("S3_BACKUP_PREFIX", "mysql-backups")


def get_mysqldump_command():
    """Формирует команду mysqldump с настройками безопасности."""
    return [
        "mysqldump",
        f"--host={MYSQL_HOST}",
        f"--port={MYSQL_PORT}",
        f"--user={MYSQL_USER}",
        f"--password={MYSQL_PASSWORD}",
        "--single-transaction",
        "--routines",
        "--triggers",
        "--events",
        "--flush-logs",
        "--master-data=2",
        MYSQL_DATABASE,
    ]


def create_backup():
    """Создает сжатый дамп базы данных."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"{MYSQL_DATABASE}_{timestamp}.sql.gz"
    backup_path = Path(BACKUP_DIR) / backup_filename
    
    print(f"[{datetime.datetime.now()}] Создание резервной копии: {backup_filename}")
    
    try:
        # Создаем директорию если не существует
        Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
        
        # Выполняем mysqldump и сжимаем на лету
        cmd = get_mysqldump_command()
        with open(backup_path, "wb") as output:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            gzip_process = subprocess.Popen(
                ["gzip"], stdin=process.stdout, stdout=output
            )
            process.stdout.close()
            gzip_process.wait()
            process.wait()
        
        if process.returncode == 0:
            file_size = backup_path.stat().st_size
            print(f"[OK] Резервная копия создана: {file_size / 1024 / 1024:.2f} MB")
            
            # Загружаем в S3 если настроено
            if S3_BUCKET:
                upload_to_s3(backup_path, backup_filename)
            
            return backup_path
        else:
            stderr = process.stderr.read().decode()
            print(f"[ERROR] Ошибка mysqldump: {stderr}")
            return None
            
    except Exception as e:
        print(f"[ERROR] Критическая ошибка: {e}")
        return None


def upload_to_s3(backup_path, filename):
    """Загружает резервную копию в S3."""
    try:   
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        )
        
        s3_key = f"{S3_PREFIX}/{filename}"
        s3_client.upload_file(str(backup_path), S3_BUCKET, s3_key)
        print(f"[S3] Загружено в s3://{S3_BUCKET}/{s3_key}")
        
        # Удаляем локальный файл после загрузки
        backup_path.unlink()
        print(f"[CLEANUP] Локальный файл удален")
        
    except ImportError:
        print("[WARN] boto3 не установлен, пропуск загрузки в S3")
    except Exception as e:
        print(f"[ERROR] Ошибка загрузки в S3: {e}")


def cleanup_old_backups():
    """Удаляет устаревшие резервные копии."""
    backup_dir = Path(BACKUP_DIR)
    if not backup_dir.exists():
        return
    
    now = datetime.datetime.now()
    
    for backup_file in backup_dir.glob(f"{MYSQL_DATABASE}_*.sql.gz"):
        # Пропускаем S3 загруженные файлы
        if backup_file.name.endswith("_uploaded.gz"):
            continue
            
        try:
            # Извлекаем дату из имени файла
            date_str = backup_file.name.replace(f"{MYSQL_DATABASE}_", "").replace(".sql.gz", "")
            file_date = datetime.datetime.strptime(date_str, "%Y%m%d_%H%M%S")
            
            age_days = (now - file_date).days
            
            # Определяем категорию файла для разной политики хранения
            is_weekly = file_date.weekday() == 0  # Понедельник
            is_monthly = file_date.day == 1  # Первое число
            
            should_delete = False
            
            if is_monthly and age_days > KEEP_MONTHLY * 30:
                should_delete = True
            elif is_weekly and age_days > KEEP_WEEKLY * 7:
                should_delete = True
            elif age_days > KEEP_DAILY:
                should_delete = True
            
            if should_delete:
                backup_file.unlink()
                print(f"[CLEANUP] Удален устаревший файл: {backup_file.name}")
                
        except ValueError:
            print(f"[WARN] Не удалось разобрать дату файла: {backup_file.name}")


def verify_backup(backup_path):
    """Проверяет целостность резервной копии."""
    try:
        # Проверяем что файл можно распаковать
        result = subprocess.run(
            ["gzip", "-t", str(backup_path)],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"[VERIFY] Резервная копия прошла проверку целостности")
            return True
        else:
            print(f"[VERIFY] Ошибка проверки: {result.stderr}")
            return False
    except Exception as e:
        print(f"[VERIFY] Ошибка проверки: {e}")
        return False


def list_backups():
    """Выводит список существующих резервных копий."""
    backup_dir = Path(BACKUP_DIR)
    if not backup_dir.exists():
        print("Нет резервных копий")
        return
    
    print("\nСуществующие резервные копии:")
    print("-" * 60)
    
    total_size = 0
    for backup_file in sorted(backup_dir.glob(f"{MYSQL_DATABASE}_*.sql.gz"), reverse=True):
        if "_uploaded" in backup_file.name:
            continue
        size_mb = backup_file.stat().st_size / 1024 / 1024
        total_size += size_mb
        print(f"{backup_file.name:45} {size_mb:>8.2f} MB")
    
    print("-" * 60)
    print(f"Всего: {total_size:.2f} MB\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MySQL Backup Manager")
    parser.add_argument(
        "--create", action="store_true", help="Создать новую резервную копию"
    )
    parser.add_argument(
        "--cleanup", action="store_true", help="Удалить устаревшие копии"
    )
    parser.add_argument(
        "--verify", action="store_true", help="Проверить последнюю копию"
    )
    parser.add_argument(
        "--list", action="store_true", help="Показать список копий"
    )
    parser.add_argument(
        "--all", action="store_true", help="Выполнить все операции"
    )
    
    args = parser.parse_args()
    
    if not any([args.create, args.cleanup, args.verify, args.list, args.all]):
        parser.print_help()
        sys.exit(1)
    
    if args.create or args.all:
        backup_path = create_backup()
        if backup_path:
            verify_backup(backup_path)
    
    if args.cleanup or args.all:
        cleanup_old_backups()
    
    if args.list or args.all:
        list_backups()
    
    if args.verify and not args.create:
        backup_dir = Path(BACKUP_DIR)
        latest = max(backup_dir.glob(f"{MYSQL_DATABASE}_*.sql.gz"), default=None)
        if latest:
            verify_backup(latest)
        else:
            print("Нет резервных копий для проверки")
