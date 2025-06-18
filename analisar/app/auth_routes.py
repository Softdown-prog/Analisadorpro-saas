# app/auth_routes.py
from flask import render_template, url_for, flash, redirect, Blueprint, request, session
from flask_login import login_user, current_user, logout_user
from app import db, bcrypt
from app.forms import RegistrationForm, LoginForm, SetPasswordForm
from app.models import User, Plan
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bp = Blueprint('auth', __name__)

@bp.route("/registo", methods=['GET', 'POST'])
def registo():
    if current_user.is_authenticated:
        return redirect(url_for('pro.dashboard_pro'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            free_plan = Plan.query.get(1)
            if not free_plan:
                logging.error("Erro no registro: Plano gratuito (ID 1) não encontrado no banco de dados. Execute 'flask db-commands init-plans'.")
                flash('Erro interno: Plano gratuito não configurado. Contacte o suporte.', 'danger')
                return redirect(url_for('auth.registo'))

            user = User(username=form.username.data, email=form.email.data,
                        password=hashed_password, plan_id=free_plan.id)

            db.session.add(user)
            db.session.commit()
            logging.info(f"Novo usuário registrado: {user.email} com plano {free_plan.nome} (ID: {free_plan.id})")
            flash('Sua conta foi criada com sucesso! Por favor, faça login.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            logging.error(f"Erro ao registrar usuário {form.email.data}: {e}", exc_info=True)
            flash(f'Erro ao criar conta: {e}. Por favor, tente novamente.', 'danger')
            db.session.rollback()
    return render_template('registo.html', title='Registar', form=form)

@bp.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('pro.dashboard_pro'))
    
    form = LoginForm()
    if form.validate_on_submit():
        logging.info(f"Tentativa de login para o email: {form.email.data}")
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            logging.info(f"Usuário {user.email} encontrado (ID: {user.id}). Verificando senha...")
            logging.info(f"Senha hash no DB para {user.email}: {user.password}")
            logging.info(f"Senha fornecida para {user.email}: {form.password.data}")

            if user.password and bcrypt.check_password_hash(user.password, form.password.data):
                logging.info(f"Senha correta para {user.email}. Tentando login_user...")
                login_user(user, remember=form.remember.data)
                
                if current_user.is_authenticated:
                    logging.info(f"Login bem-sucedido para: {user.email} (current_user.is_authenticated: True)")
                    try:
                        plan_name = current_user.current_plan.nome if current_user.current_plan else 'N/A'
                        logging.info(f"Plano do usuário logado: {plan_name}")
                    except Exception as e:
                        logging.error(f"Erro ao acessar current_plan para usuário logado {user.email}: {e}", exc_info=True)
                        flash('Erro interno ao carregar dados do plano. Contacte o suporte.', 'danger')
                        logout_user()
                        return redirect(url_for('auth.login'))
                else:
                    logging.error(f"Login_user falhou para {user.email}: current_user não autenticado após chamada.")
                    flash('Erro interno ao processar login. Contacte o suporte.', 'danger')
                    return redirect(url_for('auth.login'))
                
                flash('Login realizado com sucesso!', 'success')
                return redirect(url_for('pro.dashboard_pro'))
            else:
                logging.warning(f"Tentativa de login falhou para {user.email}: Senha incorreta ou hash nulo no DB.")
                flash('Login sem sucesso. Verifique o email e a palavra-passe.', 'danger')
        else:
            logging.warning(f"Tentativa de login falhou: Usuário com email {form.email.data} não encontrado.")
            flash('Login sem sucesso. Verifique o email e a palavra-passe.', 'danger')
    return render_template('login.html', title='Login', form=form)

@bp.route("/sair")
def sair():
    logout_user()
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('public.home'))

@bp.route("/set_password_after_payment", methods=['GET', 'POST'])
def set_password_after_payment():
    external_ref = request.args.get('external_ref')
    email_from_param = request.args.get('email') # Obter email do query param
    
    if not external_ref or not email_from_param:
        flash('Link inválido para definir senha.', 'danger')
        return redirect(url_for('public.home'))

    user = User.query.filter_by(email=email_from_param).first() # Usar o email do param
    if not user:
        flash('Conta não encontrada ou pagamento pendente de confirmação. Tente novamente mais tarde.', 'danger')
        logging.warning(f"Tentativa de set_password para email {email_from_param} com ref {external_ref} mas usuário não encontrado.")
        return redirect(url_for('public.home'))
    
    # Se o usuário já tem senha definida E NÃO é a senha temporária, redireciona
    if user.password and bcrypt.check_password_hash(user.password, "TEMP_PASSWORD_NEEDS_RESET") is False:
        flash('Sua conta já possui uma senha. Por favor, faça login.', 'info')
        return redirect(url_for('auth.login'))

    form = SetPasswordForm()
    if form.validate_on_submit():
        try:
            # Revalidar que o usuário ainda existe e é o mesmo email da ref
            user = User.query.filter_by(email=email_from_param).first()
            if not user:
                flash('Erro: Conta não encontrada ou problema de sincronização. Contacte o suporte.', 'danger')
                return redirect(url_for('public.home'))

            user.username = form.username.data
            user.password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            db.session.commit()
            flash('Sua senha foi definida com sucesso! Por favor, faça login.', 'success')
            logging.info(f"Usuário {user.email} (pós-pagamento) definiu a senha.")
            return redirect(url_for('auth.login'))
        except Exception as e:
            logging.error(f"Erro ao definir senha para usuário {email_from_param}: {e}", exc_info=True)
            flash(f'Erro ao definir senha: {e}. Por favor, tente novamente.', 'danger')
            db.session.rollback()
    
    # Preencher o campo email no formulário hidden ou exibir para o user
    form.username.data = email_from_param.split('@')[0] # Sugere username
    return render_template('set_password_after_payment.html', title='Definir Senha da Conta PRO', form=form, email=email_from_param)