import re
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os
import requests
from replit import db

from database import (
    get_user_data, set_user_data,
    salvar_transacao_db, salvar_compra_parcelada_db,
    get_categorias, get_contas_conhecidas, get_cartoes_conhecidos,
    salvar_lembrete_db, get_lembretes_db, adicionar_conta_db
)

VERIFY_TOKEN = "teste"
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")

def send_whatsapp_message(phone_number, message):
    """
    Função para enviar uma mensagem de texto simples de volta para o utilizador.
    """
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {"messaging_product": "whatsapp", "to": phone_number, "text": {"body": message}}

    print(f"Tentando enviar para {phone_number}: '{message}'")
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        print(f"Resposta da API da Meta ao enviar: {response.status_code}")
        # print(response.json()) # Descomente para depuração detalhada
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro ao enviar mensagem: {e}")
        print(f"Resposta recebida: {e.response.text if e.response else 'Nenhuma resposta'}")

    return None

# --- Funções de Processamento de Mensagens ---

def processar_mensagem(user_id, texto):
    """
    Função principal que decide o que fazer com a mensagem do utilizador.
    """
    texto_lower = texto.lower()

    # --- Lógica para Comandos Específicos ---
    if texto_lower.startswith("meta "):
        return processar_comando_meta(user_id, texto)

    if texto_lower == "lembrete":
        return (
            "Para registar um lembrete, copie o modelo abaixo, preencha e envie:",
            "lembrete: [descrição]\nvalor: [valor]\nvence dia: [dia]"
        )

    if texto_lower.startswith("lembrete:"):
        return processar_comando_lembrete(user_id, texto)

    if texto_lower == "parcelado":
        return gerar_modelo_parcelado(user_id)

    if texto_lower.startswith("parcelado:"):
        return processar_compra_parcelada(user_id, texto)

    # --- Lógica para Respostas a Perguntas do Bot ---
    ultima_pergunta = get_user_data(user_id, "ultima_pergunta", None)
    if ultima_pergunta:
        return processar_resposta_pergunta(user_id, texto_lower, ultima_pergunta)

    # --- Se não for nenhum comando, trata como uma transação normal ---
    return processar_transacao_normal(user_id, texto)

def processar_comando_lembrete(user_id, texto):
    """Extrai dados de uma mensagem de lembrete formatada."""
    try:
        dados = {}
        for linha in texto.split('\n'):
            if ':' in linha:
                chave, valor = linha.split(':', 1)
                dados[chave.strip().lower()] = valor.strip()

        descricao = dados['lembrete']
        valor = float(dados['valor'].replace(',', '.'))
        dia_vencimento = int(dados['vence dia'])

        if not (1 <= dia_vencimento <= 31):
            return "❌ O dia do vencimento deve ser um número entre 1 e 31."

        lembrete_data = {
            "descricao": descricao, "valor": valor, 
            "dia_vencimento": dia_vencimento, "timestamp": datetime.now().isoformat()
        }
        salvar_lembrete_db(user_id, lembrete_data)
        return f"✅ Lembrete registado: '{descricao}' no valor de R$ {valor:.2f}, com vencimento todo dia {dia_vencimento}."
    except (ValueError, KeyError, IndexError):
        return "❌ Formato do lembrete inválido. Por favor, use o modelo exato que eu enviei."

def processar_comando_meta(user_id, texto):
    try:
        partes = texto.split()
        if len(partes) < 3:
            return "❌ Formato inválido. Use: meta [categoria] [valor]"

        nome_categoria = partes[1].capitalize()
        valor_meta = float(partes[2].replace(',', '.'))

        categorias_usuario = get_categorias(user_id)
        if nome_categoria not in categorias_usuario:
            return (f"❌ Categoria '{nome_categoria}' não encontrada.\n\n"
                    f"Categorias disponíveis são: {', '.join(categorias_usuario.keys())}")

        from database import salvar_meta_db
        salvar_meta_db(user_id, nome_categoria, valor_meta)
        return f"✅ Meta de R$ {valor_meta:.2f} definida para a categoria '{nome_categoria}'."

    except (ValueError, IndexError):
        return "❌ Formato inválido. Use: meta [categoria] [valor]"


def processar_resposta_pergunta(user_id, texto_resposta, ultima_pergunta):
    set_user_data(user_id, "ultima_pergunta", None) # Limpa a pergunta

    if texto_resposta == "sim":
        tipo_pergunta = ultima_pergunta.get("tipo")
        novo_item = ultima_pergunta.get("item")

        if tipo_pergunta == "nova_conta":
            adicionar_conta_db(user_id, novo_item)
            return f"✅ Conta '{novo_item.capitalize()}' adicionada com sucesso!"
        # Adicionar lógica para nova categoria aqui se necessário

    return "Ok, não vou adicionar."


def gerar_modelo_parcelado(user_id):
    """Gera as duas mensagens de instrução para compras parceladas."""
    cartoes = get_cartoes_conhecidos(user_id)
    instrucao = (
        "Para registar uma compra parcelada, por favor, copie o modelo abaixo, preencha os dados e envie:"
    )
    modelo = (
        "parcelado: [descrição da compra]\n"
        "valor: [valor total]\n"
        "parcelas: [Nº de parcelas]\n"
        f"cartão: [um de: {', '.join(cartoes)}]"
    )
    return instrucao, modelo

def processar_compra_parcelada(user_id, texto):
    """Extrai dados de uma mensagem de parcelamento formatada."""
    try:
        dados = {}
        linhas = texto.split('\n')

        descricao = linhas[0].split(':', 1)[1].strip()

        for linha in linhas[1:]:
            if ':' in linha:
                chave, valor = linha.split(':', 1)
                dados[chave.strip().lower()] = valor.strip()

        valor_total = float(dados['valor'].replace(',', '.'))
        num_parcelas = int(dados['parcelas'])
        cartao = dados['cartão'].capitalize()

        cartoes_conhecidos = get_cartoes_conhecidos(user_id)
        if cartao not in cartoes_conhecidos:
            return f"❌ Cartão '{cartao}' não reconhecido. Cartões disponíveis: {', '.join(cartoes_conhecidos)}."

        valor_parcela = valor_total / num_parcelas
        categoria = categorizar_transacao(descricao, 'despesa', user_id)

        compra_data = {
            "descricao": descricao, "valor_total": valor_total,
            "num_parcelas": num_parcelas, "cartao": cartao,
            "categoria": categoria, "data_inicio": datetime.now().isoformat()
        }
        salvar_compra_parcelada_db(user_id, compra_data)

        return (f"✅ Compra parcelada registada: '{descricao}'\n"
                f"Valor: R$ {valor_total:.2f} em {num_parcelas}x de R$ {valor_parcela:.2f}\n"
                f"Cartão: {cartao}")

    except (ValueError, KeyError, IndexError):
        return "❌ Formato da compra parcelada inválido. Por favor, use o modelo exato que eu enviei."

def processar_transacao_normal(user_id, texto):
    """Processa uma mensagem de transação normal (receita ou despesa)."""
    tipo, valor, descricao_original, metodo, cartao, conta = extrair_dados_transacao_normal(user_id, texto)

    if valor is None:
        # CORREÇÃO DO BUG: Verifica se o valor foi encontrado antes de prosseguir
        match_valor_unico = re.search(r'^[\d,.]+$', texto.strip())
        if match_valor_unico:
            return "Não entendi sua mensagem. Para registar, diga algo como 'Gastei 10 reais com pão'."
        return "Não consegui identificar um valor na sua mensagem. Tente novamente."

    categoria = categorizar_transacao(descricao_original, tipo, user_id)

    # Lógica para perguntar sobre contas/categorias desconhecidas...
    if tipo == 'receita' and conta is None:
        # Lógica para perguntar sobre nova conta
        pass # Implementação futura

    transacao_data = {
        "tipo": tipo, "descricao": descricao_original, "valor": valor,
        "categoria": categoria, "metodo": metodo, "cartao": cartao,
        "conta": conta, "timestamp": datetime.now().isoformat()
    }
    salvar_transacao_db(user_id, transacao_data)

    if tipo == 'despesa':
        return f"✅ Despesa registada: '{descricao_original}' (R$ {valor:.2f})."
    elif tipo == 'receita':
        return f"✅ Receita registada: '{descricao_original}' (R$ {valor:.2f})."

def extrair_dados_transacao_normal(user_id, texto):
    tipo, valor, metodo, cartao, conta = 'desconhecido', None, 'outro', None, None
    texto_lower = texto.lower()

    palavras_despesa = ['comprei', 'gastei', 'paguei']
    palavras_receita = ['recebi', 'ganhei', 'salário']

    if any(p in texto_lower for p in palavras_despesa): tipo = 'despesa'
    elif any(p in texto_lower for p in palavras_receita): tipo = 'receita'

    # Expressão regular mais robusta para encontrar valores monetários
    match_valor = re.search(r'[\d,.]+', texto)
    if match_valor and match_valor.group(0) not in ['.', ',']:
        try:
            valor = float(match_valor.group(0).replace(',', '.'))
        except ValueError:
            valor = None # Se a conversão falhar, o valor continua nulo

    if tipo == 'receita':
        metodo = 'débito'
        contas = get_contas_conhecidas(user_id).get('contas', [])
        for c in contas:
            if c.lower() in texto_lower:
                conta = c
                break
    elif tipo == 'despesa':
        if 'crédito' in texto_lower or 'cartao' in texto_lower or 'cartão' in texto_lower:
            metodo = 'crédito'
            cartoes = get_cartoes_conhecidos(user_id)
            for c in cartoes:
                if c.lower() in texto_lower:
                    cartao = c
                    break
        elif 'débito' in texto_lower or 'pix' in texto_lower or 'swile' in texto_lower:
            metodo = 'débito'
            contas = get_contas_conhecidas(user_id).get('contas', [])
            for c in contas:
                if c.lower() in texto_lower:
                    conta = c
                    break

    if categorizar_transacao(texto, 'despesa', user_id) == 'Pagamentos': metodo = 'débito'
    return tipo, valor, texto, metodo, cartao, conta

def categorizar_transacao(descricao, tipo, user_id):
    """Categoriza uma transação com base no tipo (receita ou despesa)."""
    categorias = get_categorias(user_id)
    descricao_lower = descricao.lower()

    # Define categorias específicas para receitas
    categorias_receita = {
        'Salário': ['salário'],
        'Outras Receitas': ['recebi', 'ganhei', 'investimentos']
    }

    if tipo == 'receita':
        for categoria, palavras in categorias_receita.items():
            if any(palavra in descricao_lower for palavra in palavras):
                return categoria
        return 'Outras Receitas' # Padrão para receitas não categorizadas

    elif tipo == 'despesa':
        for categoria, palavras in categorias.items():
            if categoria not in ['Salário', 'Outras Receitas']:
                if any(palavra in descricao_lower for palavra in palavras):
                    return categoria
    return 'Outros'

def verificar_e_enviar_lembretes():
    """
    Verifica todos os lembretes de todos os utilizadores e envia notificações
    para aqueles que estão próximos do vencimento.
    """
    hoje = datetime.now()
    chaves_lembretes = db.prefix("lembretes_") 

    for chave in chaves_lembretes:
        user_id = chave.split("_")[-1]
        lembretes = get_lembretes_db(user_id)

        for lembrete in lembretes:
            dia_vencimento = lembrete.get('dia_vencimento')

            # Lógica para avisar 2 dias antes
            dia_para_avisar = dia_vencimento - 2
            if dia_para_avisar <= 0:
                data_vencimento_mes_atual = datetime(hoje.year, hoje.month, dia_vencimento)
                data_aviso = data_vencimento_mes_atual - relativedelta(days=2)
                dia_para_avisar = data_aviso.day

            if hoje.day == dia_para_avisar:
                mensagem = (
                    f"🔔 Lembrete de Pagamento!\n\n"
                    f"Conta: {lembrete['descricao']}\n"
                    f"Valor: R$ {lembrete['valor']:.2f}\n"
                    f"Vence no dia: {dia_vencimento}"
                )
                send_whatsapp_message(user_id, mensagem)
                print(f"Enviando lembrete para {user_id} sobre '{lembrete['descricao']}'")

