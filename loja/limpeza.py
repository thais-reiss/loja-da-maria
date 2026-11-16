"""Regras de limpeza da planilha da Maria.

Cada função recebe o texto do jeito que a Maria escreveu e devolve o valor
limpo junto com um motivo para conferir (None quando não há dúvida).
"""
import re
import unicodedata
from datetime import date, datetime

ANO_PADRAO = 2026   # ano usado quando a Maria escreve só dia e mês
DIAS_LONGE = 60     # distância que faz uma data parecer fora do lugar

# Opções oficiais: a migração e o formulário do app usam as mesmas.
PAGAMENTOS = ["Pix", "Dinheiro", "Débito", "Crédito", "Fiado"]
ENTREGAS = ["Retirada na loja", "Correios", "Motoboy"]

MESES = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}

# palavra que a Maria usa -> opção oficial
PALAVRAS_PAGAMENTO = [
    ("pix", "Pix"),
    ("dinheiro", "Dinheiro"),
    ("debito", "Débito"),
    ("credito", "Crédito"),
    ("fiado", "Fiado"),
    ("depois paga", "Fiado"),
    ("fica devendo", "Fiado"),
]
PALAVRAS_ENTREGA = [
    ("loja", "Retirada na loja"),
    ("presencial", "Retirada na loja"),
    ("veio buscar", "Retirada na loja"),
    ("correios", "Correios"),
    ("sedex", "Correios"),
    ("motoboy", "Motoboy"),
]
BANDEIRAS = [("visa", "Visa"), ("master", "Mastercard"), ("elo", "Elo")]

# palavras que a Maria escreve errado ou sem acento -> jeito certo
CORRECOES_PRODUTO = {"brinc": "brinco", "cordao": "cordão", "lenco": "lenço", "perola": "pérola"}
CORRECOES_CLIENTE = {"joao": "João", "lucia": "Lúcia", "moca": "moça", "predio": "prédio"}

# código dos Correios: 2 letras, 9 números, 2 letras (ex.: AA123456789BR)
FORMATO_RASTREIO = r"[A-Z]{2}\d{9}[A-Z]{2}"


def _texto(valor):
    """Transforma a célula em texto, sem espaços nas pontas."""
    if valor is None:
        return ""
    return str(valor).strip()


def _simples(valor):
    """Texto em minúsculas e sem acentos, para comparar palavras."""
    texto = unicodedata.normalize("NFKD", _texto(valor).lower())
    return "".join(letra for letra in texto if not unicodedata.combining(letra))


sem_acento = _simples  # nome público, usado pela pesquisa do app


def _corrigir_palavras(texto, correcoes):
    """Troca, palavra por palavra, as que estão na lista de correções."""
    return re.sub(r"\w+", lambda m: correcoes.get(_simples(m[0]), m[0]), texto)


# ---------------------------------------------------------------- data

def _ler_data(texto):
    """Tenta cada formato que aparece na planilha. Devolve None se nenhum servir."""
    try:
        # 2026-08-06
        m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", texto)
        if m:
            return date(int(m[1]), int(m[2]), int(m[3]))

        # 04/08/2026 -> dia/mês/ano
        m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", texto)
        if m:
            return date(int(m[3]), int(m[2]), int(m[1]))

        # 8/16/26 -> mês/dia/ano (na planilha, ano com 2 dígitos vem sempre assim)
        m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{2})", texto)
        if m:
            return date(2000 + int(m[3]), int(m[1]), int(m[2]))

        # 05/08 -> dia/mês, sem ano
        m = re.fullmatch(r"(\d{1,2})/(\d{1,2})", texto)
        if m:
            return date(ANO_PADRAO, int(m[2]), int(m[1]))

        # 12 de marco
        m = re.fullmatch(r"(\d{1,2}) de (\w+)", texto)
        if m and m[2] in MESES:
            return date(ANO_PADRAO, MESES[m[2]], int(m[1]))
    except ValueError:
        pass  # números que não formam uma data, como 31/02
    return None


def limpar_data(valor, vizinha=None):
    """Devolve (data, motivo). `vizinha` é a última data confiável das linhas acima."""
    if isinstance(valor, datetime):
        return valor.date(), None
    if isinstance(valor, date):
        return valor, None

    texto = _simples(valor)
    if not texto:
        return None, "sem data"

    if texto in ("hj", "hoje", "ontem"):
        return vizinha, f"data escrita como '{texto}'; usei a da linha anterior"

    data = _ler_data(texto)
    if data is None:
        return None, f"não entendi a data '{texto}'"

    if vizinha and abs((data - vizinha).days) > DIAS_LONGE:
        return data, f"a data '{texto}' fica longe das vendas vizinhas"
    return data, None


# --------------------------------------------------------------- valor

def limpar_valor(valor):
    """Devolve (valor em reais, motivo). Aceita 'R$ 35', '28,00', '35+12 frete', '-40'."""
    if isinstance(valor, (int, float)):
        return float(valor), None

    texto = _simples(valor)
    if not texto:
        return None, "sem valor"

    numeros = re.findall(r"-?\d+(?:[.,]\d+)?", texto)
    if not numeros:
        return None, f"não entendi o valor '{texto}'"

    total = sum(float(numero.replace(",", ".")) for numero in numeros)
    if len(numeros) > 1:
        return total, f"valor escrito como '{texto}'; somei tudo"
    if total < 0:
        return total, "valor negativo; parece devolução"
    return total, None


# ----------------------------------------------------------- pagamento

def limpar_pagamento(pagamento, cartao=None, vezes=None, obs=None):
    """Devolve (forma, bandeira do cartão, parcelas, motivo)."""
    texto = _simples(pagamento)
    if not texto:
        texto = _simples(obs)  # às vezes ela anota "pagou no pix" na observação

    forma = None
    for palavra, opcao in PALAVRAS_PAGAMENTO:
        if palavra in texto:
            forma = opcao

    bandeira = None
    for palavra, nome in BANDEIRAS:
        if palavra in _simples(cartao) or palavra in texto:
            bandeira = nome

    parcelas = None
    if _texto(vezes).isdigit():
        parcelas = int(_texto(vezes))
    else:
        m = re.search(r"(\d+)\s*x", texto)  # "credito 3x visa"
        if m:
            parcelas = int(m[1])

    motivo = None
    if forma is None and "maqui" in texto:
        # maquininha: só o crédito pode ser parcelado
        if parcelas and parcelas > 1:
            forma = "Crédito"
        else:
            motivo = "foi na maquininha, mas não diz se débito ou crédito"
    elif forma is None:
        motivo = "sem forma de pagamento"

    if forma not in ("Débito", "Crédito", None):
        bandeira, parcelas = None, None  # pix, dinheiro e fiado não têm cartão
    return forma, bandeira, parcelas, motivo


# ------------------------------------------------------------- entrega

def limpar_entrega(valor):
    """Devolve (entrega, motivo). Vazio não é erro: ela só não anotou."""
    texto = _simples(valor)
    if not texto:
        return None, None
    for palavra, opcao in PALAVRAS_ENTREGA:
        if palavra in texto:
            return opcao, None
    return None, f"não entendi a entrega '{texto}'"


# ------------------------------------------------------------- produto

def limpar_produto(valor):
    """Devolve (produto, motivo)."""
    texto = _texto(valor).lower()
    if not texto:
        return None, "sem produto"
    texto = re.sub(r"^devolveu\s+", "", texto)  # "devolveu pulseira" -> "pulseira"
    texto = _corrigir_palavras(texto, CORRECOES_PRODUTO)
    return texto.capitalize(), None


def descobrir_tipo(produto, valor, obs):
    """Venda, Devolução ou Compra (o que ela comprou do fornecedor)."""
    texto = _simples(produto) + " " + _simples(obs)
    if "devolveu" in texto or (valor is not None and valor < 0):
        return "Devolução"
    if "comprei" in texto or "fornecedor" in texto or "nao e venda" in texto:
        return "Compra"
    return "Venda"


# ------------------------------------------------------------- cliente

def limpar_cliente(valor, obs=None):
    """Devolve (cliente, rastreio achado no lugar do nome, nota para a observação, motivo).

    Apelidos como 'a vizinha' ficam como estão: é assim que a Maria conhece a pessoa.
    """
    texto = _texto(valor)

    if re.fullmatch(FORMATO_RASTREIO, texto.upper()):
        nome = re.search(r"era [ao] (\w+)", _texto(obs))  # "era a Juliana"
        cliente = nome[1] if nome else None
        return cliente, texto.upper(), None, "o rastreio estava no lugar do nome"

    if re.fullmatch(r"\d{10,11}", texto):
        return None, None, f"telefone {texto}", None

    if _simples(texto) in ("", "nao lembro", "cliente"):
        return None, None, None, None
    return _corrigir_palavras(texto, CORRECOES_CLIENTE), None, None, None


# --------------------------------------------------------- linha inteira

def limpar_linha(linha, vizinha=None):
    """Recebe uma linha da planilha (dicionário com os títulos da Maria) e devolve a venda limpa."""
    motivos = []

    data, motivo = limpar_data(linha.get("data"), vizinha)
    motivos.append(motivo)

    produto, motivo = limpar_produto(linha.get("oq vendeu"))
    motivos.append(motivo)

    valor, motivo = limpar_valor(linha.get("valor"))
    motivos.append(motivo)

    forma, bandeira, parcelas, motivo = limpar_pagamento(
        linha.get("como pagou"), linha.get("cartao"), linha.get("vezes"), linha.get("obs")
    )
    motivos.append(motivo)

    entrega, motivo = limpar_entrega(linha.get("entrega ou loja"))
    motivos.append(motivo)

    cliente, rastreio_no_nome, nota, motivo = limpar_cliente(linha.get("pra quem"), linha.get("obs"))
    motivos.append(motivo)

    rastreio = _texto(linha.get("rastreio")).upper() or rastreio_no_nome
    obs = "; ".join(parte for parte in (_texto(linha.get("obs")), nota) if parte)

    return {
        "data": data,
        "produto": produto,
        "cliente": cliente,
        "valor": valor,
        "pagamento": forma,
        "cartao": bandeira,
        "parcelas": parcelas,
        "entrega": entrega,
        "rastreio": rastreio or None,
        "obs": obs or None,
        "tipo": descobrir_tipo(linha.get("oq vendeu"), valor, linha.get("obs")),
        "conferir": "; ".join(m for m in motivos if m) or None,
        "original": " | ".join(_texto(celula) for celula in linha.values()),
    }
