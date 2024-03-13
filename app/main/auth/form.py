""" Форма регистрации """
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import InputRequired, Email, Length


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=80)])
    email = StringField('Email', validators=[InputRequired(), Email(message='Invalid email'), Length(max=120)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8)])
