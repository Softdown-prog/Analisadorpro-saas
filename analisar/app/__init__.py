# app/__init__.py
import os
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate # Importar Migrate

load_dotenv()

db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
migrate = Migrate() # Instanciar Migrate

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'uma_chave_secreta_padrao_muito_segura')
    
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '3306')
    DB_NAME = os.getenv('DB_NAME', 'analisadorpro_db')

    app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.config['ADMIN_USERNAME'] = os.getenv('ADMIN_USERNAME', 'adminsoft')
    app.config['ADMIN_PASSWORD_HASH'] = bcrypt.generate_password_hash(
        os.getenv('ADMIN_PASSWORD', 'supersecretpassword')
    ).decode('utf-8')

    app.config['MERCADOPAGO_ACCESS_TOKEN'] = os.getenv('MERCADOPAGO_ACCESS_TOKEN')
    app.config['MERCADOPAGO_CLIENT_ID'] = os.getenv('MERCADOPAGO_CLIENT_ID')
    app.config['MERCADOPAGO_CLIENT_SECRET'] = os.getenv('MERCADOPAGO_CLIENT_SECRET')

    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db) # Inicializar Flask-Migrate com o app e db

    from .payment_routes import init_mercadopago_sdk
    init_mercadopago_sdk(app)

    # NOVO: Registrar os comandos CLI AQUI novamente
    from .cli_commands import db_commands
    app.cli.add_command(db_commands)

    with app.app_context():
        # db.create_all() será substituído por Flask-Migrate após a primeira migração
        # Com Flask-Migrate, você não chama db.create_all() diretamente mais.
        # No entanto, se as migrações não forem executadas, as tabelas não existirão.
        # POR SEGURANÇA DURANTE O DESENVOLVIMENTO, PODE-SE MANTER db.create_all() AQUI TEMPORARIAMENTE
        # E REMOVÊ-LO DEPOIS QUE AS MIGRAÇÕES INICIAIS FOREM APLICADAS COM SUCESSO.
        # Mas o erro no log indica que ele nem está chegando aqui se o db-commands não é achado.
        
        # Vamos manter ele COMENTADO, e confiar que 'flask db upgrade' vai criar as tabelas.
        # from . import models
        # db.create_all() # COMENTADO/REMOVIDO APÓS A PRIMEIRA MIGRAÇÃO COM FLASK-MIGRATE

        # NOVOS BLUEPRINTS
        from .public_routes import bp as public_bp
        from .auth_routes import bp as auth_bp
        from .pro_routes import bp as pro_bp
        from .soft_routes import bp as soft_bp
        from .payment_routes import bp as payment_bp

        app.register_blueprint(public_bp)
        app.register_blueprint(auth_bp)
        app.register_blueprint(pro_bp, url_prefix='/pro')
        app.register_blueprint(soft_bp, url_prefix='/soft')
        app.register_blueprint(payment_bp)

    return app