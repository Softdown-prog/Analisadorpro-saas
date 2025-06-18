# app/soft_routes.py
from flask import render_template, url_for, flash, redirect, Blueprint, request, session, current_app
from app import db, bcrypt
from app.forms import AdminLoginForm # Importar o novo formulário de login admin
from app.models import User, Plan, AnalysisReport, IpUsage
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bp = Blueprint('soft', __name__)

# Chave da sessão para indicar que o admin está logado
ADMIN_SESSION_KEY = 'admin_logged_in_soft_panel'

# Decorador para proteger rotas administrativas
def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get(ADMIN_SESSION_KEY):
            flash('Acesso restrito. Por favor, faça login como administrador.', 'danger')
            return redirect(url_for('soft.admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route("/", methods=['GET', 'POST'])
@bp.route("/login", methods=['GET', 'POST']) # Rota de login do admin
def admin_login():
    if session.get(ADMIN_SESSION_KEY): # Se já logado como admin
        return redirect(url_for('soft.admin_dashboard'))

    form = AdminLoginForm()
    if form.validate_on_submit():
        username_attempt = form.username.data
        password_attempt = form.password.data

        # Verifica as credenciais hardcoded (ou de variáveis de ambiente do .env)
        if username_attempt == current_app.config['ADMIN_USERNAME'] and \
           bcrypt.check_password_hash(current_app.config['ADMIN_PASSWORD_HASH'], password_attempt):
            session[ADMIN_SESSION_KEY] = True
            flash('Login de administrador bem-sucedido!', 'success')
            logging.info(f"Admin login bem-sucedido para: {username_attempt}")
            return redirect(url_for('soft.admin_dashboard'))
        else:
            flash('Credenciais de administrador inválidas.', 'danger')
            logging.warning(f"Tentativa de login admin falhou para: {username_attempt}")
    return render_template('soft_login.html', title='Login Admin', form=form)

@bp.route("/logout")
def admin_logout():
    session.pop(ADMIN_SESSION_KEY, None)
    flash('Você saiu do painel administrativo.', 'info')
    return redirect(url_for('soft.admin_login'))

@bp.route("/dashboard")
@admin_required # Protege esta rota
def admin_dashboard():
    total_users = User.query.count()
    total_reports = AnalysisReport.query.count()
    total_ips_used = IpUsage.query.count()
    
    # Exemplo: Contagem de usuários por plano
    users_by_plan = db.session.query(Plan.nome, db.func.count(User.id)).join(User).group_by(Plan.nome).all()

    return render_template('soft_dashboard.html', title='Painel Admin',
                           total_users=total_users,
                           total_reports=total_reports,
                           total_ips_used=total_ips_used,
                           users_by_plan=users_by_plan)

@bp.route("/users")
@admin_required # Protege esta rota
def manage_users():
    users = User.query.all()
    plans = Plan.query.all() # Para exibir os nomes dos planos e mudar
    return render_template('soft_users.html', title='Gerenciar Usuários', users=users, plans=plans)

@bp.route("/users/<int:user_id>/edit", methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    # TODO: Implementar formulário e lógica para editar user, mudar plano, resetar senha
    # Para o reset de senha, você geraria um novo hash bcrypt da nova senha.
    flash(f"Implementar edição para o usuário: {user.email}", 'info')
    return redirect(url_for('soft.manage_users'))

@bp.route("/users/<int:user_id>/delete", methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    try:
        AnalysisReport.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
        db.session.commit()
        flash(f'Usuário {user.email} e seus relatórios foram deletados.', 'success')
        logging.info(f"Usuário deletado via admin: {user.email}")
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao deletar usuário {user.email}: {e}', 'danger')
        logging.error(f"Erro ao deletar usuário {user.email}: {e}", exc_info=True)
    return redirect(url_for('soft.manage_users'))

@bp.route("/users/<int:user_id>/set_plan", methods=['POST']) # NOVO: Rota para mudar plano
@admin_required
def set_user_plan(user_id):
    user = User.query.get_or_404(user_id)
    new_plan_id = request.form.get('plan_id', type=int)
    
    if not new_plan_id:
        flash('Nenhum plano selecionado.', 'danger')
        return redirect(url_for('soft.manage_users'))

    new_plan = Plan.query.get(new_plan_id)
    if not new_plan:
        flash('Plano selecionado inválido.', 'danger')
        return redirect(url_for('soft.manage_users'))
    
    user.plan_id = new_plan.id
    db.session.commit()
    flash(f'Plano do usuário {user.email} alterado para {new_plan.nome}.', 'success')
    logging.info(f"Admin mudou plano do usuário {user.email} para {new_plan.nome}.")
    return redirect(url_for('soft.manage_users'))


@bp.route("/plans")
@admin_required
def manage_plans():
    plans = Plan.query.all()
    flash("Implementar gerenciamento de planos (CRUD).", 'info')
    return render_template('soft_plans.html', title='Gerenciar Planos', plans=plans) # Criar soft_plans.html