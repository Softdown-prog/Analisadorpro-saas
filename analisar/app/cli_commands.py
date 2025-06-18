# app/cli_commands.py
import click
from flask.cli import with_appcontext
from app import db, bcrypt
from app.models import Plan, User

@click.group()
def db_commands():
    """Comandos relacionados ao banco de dados."""
    pass

@db_commands.command('init_plans')
@with_appcontext
def init_plans_command():
    """Inicializa/Atualiza os planos de assinatura no banco de dados.
    Define os planos Gratuito, Profissional e Empresa com suas respectivas características.
    """
    click.echo('Verificando/Inicializando planos de assinatura...')

    # --- Plano Gratuito (ID 1) ---
    free_plan = Plan.query.filter_by(id=1).first()
    if not free_plan:
        free_plan = Plan(id=1, nome='Gratuito')
        db.session.add(free_plan)
        click.echo('Plano "Gratuito" adicionado.')
    free_plan.max_analises_por_mes = -1 # Ilimitado para o gratuito
    free_plan.permite_exportacao_csv = False # Não permite exportação
    free_plan.permite_seguranca_seo_avancado = False # SEO reduzido, sem segurança
    free_plan.permite_salvar_relatorios = False # NÃO salva relatórios
    free_plan.permite_sitemap_avancado = False # Sitemap não é gratuito
    free_plan.preco_mensal = 0.0
    click.echo('Plano "Gratuito" atualizado/verificado.')

    # --- Plano Profissional (ID 2) ---
    # NOVO NOME para o antigo "Básico"
    profissional_plan = Plan.query.filter_by(id=2).first()
    if not profissional_plan:
        profissional_plan = Plan(id=2, nome='Profissional') # NOVO NOME
        db.session.add(profissional_plan)
        click.echo('Plano "Profissional" adicionado.')
    profissional_plan.max_analises_por_mes = 15 # Até 15 análises por mês
    profissional_plan.permite_exportacao_csv = True # Permite exportação para este plano
    profissional_plan.permite_seguranca_seo_avancado = True # SEO completo e segurança
    profissional_plan.permite_salvar_relatorios = True # Salva relatórios
    profissional_plan.permite_sitemap_avancado = True # Permite Sitemap
    profissional_plan.preco_mensal = 39.00 # NOVO PREÇO: R$ 39/mês
    click.echo('Plano "Profissional" atualizado/verificado.')

    # --- Plano Empresa (ID 3) ---
    # NOVO NOME para o antigo "Pro"
    empresa_plan = Plan.query.filter_by(id=3).first()
    if not empresa_plan:
        empresa_plan = Plan(id=3, nome='Empresa') # NOVO NOME
        db.session.add(empresa_plan)
        click.echo('Plano "Empresa" adicionado.')
    empresa_plan.max_analises_por_mes = -1 # Análises ilimitadas
    empresa_plan.permite_exportacao_csv = True
    empresa_plan.permite_seguranca_seo_avancado = True
    empresa_plan.permite_salvar_relatorios = True
    empresa_plan.permite_sitemap_avancado = True
    empresa_plan.preco_mensal = 119.00 # NOVO PREÇO: R$ 119/mês
    click.echo('Plano "Empresa" atualizado/verificado.')

    db.session.commit()
    click.echo('Todos os planos de assinatura inicializados/verificados com sucesso.')

@db_commands.command('create_admin')
@with_appcontext
@click.argument('email')
@click.argument('username')
@click.argument('password')
def create_admin_command(email, username, password):
    """Cria um usuário administrador com plano Empresa."""
    click.echo(f"Tentando criar usuário administrador: {email}")
    empresa_plan = Plan.query.filter_by(nome='Empresa').first() # Admin agora usa o plano Empresa
    if not empresa_plan:
        click.echo("Erro: Plano 'Empresa' não encontrado. Execute 'flask db-commands init-plans' primeiro.")
        return

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        click.echo(f"Erro: Usuário com email '{email}' já existe.")
        return

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    admin_user = User(
        username=username,
        email=email,
        password=hashed_password,
        plan_id=empresa_plan.id, # Admin com plano Empresa
    )
    db.session.add(admin_user)
    db.session.commit()
    click.echo(f"Usuário administrador '{username}' ({email}) criado com plano '{empresa_plan.nome}' com sucesso!")