from flask import Flask, request, make_response, render_template

# Importa as funções dos nossos novos arquivos
from utils import processar_mensagem, send_whatsapp_message, verificar_e_enviar_lembretes
from database import (
    salvar_meta_db, apagar_categoria_db, apagar_conta_db, 
    adicionar_conta_db, adicionar_categoria_db, apagar_meta_db,
    salvar_regras_cartao_db, apagar_lembrete_db
)
from dashboard_calculations import calcular_dados_dashboard

app = Flask(__name__)

@app.route("/webhook", methods=['GET', 'POST'])
def webhook():
    if request.method == 'POST':
        data = request.get_json()
        try:
            message_data = data['entry'][0]['changes'][0]['value']['messages'][0]
            if message_data['type'] == 'text':
                phone_number = message_data['from']
                message_body = message_data['text']['body']

                resposta_bot = processar_mensagem(phone_number, message_body)

                if resposta_bot:
                    if isinstance(resposta_bot, tuple):
                        for msg in resposta_bot:
                            send_whatsapp_message(phone_number, msg)
                    else:
                        send_whatsapp_message(phone_number, resposta_bot)

        except (KeyError, IndexError):
            pass 

        return make_response("EVENT_RECEIVED", 200)

    elif request.method == 'GET':
        from utils import VERIFY_TOKEN
        token_sent = request.args.get("hub.verify_token")
        if token_sent == VERIFY_TOKEN:
            challenge = request.args.get("hub.challenge")
            return make_response(challenge, 200)
        return make_response('Invalid verification token', 403)

@app.route("/")
@app.route("/dashboard")
def dashboard_home():
    user_id = "554398091663" 
    return dashboard(user_id)

@app.route("/dashboard/<user_id>")
def dashboard(user_id):
    dados_dashboard = calcular_dados_dashboard(user_id)
    return render_template('dashboard.html', **dados_dashboard)

@app.route("/check_reminders")
def check_reminders():
    verificar_e_enviar_lembretes()
    return "Verificação de lembretes concluída."

# --- Rotas para a Aba de Configurações ---

@app.route("/add_category", methods=['POST'])
def add_category():
    data = request.get_json()
    adicionar_categoria_db(data['user_id'], data['nome_categoria'], data['palavras_chave'])
    return make_response("Categoria adicionada", 200)

@app.route("/delete_category", methods=['POST'])
def delete_category():
    data = request.get_json()
    apagar_categoria_db(data['user_id'], data['nome_categoria'])
    return make_response("Categoria apagada", 200)

@app.route("/add_account", methods=['POST'])
def add_account():
    data = request.get_json()
    adicionar_conta_db(data['user_id'], data['nome_conta'])
    return make_response("Conta adicionada", 200)

@app.route("/delete_account", methods=['POST'])
def delete_account():
    data = request.get_json()
    apagar_conta_db(data['user_id'], data['nome_conta'])
    return make_response("Conta apagada", 200)

@app.route("/add_meta", methods=['POST'])
def add_meta():
    data = request.get_json()
    salvar_meta_db(data['user_id'], data['categoria'], float(data['valor']))
    return make_response("Meta adicionada", 200)

@app.route("/delete_meta", methods=['POST'])
def delete_meta():
    data = request.get_json()
    apagar_meta_db(data['user_id'], data['categoria'])
    return make_response("Meta apagada", 200)

@app.route("/save_card_rules", methods=['POST'])
def save_card_rules():
    data = request.get_json()
    salvar_regras_cartao_db(data['user_id'], data['regras'])
    return make_response("Regras salvas", 200)

@app.route("/delete_lembrete", methods=['POST'])
def delete_lembrete():
    data = request.get_json()
    apagar_lembrete_db(data['user_id'], data['timestamp'])
    return make_response("Lembrete apagado", 200)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)

