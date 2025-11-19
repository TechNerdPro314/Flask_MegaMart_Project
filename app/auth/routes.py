from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User, Order
from app import db, limiter
from . import auth_bp
from app.forms import LoginForm, RegisterForm, ProfileForm, ChangePasswordForm
from app.cart.routes import (
    merge_session_cart_to_db,
)
from app.email import send_welcome_email


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = RegisterForm()
    if form.validate_on_submit():
        new_user = User(email=form.email.data, name=form.name.data)
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()

        # Отправляем приветственное письмо
        send_welcome_email(new_user)

        login_user(new_user)
        merge_session_cart_to_db()
        flash(
            "Вы успешно зарегистрированы! На вашу почту отправлено приветственное письмо.",
            "success",
        )
        return redirect(url_for("main.index"))
    return render_template("register.html", title="Регистрация", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None or not user.check_password(form.password.data):
            flash("Неверный email или пароль", "danger")
            return redirect(url_for("auth.login"))

        login_user(user, remember=form.remember.data)
        merge_session_cart_to_db()

        next_page = request.args.get("next")

        if user.is_admin:
            flash(f"Добро пожаловать в админ-панель, {user.name}!", "success")
            return redirect(next_page or url_for("admin.index"))

        flash(f"Добро пожаловать, {user.name}!", "success")
        return redirect(next_page or url_for("main.index"))

    return render_template("login.html", title="Вход", form=form)


@auth_bp.route("/logout")
def logout():
    logout_user()
    flash("Вы вышли из системы.", "info")
    return redirect(url_for("main.index"))


@auth_bp.route("/profile")
@login_required
def profile():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(db.desc(Order.created_at)).all()
    return render_template("profile.html", title="Личный кабинет", orders=orders)


@auth_bp.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = ProfileForm(obj=current_user)

    if form.validate_on_submit():
        existing_user = User.query.filter(
            User.email == form.email.data, User.id != current_user.id
        ).first()
        if existing_user:
            flash("Этот Email уже используется другим пользователем.", "danger")
            return redirect(url_for("auth.edit_profile"))

        current_user.name = form.name.data
        current_user.email = form.email.data
        current_user.phone = form.phone.data
        current_user.address = form.address.data

        try:
            db.session.commit()
            flash("Данные профиля успешно обновлены.", "success")
            return redirect(url_for("auth.profile"))
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при обновлении профиля: {e}", "danger")

    return render_template(
        "edit_profile.html", title="Редактировать профиль", form=form
    )


@auth_bp.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()

    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Неверный текущий пароль.", "danger")
            return redirect(url_for("auth.change_password"))

        current_user.set_password(form.new_password.data)
        try:
            db.session.commit()
            flash("Пароль успешно изменен.", "success")
            return redirect(url_for("auth.profile"))
        except Exception as e:
            db.session.rollback()
            flash(f"Ошибка при изменении пароля: {e}", "danger")

    return render_template("change_password.html", title="Изменить пароль", form=form)


@auth_bp.route("/reset_password", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()

        if user:
            token = user.get_reset_token()
            reset_url = url_for("auth.reset_token", token=token, _external=True)
            # В реальном приложении здесь будет отправка email
            current_app.logger.info("-" * 50)
            current_app.logger.info(
                f"СБРОС ПАРОЛЯ ДЛЯ {user.email}. ССЫЛКА: {reset_url}"
            )
            current_app.logger.info("-" * 50)

            flash(
                "На ваш email отправлена инструкция по сбросу пароля (в логах сервера).",
                "info",
            )
        else:
            flash("Пользователь с таким email не найден.", "danger")

        return redirect(url_for("auth.login"))

    return render_template("reset_request.html", title="Восстановление пароля")


@auth_bp.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    user = User.verify_reset_token(token)

    if user is None:
        flash(
            "Ссылка для сброса пароля недействительна или срок ее действия истек.",
            "danger",
        )
        return redirect(url_for("auth.reset_request"))

    if request.method == "POST":
        password = request.form.get("password")
        password_confirm = request.form.get("password_confirm")

        if password != password_confirm:
            flash("Пароли не совпадают.", "danger")
            return redirect(url_for("auth.reset_token", token=token))

        user.set_password(password)
        db.session.commit()
        flash("Ваш пароль успешно изменен. Можете войти.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_token.html", title="Установить новый пароль")
