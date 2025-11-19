from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    BooleanField,
    SubmitField,
    TextAreaField,
    IntegerField,
    RadioField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    Optional,
    NumberRange,
    ValidationError,
)
from .models import User


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    remember = BooleanField("Запомнить меня")
    submit = SubmitField("Войти")


class RegisterForm(FlaskForm):
    name = StringField("Имя", validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Пароль", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Подтвердите пароль", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Зарегистрироваться")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError("Этот email уже зарегистрирован.")


class ProfileForm(FlaskForm):
    name = StringField("Имя", validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    phone = StringField("Телефон", validators=[Optional(), Length(max=20)])
    address = TextAreaField("Адрес", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Сохранить")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Текущий пароль", validators=[DataRequired()])
    new_password = PasswordField(
        "Новый пароль", validators=[DataRequired(), Length(min=6)]
    )
    confirm_password = PasswordField(
        "Подтвердите новый пароль", validators=[DataRequired(), EqualTo("new_password")]
    )
    submit = SubmitField("Изменить пароль")


class ReviewForm(FlaskForm):
    rating = RadioField(
        "Оценка",
        choices=[(5, "5"), (4, "4"), (3, "3"), (2, "2"), (1, "1")],
        validators=[DataRequired("Пожалуйста, поставьте оценку.")],
        coerce=int,
    )
    comment = TextAreaField("Ваш отзыв", validators=[Length(max=1000)])
    submit = SubmitField("Отправить отзыв")
