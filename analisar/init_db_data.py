# init_db_data.py (Este arquivo deve ser criado na RAIZ do seu projeto, ao lado de run.py)
import os
from dotenv import load_dotenv
from app import create_app, db # Importa create_app e db de 'app'
from app.models import Plan, User # Importa os modelos

load_dotenv() # Carrega variáveis do .env

# Cria a instância do app Flask
app = create_app()

with app.app_context():
    print("Inicializando planos de assinatura no banco de dados...")
    # --- Plano Gratuito (ID 1) ---
    free_plan = Plan.query.filter_by(id=1).first()
    if not free_plan:
        free_plan = Plan(id=1, nome='Gratuito')
        db.session.add(free_plan)
        print('Plano "Gratuito" adicionado.')
    free_plan.max_analises_por_mes = -1
    free_plan.permite_exportacao_csv = False
    free_plan.permite_seguranca_seo_avancado = False
    free_plan.permite_salvar_relatorios = False
    free_plan.permite_sitemap_avancado = False
    free_plan.preco_mensal = 0.0
    print('Plano "Gratuito" atualizado/verificado.')

    # --- Plano Básico (ID 2) ---
    basic_plan = Plan.query.filter_by(id=2).first()
    if not basic_plan:
        basic_plan = Plan(id=2, nome='Básico')
        db.session.add(basic_plan)
        print('Plano "Básico" adicionado.')
    basic_plan.max_analises_por_mes = 100
    basic_plan.permite_exportacao_csv = False
    basic_plan.permite_seguranca_seo_avancado = False
    basic_plan.permite_salvar_relatorios = False
    basic_plan.permite_sitemap_avancado = False
    basic_plan.preco_mensal = 9.99
    print('Plano "Básico" atualizado/verificado.')

    # --- Plano Pro (ID 3) ---
    pro_plan = Plan.query.filter_by(id=3).first()
    if not pro_plan:
        pro_plan = Plan(id=3, nome='Pro')
        db.session.add(pro_plan)
        print('Plano "Pro" adicionado.')
    pro_plan.max_analises_por_mes = -1
    pro_plan.permite_exportacao_csv = True
    pro_plan.permite_seguranca_seo_avancado = True
    pro_plan.permite_salvar_relatorios = True
    pro_plan.permite_sitemap_avancado = True
    pro_plan.preco_mensal = 29.99
    print('Plano "Pro" atualizado/verificado.')

    db.session.commit()
    print('Todos os planos de assinatura inicializados/verificados com sucesso no banco de dados!')

    # Opcional: Criar um usuário admin inicial (SE VOCÊ QUISER CRIAR UM ADMIN POR SCRIPT, NÃO POR PAINEL SOFT)
    # APENAS PARA TESTE INICIAL. REMOVA ISTO APÓS A PRIMEIRA EXECUÇÃO OU USE COM CAUTELA!
    # print("Tentando criar usuário administrador de teste...")
    # admin_email = "admin@analisadorpro.com"
    # admin_username = "adminpro"
    # admin_password = "adminpassword123" # TROQUE ISSO POR UMA SENHA FORTE

    # existing_admin = User.query.filter_by(email=admin_email).first()
    # if not existing_admin:
    #     hashed_password = bcrypt.generate_password_hash(admin_password).decode('utf-8')
    #     new_admin = User(username=admin_username, email=admin_email, password=hashed_password,
    #                      plan_id=pro_plan.id) # Admin tem plano Pro
    #     db.session.add(new_admin)
    #     db.session.commit()
    #     print(f"Usuário administrador '{admin_username}' ({admin_email}) criado com plano '{pro_plan.nome}'.")
    # else:
    #     print(f"Usuário administrador '{admin_email}' já existe.")