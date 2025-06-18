# app/payment_routes.py
import mercadopago
from flask import Blueprint, request, redirect, url_for, flash, current_app, jsonify, render_template
from app import db, bcrypt
from app.models import User, Plan
from app.forms import SetPasswordForm
from datetime import datetime
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bp = Blueprint('payment', __name__)

mp_sdk_instance = None # Será inicializado por __init__.py

def init_mercadopago_sdk(app_instance):
    """Inicializa o SDK do Mercado Pago uma vez para toda a aplicação.
    Esta função é chamada de app/__init__.py
    """
    global mp_sdk_instance
    if mp_sdk_instance is None:
        mp_sdk_instance = mercadopago.SDK(app_instance.config['MERCADOPAGO_ACCESS_TOKEN'])
        logging.info("Mercado Pago SDK inicializado.")

# REMOVIDO: O decorador @bp.before_app_first_request e a função que ele decorava.

@bp.route("/planos")
def planos():
    plans = Plan.query.order_by(Plan.preco_mensal.asc()).all()
    # Não precisa de form aqui se não houver lógica de POST no planos.html
    return render_template('planos.html', title='Escolha Seu Plano', plans=plans)

@bp.route("/processar_pagamento/<int:plan_id>", methods=['POST'])
def processar_pagamento(plan_id):
    if mp_sdk_instance is None:
        # Se por algum motivo não inicializou, tenta forçar novamente (fallback)
        init_mercadopago_sdk(current_app) 
        if mp_sdk_instance is None:
            flash('Erro interno: Serviço de pagamento não inicializado.', 'danger')
            return redirect(url_for('public.analisar'))

    plan = Plan.query.get(plan_id)
    if not plan or plan.preco_mensal <= 0:
        flash('Plano inválido ou não pago.', 'danger')
        return redirect(url_for('payment.planos'))

    payer_email = current_user.email if current_user.is_authenticated else "anonimo@example.com"
    
    preference_data = {
        "items": [
            {
                "title": f"Assinatura Plano {plan.nome} - Analisador PRO",
                "quantity": 1,
                "unit_price": float(plan.preco_mensal),
                "currency_id": "BRL"
            }
        ],
        "payer": {
            "email": payer_email,
        },
        "back_urls": {
            "success": url_for('payment.pagamento_retorno', _external=True, status='success'),
            "failure": url_for('payment.pagamento_retorno', _external=True, status='failure'),
            "pending": url_for('payment.pagamento_retorno', _external=True, status='pending')
        },
        "auto_return": "approved",
        "external_reference": f"{plan.id}_{current_user.id if current_user.is_authenticated else 'anon'}_{datetime.utcnow().timestamp()}_{payer_email}",
        "notification_url": url_for('payment.mercadopago_webhook', _external=True)
    }

    try:
        preference_response = mp_sdk_instance.create_preference(preference_data)
        preference = preference_response["response"]
        
        checkout_url = preference.get("init_point")
        if current_app.debug:
            checkout_url = preference.get("sandbox_init_point", preference.get("init_point"))
        
        if not checkout_url:
            flash('Erro ao gerar URL de pagamento.', 'danger')
            return redirect(url_for('payment.planos'))

        logging.info(f"Preferência de pagamento criada para o plano {plan.nome}. Redirecionando para: {checkout_url}")
        return redirect(checkout_url)

    except Exception as e:
        logging.error(f"Erro ao processar pagamento com Mercado Pago: {e}", exc_info=True)
        flash('Erro ao iniciar processo de pagamento. Tente novamente mais tarde.', 'danger')
        return redirect(url_for('payment.planos'))

@bp.route("/pagamento_retorno")
def pagamento_retorno():
    status = request.args.get('status')
    collection_id = request.args.get('collection_id')
    collection_status = request.args.get('collection_status')
    external_reference = request.args.get('external_reference')

    logging.info(f"Retorno do Mercado Pago: Status={status}, Collection_ID={collection_id}, Collection_Status={collection_status}, External_Ref={external_reference}")

    if collection_status == 'approved':
        flash('Seu pagamento foi aprovado! Estamos processando seu acesso ao plano.', 'success')
        if external_reference and "anon" in external_reference:
            email_from_ref = external_reference.split('_')[-1]
            return redirect(url_for('auth.set_password_after_payment', email=email_from_ref, external_ref=external_reference))
        else:
            flash('Login para acessar seu plano!', 'info')
            return redirect(url_for('auth.login'))
    elif collection_status == 'pending':
        flash('Seu pagamento está pendente. Assim que for aprovado, seu plano será ativado.', 'info')
    else:
        flash('Seu pagamento não foi aprovado. Por favor, tente novamente ou entre em contato.', 'danger')
    
    return redirect(url_for('public.home'))

@bp.route("/webhooks/mercadopago", methods=['GET', 'POST'])
def mercadopago_webhook():
    data = request.json
    logging.info(f"Webhook do Mercado Pago recebido: {json.dumps(data)}")

    topic = request.args.get('topic')
    resource_id = request.args.get('id')

    if topic == 'payment' and resource_id:
        try:
            if mp_sdk_instance is None:
                init_mercadopago_sdk(current_app)
                if mp_sdk_instance is None:
                    logging.error("Erro no webhook: Mercado Pago SDK não inicializado.")
                    return jsonify({"status": "error", "message": "SDK not initialized"}), 500

            payment_info = mp_sdk_instance.get(f"/v1/payments/{resource_id}")
            
            if "response" not in payment_info or payment_info["response"] is None:
                logging.error(f"Webhook: Resposta vazia ou inválida da API do MP para ID {resource_id}.")
                return jsonify({"status": "error", "message": "Invalid MP API response"}), 400

            payment_status = payment_info["response"]["status"]
            payment_email = payment_info["response"]["payer"]["email"]
            external_reference = payment_info["response"].get("external_reference")

            logging.info(f"Webhook Payment ID: {resource_id}, Status: {payment_status}, Email: {payment_email}, ExternalRef: {external_reference}")

            if payment_status == 'approved':
                ref_parts = external_reference.split('_') if external_reference else []
                plan_id_ref = int(ref_parts[0]) if len(ref_parts) > 0 and ref_parts[0].isdigit() else None
                user_id_ref = int(ref_parts[1]) if len(ref_parts) > 1 and ref_parts[1].isdigit() else None
                
                plan_to_activate = Plan.query.get(plan_id_ref)

                if not plan_to_activate:
                    logging.error(f"Webhook: Plano {plan_id_ref} não encontrado para ativação.")
                    return jsonify({"status": "error", "message": "Plan not found"}), 400

                user = None
                if user_id_ref:
                    user = User.query.get(user_id_ref)
                
                if user is None:
                    user = User.query.filter_by(email=payment_email).first()

                if user:
                    if user.plan_id != plan_to_activate.id:
                        user.plan_id = plan_to_activate.id
                        db.session.commit()
                        logging.info(f"Webhook: Plano de usuário existente {user.email} atualizado para {plan_to_activate.nome}.")
                    else:
                        logging.info(f"Webhook: Usuário existente {payment_email} já tinha o plano {plan_to_activate.nome}.")
                else:
                    try:
                        new_user = User(
                            username=payment_email.split('@')[0],
                            email=payment_email,
                            password=bcrypt.generate_password_hash("TEMP_PASSWORD_NEEDS_RESET").decode('utf-8'),
                            plan_id=plan_to_activate.id
                        )
                        db.session.add(new_user)
                        db.session.commit()
                        logging.info(f"Webhook: Novo usuário '{payment_email}' criado com plano '{plan_to_activate.nome}' com senha temporária. Aguardando definição final de senha.")
                    except Exception as create_user_e:
                        logging.error(f"Webhook: Erro ao criar novo usuário '{payment_email}' após pagamento aprovado: {create_user_e}", exc_info=True)
                        db.session.rollback()
                        return jsonify({"status": "error", "message": "Failed to create new user after approved payment"}), 500

            return jsonify({"status": "success"}), 200

        except Exception as e:
            logging.error(f"Erro ao processar webhook do Mercado Pago: {e}", exc_info=True)
            return jsonify({"status": "error", "message": str(e)}), 400
    
    return jsonify({"status": "ignored", "message": "Topic or ID missing"}), 200