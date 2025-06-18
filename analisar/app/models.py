# app/models.py
from datetime import datetime, timedelta
from app import db, login_manager
from flask_login import UserMixin
import logging

@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    user = db.session.get(User, int(user_id))
    logging.info(f"load_user: Tentando carregar usuário com ID {user_id}. Usuário encontrado: {user is not None}")
    if user:
        try:
            # É crucial que user.current_plan não dê erro aqui se o plano não existir (ex: DB corrompida)
            plan_name = user.current_plan.nome if user.current_plan else 'N/A'
            logging.info(f"load_user: Usuário {user.email} (ID: {user.id}) carregado com sucesso. Plano: {plan_name}")
        except Exception as e:
            logging.error(f"load_user: Erro ao acessar plano para o usuário {user.email} (ID: {user.id}): {e}", exc_info=True)
    return user

class Plan(db.Model):
    """ Modelo da base de dados para os Planos de Assinatura. """
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False)
    max_analises_por_mes = db.Column(db.Integer, nullable=True, default=-1) # -1 para ilimitado

    permite_exportacao_csv = db.Column(db.Boolean, nullable=False, default=False)
    permite_seguranca_seo_avancado = db.Column(db.Boolean, nullable=False, default=False)
    permite_salvar_relatorios = db.Column(db.Boolean, nullable=False, default=False)
    permite_sitemap_avancado = db.Column(db.Boolean, nullable=False, default=False)
    preco_mensal = db.Column(db.Float, nullable=False, default=0.0)

    users = db.relationship('User', backref='current_plan', lazy=True)

    def __repr__(self):
        return f"Plan('{self.nome}', Preço: {self.preco_mensal}')"

class User(db.Model, UserMixin):
    """ Modelo da base de dados para os Utilizadores (clientes). """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)

    plan_id = db.Column(db.Integer, db.ForeignKey('plan.id'), nullable=False, default=1) # Default 1 para plano Gratuito
    # Campo 'is_admin' foi removido pois o admin terá um login/lógica separados.

    reports = db.relationship('AnalysisReport', backref='author', lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

class AnalysisReport(db.Model):
    """ Modelo da base de dados para os Relatórios de Análise. """
    id = db.Column(db.Integer, primary_key=True)
    url_analisada = db.Column(db.String(200), nullable=False)
    data_criacao = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='CONCLUIDO')
    resultado_json = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"AnalysisReport('{self.url_analisada}', '{self.status}')"

class IpUsage(db.Model):
    """ Modelo da base de dados para registrar o último uso de análise por IP. """
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), unique=True, nullable=False)
    last_analysis_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"IpUsage(IP='{self.ip_address}', LastUsed='{self.last_analysis_time}')"