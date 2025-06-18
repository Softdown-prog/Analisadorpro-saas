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

    # --- Plano Profissional (ID 2) ---
    profissional_plan = Plan.query.filter_by(id=2).first()
    if not profissional_plan:
        profissional_plan = Plan(id=2, nome='Profissional')
        db.session.add(profissional_plan)
        print('Plano "Profissional" adicionado.')
    profissional_plan.max_analises_por_mes = 15
    profissional_plan.permite_exportacao_csv = True
    profissional_plan.permite_seguranca_seo_avancado = True
    profissional_plan.permite_salvar_relatorios = True
    profissional_plan.permite_sitemap_avancado = True
    profissional_plan.preco_mensal = 39.00
    print('Plano "Profissional" atualizado/verificado.')

    # --- Plano Empresa (ID 3) ---
    empresa_plan = Plan.query.filter_by(id=3).first()
    if not empresa_plan:
        empresa_plan = Plan(id=3, nome='Empresa')
        db.session.add(empresa_plan)
        print('Plano "Empresa" adicionado.')
    empresa_plan.max_analises_por_mes = -1
    empresa_plan.permite_exportacao_csv = True
    empresa_plan.permite_seguranca_seo_avancado = True
    empresa_plan.permite_salvar_relatorios = True
    empresa_plan.permite_sitemap_avancado = True
    empresa_plan.preco_mensal = 119.00
    print('Plano "Empresa" atualizado/verificado.')

    db.session.commit()
    print('Todos os planos de assinatura inicializados/verificados com sucesso no banco de dados!')

    # Remover ou comentar a seção create_admin_command se você não quiser criar admin via script.