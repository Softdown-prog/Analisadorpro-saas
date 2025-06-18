# app/routes.py

from flask import render_template, url_for, flash, redirect, Blueprint, Response, abort, request, current_app
from flask_login import login_user, current_user, logout_user, login_required
from app import db, bcrypt
# Removida importação de CreateProUserForm, mantida SitemapForm
from app.forms import RegistrationForm, LoginForm, AnalysisForm, SitemapForm
from app.analysis.crawler import WebsiteAnalyzer
from urllib.parse import urlparse
import json
import io
import csv
from app.models import AnalysisReport, User, Plan
import logging

# Configuração do logging (para que logs apareçam no console do servidor)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bp = Blueprint('routes', __name__)

@bp.route("/")
@bp.route("/home")
def home():
    return render_template('home.html', title='Início')

@bp.route("/dashboard", methods=['GET', 'POST'])
@login_required
def dashboard():
    form = AnalysisForm()

    if form.validate_on_submit():
        url_a_analisar = form.url.data
        try:
            # Garante que current_user.current_plan está carregado
            if not current_user.current_plan:
                # Caso o plano não seja carregado por algum motivo
                logging.error(f"Usuário {current_user.email} (ID: {current_user.id}) sem plano associado no dashboard.")
                flash('Erro: Seu plano não foi definido corretamente. Contacte o suporte.', 'danger')
                return redirect(url_for('routes.dashboard'))

            analisador = WebsiteAnalyzer(url_a_analisar, user_plan=current_user.current_plan)
            resultados = analisador.analyze()

            if resultados.get("error"):
                flash(resultados["error"], 'danger')
                return redirect(url_for('routes.dashboard'))

            if current_user.current_plan.permite_salvar_relatorios:
                novo_relatorio = AnalysisReport(
                    url_analisada=url_a_analisar,
                    author=current_user,
                    status='CONCLUIDO',
                    resultado_json=json.dumps(resultados)
                )
                db.session.add(novo_relatorio)
                db.session.commit()
                resultados['id'] = novo_relatorio.id

                flash('Análise concluída e relatório salvo com sucesso!', 'success')
            else:
                flash(f'Análise concluída! Para salvar e acessar seus relatórios, faça upgrade para o plano Premium.', 'info')
                resultados['id'] = 'TEMP-' + str(len(json.dumps(resultados)))

            return render_template('resultado.html', title='Resultado da Análise', resultados=resultados, url=url_a_analisar)
        except Exception as e:
            logging.error(f"Erro inesperado durante a análise para {url_a_analisar}: {e}", exc_info=True)
            flash(f'Ocorreu um erro inesperado durante a análise: {e}', 'danger')
            return redirect(url_for('routes.dashboard'))

    return render_template('dashboard.html', title='Dashboard', form=form,
                           nome_plano=current_user.current_plan.nome if current_user.current_plan else 'N/A')

@bp.route("/meus_relatorios")
@login_required
def meus_relatorios():
    if not current_user.current_plan or not current_user.current_plan.permite_salvar_relatorios:
        flash('Seu plano atual não permite o acesso a relatórios salvos. Faça upgrade para o plano Premium.', 'warning')
        return redirect(url_for('routes.dashboard'))

    from app.models import AnalysisReport
    page = request.args.get('page', 1, type=int)
    reports = AnalysisReport.query.filter_by(author=current_user)\
        .order_by(AnalysisReport.data_criacao.desc()).paginate(page=page, per_page=10)

    return render_template('meus_relatorios.html', title='Meus Relatórios', reports=reports,
                           nome_plano=current_user.current_plan.nome,
                           permite_exportacao=current_user.current_plan.permite_exportacao_csv)

@bp.route("/relatorio/<int:report_id>")
@login_required
def ver_relatorio(report_id):
    if not current_user.current_plan or not current_user.current_plan.permite_salvar_relatorios:
        flash('Seu plano atual não permite o acesso a relatórios salvos. Faça upgrade para o plano Premium.', 'warning')
        return redirect(url_for('routes.dashboard'))

    from app.models import AnalysisReport
    report = AnalysisReport.query.get_or_404(report_id)
    if report.author != current_user:
        abort(403)

    resultados = json.loads(report.resultado_json)
    resultados['id'] = report.id

    return render_template('resultado.html', title='Resultado da Análise',
                           resultados=resultados, url=report.url_analisada)

@bp.route("/relatorio/<int:report_id>/exportar")
@login_required
def exportar_csv(report_id):
    if not current_user.current_plan or not current_user.current_plan.permite_exportacao_csv:
        flash('Seu plano atual não permite a exportação de relatórios CSV. Faça upgrade para ter acesso a este recurso.', 'warning')
        abort(403)

    from app.models import AnalysisReport
    report = AnalysisReport.query.get_or_404(report_id)
    if report.author != current_user:
        abort(403)

    resultados = json.loads(report.resultado_json)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Tipo de Análise', 'Item Verificado', 'Resultado/Status'])

    if resultados.get('seo_check'):
        seo = resultados['seo_check']
        writer.writerow(['SEO', 'Title', f"{seo['title']['text']} ({seo['title']['length']})"])
        writer.writerow(['SEO', 'Meta Description', f"{seo['meta_description']['text']} ({seo['meta_description']['length']})"])
    if resultados.get('onpage_seo_check'):
        onpage_seo = resultados['onpage_seo_check']
        writer.writerow(['SEO On-Page', 'H1s', ', '.join(onpage_seo['h_tags']['h1']) if onpage_seo['h_tags']['h1'] else 'Nenhum'])
        writer.writerow(['SEO On-Page', 'Imagens Alt Faltando', ', '.join(onpage_seo['img_alt_tags']['missing']) if onpage_seo['img_alt_tags']['missing'] else 'Nenhum'])
        writer.writerow(['SEO On-Page', 'Imagens Alt Vazias', ', '.join(onpage_seo['img_alt_tags']['empty']) if onpage_seo['img_alt_tags']['empty'] else 'Nenhum'])
        writer.writerow(['SEO On-Page', 'Robots Meta', onpage_seo['robots_meta']['content'] if onpage_seo['robots_meta']['present'] else 'Não presente'])
        writer.writerow(['SEO On-Page', 'Canonical URL', onpage_seo['canonical_tag']['href'] if onpage_seo['canonical_tag']['present'] else 'Não presente'])

    if resultados.get('link_check') and resultados['link_check'].get('broken_links'):
        for link in resultados['link_check']['broken_links']:
            writer.writerow(['Link Quebrado', link['url'], link['status_code']])

    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=relatorio_{urlparse(report.url_analisada).netloc}.csv"}
    )

@bp.route("/termos")
def termos_de_uso():
    return render_template('termos_de_uso.html', title='Termos de Uso')

@bp.route("/privacidade")
def politica_de_privacidade():
    return render_template('politica_de_privacidade.html', title='Política de Privacidade')

@bp.route("/registo", methods=['GET', 'POST'])
def registo():
    from app.models import User, Plan
    if current_user.is_authenticated:
        return redirect(url_for('routes.dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            free_plan = Plan.query.get(1)
            if not free_plan:
                logging.error("Erro no registro: Plano gratuito (ID 1) não encontrado no banco de dados. Execute 'flask db-commands init-plans'.")
                flash('Erro interno: Plano gratuito não configurado. Contacte o suporte.', 'danger')
                return redirect(url_for('routes.registo'))

            user = User(username=form.username.data, email=form.email.data,
                        password=hashed_password, plan_id=free_plan.id,
                        analises_restantes_mes=None) # analises_restantes_mes será populado por cron job ou na atualização de plano

            db.session.add(user)
            db.session.commit()
            logging.info(f"Novo usuário registrado: {user.email} com plano {free_plan.nome} (ID: {free_plan.id})")
            flash('Sua conta foi criada com sucesso! Você já pode fazer login.', 'success')
            return redirect(url_for('routes.login'))
        except Exception as e:
            logging.error(f"Erro ao registrar usuário {form.email.data}: {e}", exc_info=True)
            flash(f'Erro ao criar conta: {e}. Por favor, tente novamente.', 'danger')
            db.session.rollback()
    return render_template('registo.html', title='Registo', form=form)

@bp.route("/login", methods=['GET', 'POST'])
def login():
    from app.models import User
    if current_user.is_authenticated:
        return redirect(url_for('routes.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        logging.info(f"Tentativa de login para o email: {form.email.data}")
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            logging.info(f"Usuário {user.email} encontrado (ID: {user.id}). Verificando senha...")
            logging.info(f"Senha hash no DB para {user.email}: {user.password}")
            logging.info(f"Senha fornecida para {user.email}: {form.password.data}")

            # Verifica se a senha hash do DB não é nula antes de comparar
            if user.password and bcrypt.check_password_hash(user.password, form.password.data):
                logging.info(f"Senha correta para {user.email}. Tentando login_user...")
                login_user(user, remember=form.remember.data)
                # Verifica se o current_user foi carregado após login
                if current_user.is_authenticated:
                    logging.info(f"Login bem-sucedido para: {user.email} (current_user.is_authenticated: True)")
                    # Tenta acessar o plano após login para verificar se a relação funciona
                    try:
                        plan_name = current_user.current_plan.nome if current_user.current_plan else 'N/A'
                        logging.info(f"Plano do usuário logado: {plan_name}")
                    except Exception as e:
                        logging.error(f"Erro ao acessar current_plan para usuário logado {user.email}: {e}", exc_info=True)
                else:
                    logging.error(f"Login_user falhou para {user.email}: current_user não autenticado após chamada.")
                    flash('Erro interno ao processar login. Contacte o suporte.', 'danger')
                    return redirect(url_for('routes.login'))
                
                flash('Login realizado com sucesso!', 'success')
                return redirect(url_for('routes.dashboard'))
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
    return redirect(url_for('routes.home'))

# Rota /admin/create-pro-user foi removida.