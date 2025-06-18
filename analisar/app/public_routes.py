# app/public_routes.py
from flask import render_template, url_for, flash, redirect, Blueprint, request, abort
from flask_login import current_user
from app import db
from app.forms import AnalysisForm # Importa apenas o que é necessário aqui
from app.analysis.crawler import WebsiteAnalyzer
from app.models import Plan, IpUsage
from datetime import datetime, timedelta
import json # Para lidar com resultados do crawler
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bp = Blueprint('public', __name__)

@bp.route("/")
@bp.route("/home")
def home():
    return render_template('home.html', title='Início')

@bp.route("/analisar", methods=['GET', 'POST'])
def analisar():
    form = AnalysisForm()

    user_ip = request.remote_addr
    # Para ambientes de produção atrás de proxies (como Nginx), usar request.headers.get('X-Forwarded-For', request.remote_addr)

    free_plan = Plan.query.get(1)
    if not free_plan:
        logging.critical("Erro FATAL: Plano gratuito (ID 1) não encontrado no banco de dados. Execute 'flask db-commands init-plans'.")
        abort(500, description="O serviço não está configurado corretamente. Por favor, contacte o administrador.")

    if form.validate_on_submit():
        # Lógica de RESTRIÇÃO POR IP (APENAS PARA USUÁRIOS NÃO LOGADOS)
        if not current_user.is_authenticated:
            ip_record = IpUsage.query.filter_by(ip_address=user_ip).first()
            if ip_record:
                time_since_last_analysis = datetime.utcnow() - ip_record.last_analysis_time
                if time_since_last_analysis < timedelta(hours=24):
                    hours_remaining = round((timedelta(hours=24) - time_since_last_analysis).total_seconds() / 3600)
                    flash(f'Você pode realizar apenas uma análise gratuita a cada 24 horas. Para uso ilimitado e sem restrições, faça login e assine um plano Premium.', 'warning')
                    return redirect(url_for('public.analisar'))
            
            # Se não houver registro ou o tempo passou, atualiza/cria o registro de IP
            if ip_record:
                ip_record.last_analysis_time = datetime.utcnow()
            else:
                new_ip_usage = IpUsage(ip_address=user_ip, last_analysis_time=datetime.utcnow())
                db.session.add(new_ip_usage)
            db.session.commit()
            logging.info(f"Análise gratuita registrada para IP: {user_ip}")

        url_a_analisar = form.url.data
        try:
            # Usuários não logados sempre usam as características do plano gratuito
            # Usuários logados, mas com plano gratuito, usarão as características do plano gratuito
            plan_for_analysis = current_user.current_plan if current_user.is_authenticated and current_user.current_plan else free_plan

            analisador = WebsiteAnalyzer(url_a_analisar, user_plan=plan_for_analysis)
            resultados = analisador.analyze()

            if resultados.get("error"):
                flash(resultados["error"], 'danger')
                return redirect(url_for('public.analisar'))

            # No modo público/gratuito, os relatórios NÃO SÃO SALVOS no banco de dados
            # Relatórios só são salvos se o usuário estiver autenticado E o plano permitir
            if current_user.is_authenticated and plan_for_analysis.permite_salvar_relatorios:
                from app.models import AnalysisReport # Importar aqui para evitar ciclo
                novo_relatorio = AnalysisReport(
                    url_analisada=url_a_analisar,
                    author=current_user,
                    status='CONCLUIDO',
                    resultado_json=json.dumps(resultados)
                )
                db.session.add(novo_relatorio)
                db.session.commit()
                resultados['id'] = novo_relatorio.id
                flash('Análise concluída e relatório salva com sucesso!', 'success')
            else:
                if current_user.is_authenticated:
                    flash(f'Análise concluída! Seu plano ({plan_for_analysis.nome}) não permite o salvamento de relatórios. Faça upgrade para o plano Premium para salvar e acessar seus relatórios.', 'info')
                else:
                    flash('Análise concluída! Esta análise não será salva. Faça login e assine um plano Premium para salvar e acessar seus relatórios.', 'info')
                
                resultados['id'] = 'TEMP-' + str(len(json.dumps(resultados))) # ID temporário para exibição

            return render_template('resultado.html', title='Resultado da Análise', resultados=resultados, url=url_a_analisar,
                                   nome_plano=plan_for_analysis.nome,
                                   is_authenticated=current_user.is_authenticated)

        except Exception as e:
            logging.error(f"Erro inesperado durante a análise para {url_a_analisar}: {e}", exc_info=True)
            flash(f'Ocorreu um erro inesperado durante a análise: {e}', 'danger')
            return redirect(url_for('public.analisar'))

    return render_template('dashboard.html', title='Analisar', form=form,
                           nome_plano=free_plan.nome, # Exibe sempre o plano gratuito para esta página
                           is_authenticated=current_user.is_authenticated)

@bp.route("/termos")
def termos_de_uso():
    return render_template('termos_de_uso.html', title='Termos de Uso')

@bp.route("/privacidade")
def politica_de_privacidade():
    return render_template('politica_de_privacidade.html', title='Política de Privacidade')