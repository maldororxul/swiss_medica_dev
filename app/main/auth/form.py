""" Форма регистрации """
import re
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, ValidationError
from wtforms.validators import InputRequired, Length


def email_validator(form, field):
    # шаблон для проверки формата email
    if not re.match(r"[^@]+@[^@]+\.[^@]+", field.data):
        raise ValidationError("Invalid email address.")


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=80)])
    email = StringField('Email', validators=[InputRequired(), email_validator, Length(max=120)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8)])
