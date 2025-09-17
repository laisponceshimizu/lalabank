from replit import db
from datetime import datetime

# --- Funções Genéricas ---
def get_user_data(user_id, key, default_value):
    return db.get(f"{key}_{user_id}", default_value)

def set_user_data(user_id, key, value):
    db[f"{key}_{user_id}"] = value

# --- Transações ---
def get_transacoes_db(user_id):
    return get_user_data(user_id, "transacoes", [])

def salvar_transacao_db(user_id, data):
    transacoes = get_transacoes_db(user_id)
    transacoes.append(data)
    set_user_data(user_id, "transacoes", transacoes)

def get_compras_parceladas_db(user_id):
    return get_user_data(user_id, "parceladas", [])

def salvar_compra_parcelada_db(user_id, data):
    compras = get_compras_parceladas_db(user_id)
    compras.append(data)
    set_user_data(user_id, "parceladas", compras)

# --- Configurações (Categorias, Contas, etc.) ---
def get_categorias(user_id):
    default = {
        'Pagamentos': ['cartão de crédito', 'fatura', 'pagamento fatura'],
        'Compras': ['mercado pago', 'mercado livre', 'compras a vista', 'compras parceladas', 'computec'],
        'Assinaturas': ['assinatura', 'apple', 'netflix'], 'Investimentos': ['poupança', 'investi'],
        'Cuidados Pessoais': ['barbearia'], 'Educação': ['educação', 'curso', 'livro', 'puc'],
        'Saúde': ['farmacia', 'médico', 'remédio'],
        'Alimentação': ['ifood', 'marmitex', 'mercado', 'restaurante', 'dualcoffe', 'café', 'pizza', 'lanche'],
        'Transporte': ['carro', 'combustivel', 'combustível', 'uber', '99', 'gasolina', 'transporte'],
        'Salário': ['salário'], 'Outras Receitas': ['recebi', 'ganhei'], 'Outros': []
    }
    return get_user_data(user_id, "categorias", default)

def adicionar_categoria_db(user_id, nome, palavras_str):
    categorias = get_categorias(user_id)
    palavras = [p.strip().lower() for p in palavras_str.split(',')]
    categorias[nome.capitalize()] = palavras
    set_user_data(user_id, "categorias", categorias)

def apagar_categoria_db(user_id, nome):
    categorias = get_categorias(user_id)
    if nome in categorias:
        del categorias[nome]
        set_user_data(user_id, "categorias", categorias)

def get_contas_conhecidas(user_id):
    default = {'contas': ['Swile', 'Itaú', 'Nubank', 'Inter'], 'cartoes': ['Mercado Pago', 'Nubank', 'Itaú']}
    user_contas = get_user_data(user_id, "contas", default)
    if isinstance(user_contas, list): # Auto-correção para formato antigo
        set_user_data(user_id, "contas", default)
        return default
    return user_contas

def get_cartoes_conhecidos(user_id):
    return get_contas_conhecidas(user_id).get('cartoes', [])

def adicionar_conta_db(user_id, nome):
    contas = get_contas_conhecidas(user_id)
    nome_cap = nome.capitalize()
    if nome_cap not in contas['contas']: contas['contas'].append(nome_cap)
    if nome_cap not in contas['cartoes']: contas['cartoes'].append(nome_cap)
    set_user_data(user_id, "contas", contas)

def apagar_conta_db(user_id, nome):
    contas = get_contas_conhecidas(user_id)
    if nome in contas.get('contas', []): contas['contas'].remove(nome)
    if nome in contas.get('cartoes', []): contas['cartoes'].remove(nome)
    set_user_data(user_id, "contas", contas)

def get_regras_cartoes_db(user_id):
    default = {'Mercado Pago': 28, 'Nubank': 25, 'Itaú': 20}
    return get_user_data(user_id, "regras_cartoes", default)

def salvar_regras_cartao_db(user_id, regras):
    regras_atuais = get_regras_cartoes_db(user_id)
    for cartao, dia in regras.items():
        if dia.isdigit():
            regras_atuais[cartao] = int(dia)
    set_user_data(user_id, "regras_cartoes", regras_atuais)

# --- Metas ---
def get_metas_db(user_id):
    return get_user_data(user_id, "metas", {})

def salvar_meta_db(user_id, categoria, valor):
    metas = get_metas_db(user_id)
    metas[categoria] = valor
    set_user_data(user_id, "metas", metas)

def apagar_meta_db(user_id, categoria):
    metas = get_metas_db(user_id)
    if categoria in metas:
        del metas[categoria]
        set_user_data(user_id, "metas", metas)

# --- Lembretes ---
def get_lembretes_db(user_id):
    return get_user_data(user_id, "lembretes", [])

def salvar_lembrete_db(user_id, data):
    lembretes = get_lembretes_db(user_id)
    lembretes.append(data)
    set_user_data(user_id, "lembretes", lembretes)

def apagar_lembrete_db(user_id, timestamp):
    lembretes = get_lembretes_db(user_id)
    novos = [l for l in lembretes if l.get('timestamp') != timestamp]
    set_user_data(user_id, "lembretes", novos)

