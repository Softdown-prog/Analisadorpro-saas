# app/forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, URL
from app.models import User

class RegistrationForm(FlaskForm):
    username = StringField('Utilizador',
                           validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Palavra-passe', validators=[DataRequired()])
    confirm_password = PasswordField('Confirmar Palavra-passe',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Registar')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Esse nome de utilizador já existe. Por favor, escolha outro.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Esse email já está registado. Por favor, escolha outro.')


class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Palavra-passe', validators=[DataRequired()])
    remember = BooleanField('Lembrar-me')
    submit = SubmitField('Login')


class AnalysisForm(FlaskForm):
    url = StringField('URL do Site para Analisar',
                      validators=[DataRequired(), URL(message="Por favor, insira uma URL válida. Ex: https://www.google.com")])
    submit = SubmitField('Analisar Agora')

class SitemapForm(FlaskForm):
    url = StringField('URL do Site',
                      validators=[DataRequired(), URL(message="Por favor, insira uma URL válida. Ex: https://www.exemplo.com")])
    submit = SubmitField('Gerar Sitemap.xml')

class AdminLoginForm(FlaskForm):
    username = StringField('Utilizador Admin', validators=[DataRequired()])
    password = PasswordField('Palavra-passe Admin', validators=[DataRequired()])
    submit = SubmitField('Login Admin')

# NOVO FORMULÁRIO: Para usuários que pagaram e precisam definir sua senha
class SetPasswordForm(FlaskForm):
    username = StringField('Nome de Utilizador',
                           validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Nova Palavra-passe', validators=[DataRequired()])
    confirm_password = PasswordField('Confirmar Palavra-passe',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Definir Palavra-passe')

    def validate_username(self, username):
        # Garante que o username não está em uso por outro usuário se não for o caso de um usuário já existente
        pass # A validação real dependerá do contexto (se é um usuário novo ou existente)