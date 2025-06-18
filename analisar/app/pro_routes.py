# app/pro_routes.py
from flask import render_template, url_for, flash, redirect, Blueprint, Response, abort, request
from flask_login import current_user, login_required
from app import db
from app.forms import AnalysisForm, SitemapForm # Incluir SitemapForm
from app.analysis.crawler import WebsiteAnalyzer
from urllib.parse import urlparse
import json
import io
import csv
from app.models import AnalysisReport, User, Plan
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bp = Blueprint('pro', __name__)

@bp.before_request
@login_required
def require_pro_plan_access():
    if current_user.is_authenticated and current_user.current_plan:
        if current_user.current_plan.nome == 'Gratuito' or current_user.current_plan.nome == 'Básico':
            flash('Seu plano atual não dá acesso total à área PRO. Faça upgrade para desbloquear todas as funcionalidades.', 'warning')
            return redirect(url_for('public.analisar'))
    
@bp.route("/dashboard")
def dashboard_pro():
    form = AnalysisForm()

    if form.validate_on_submit():
        url_a_analisar = form.url.data
        try:
            analisador = WebsiteAnalyzer(url_a_analisar, user_plan=current_user.current_plan)
            resultados = analisador.analyze()

            if resultados.get("error"):
                flash(resultados["error"], 'danger')
                return redirect(url_for('pro.dashboard_pro'))

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
            return render_template('resultado.html', title='Resultado da Análise PRO', resultados=resultados, url=url_a_analisar,
                                   nome_plano=current_user.current_plan.nome,
                                   is_authenticated=True)

        except Exception as e:
            logging.error(f"Erro inesperado durante a análise PRO para {url_a_analisar}: {e}", exc_info=True)
            flash(f'Ocorreu um erro inesperado durante a análise: {e}', 'danger')
            return redirect(url_for('pro.dashboard_pro'))

    return render_template('dashboard.html', title='Dashboard PRO', form=form,
                           nome_plano=current_user.current_plan.nome,
                           is_authenticated=True)


@bp.route("/meus_relatorios")
def meus_relatorios():
    from app.models import AnalysisReport
    page = request.args.get('page', 1, type=int)
    reports = AnalysisReport.query.filter_by(author=current_user)\
        .order_by(AnalysisReport.data_criacao.desc()).paginate(page=page, per_page=10)

    return render_template('meus_relatorios.html', title='Meus Relatórios PRO', reports=reports,
                           nome_plano=current_user.current_plan.nome,
                           permite_exportacao=current_user.current_plan.permite_exportacao_csv)

@bp.route("/relatorio/<int:report_id>")
def ver_relatorio(report_id):
    from app.models import AnalysisReport
    report = AnalysisReport.query.get_or_404(report_id)
    if report.author != current_user:
        abort(403)

    resultados = json.loads(report.resultado_json)
    resultados['id'] = report.id

    return render_template('resultado.html', title='Resultado da Análise PRO',
                           resultados=resultados, url=report.url_analisada,
                           nome_plano=current_user.current_plan.nome,
                           is_authenticated=True)


@bp.route("/relatorio/<int:report_id>/exportar")
def exportar_csv(report_id):
    if not current_user.current_plan.permite_exportacao_csv:
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
        if 'message' not in onpage_seo:
            writer.writerow(['SEO On-Page', 'H1s', ', '.join(onpage_seo['h_tags']['h1']) if onpage_seo['h_tags']['h1'] else 'Nenhum'])
            writer.writerow(['SEO On-Page', 'Imagens Alt Faltando', ', '.join(onpage_seo['img_alt_tags']['missing']) if onpage_seo['img_alt_tags']['missing'] else 'Nenhum'])
            writer.writerow(['SEO On-Page', 'Imagens Alt Vazias', ', '.join(onpage_seo['img_alt_tags']['empty']) if onpage_seo['img_alt_tags']['empty'] else 'Nenhum'])
            writer.writerow(['SEO On-Page', 'Robots Meta', onpage_seo['robots_meta']['content'] if onpage_seo['robots_meta']['present'] else 'Não presente'])
            writer.writerow(['SEO On-Page', 'Canonical URL', onpage_seo['canonical_tag']['href'] if onpage_seo['canonical_tag']['present'] else 'Não presente'])
        else:
             writer.writerow(['SEO On-Page', 'Recurso Restrito', onpage_seo['message']])

    if resultados.get('link_check') and resultados['link_check'].get('broken_links'):
        for link in resultados['link_check']['broken_links']:
            writer.writerow(['Link Quebrado', link['url'], link['status_code']])

    output.seek(0)
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=relatorio_{urlparse(report.url_analisada).netloc}.csv"}
    )

@bp.route("/sitemap_generator", methods=['GET', 'POST']) # NOVO: Rota GET para a página do gerador de sitemap
def sitemap_generator():
    form = SitemapForm() # Usa o SitemapForm que já existe

    if not current_user.current_plan.permite_sitemap_avancado:
        flash('Seu plano atual não permite a geração de sitemap. Faça upgrade.', 'warning')
        return redirect(url_for('pro.dashboard_pro')) # Redireciona para o dashboard PRO

    if form.validate_on_submit():
        url = form.url.data
        if not url:
            flash('Nenhuma URL fornecida para o sitemap.', 'danger')
            return redirect(url_for('pro.sitemap_generator')) # Redireciona para a própria página

        try:
            # Aqui você pode chamar um método no WebsiteAnalyzer ou uma função separada
            # que rastreie o site e gere o sitemap.
            # Supondo que WebsiteAnalyzer agora tem um método para sitemap:
            analisador = WebsiteAnalyzer(url, user_plan=current_user.current_plan)
            sitemap_xml_content = analisador.generate_sitemap_xml() # Este método precisa ser implementado no WebsiteAnalyzer

            response_headers = {
                'Content-Type': 'application/xml',
                'Content-Disposition': f'attachment; filename=sitemap_{urlparse(url).netloc}.xml'
            }
            return Response(sitemap_xml_content, headers=response_headers)
        except Exception as e:
            logging.error(f"Erro ao gerar sitemap para {url}: {e}", exc_info=True)
            flash(f'Ocorreu um erro ao gerar o sitemap: {e}', 'danger')
            return redirect(url_for('pro.sitemap_generator'))

    return render_template('sitemap_generator.html', title='Gerador de Sitemap XML', form=form)


# REMOVIDO: A antiga rota @bp.route("/gerar-sitemap", methods=['POST']) foi substituída pela sitemap_generator