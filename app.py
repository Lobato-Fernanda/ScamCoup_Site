from flask import Flask, render_template, request
import sqlite3
from datetime import datetime
from urllib.parse import urlparse
import re
import os
import cv2
app = Flask(__name__)
UPLOAD_FOLDER = "uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)
def ler_qrcode(caminho):

    imagem = cv2.imread(caminho)

    if imagem is None:
        return None

    detector = cv2.QRCodeDetector()

    conteudo, pontos, _ = detector.detectAndDecode(
        imagem
    )

    if conteudo:
        return conteudo

    return None
def criar_banco():
    conexao = sqlite3.connect("database.db")
    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mensagem TEXT NOT NULL,
            score INTEGER NOT NULL,
            nivel TEXT NOT NULL,
            motivos TEXT NOT NULL,
            data TEXT NOT NULL
        )
    """)

    conexao.commit()
    conexao.close()


def analisar_mensagem(mensagem):
    texto = mensagem.lower()

    score = 0
    motivos = []

    regras = [
        (
            ["urgente", "urgência", "imediatamente", "agora", "última chance"],
            20,
            "A mensagem utiliza linguagem de urgência."
        ),

        (
            ["senha", "cpf", "dados pessoais", "dados bancários", "cartão"],
            30,
            "A mensagem solicita ou menciona informações sensíveis."
        ),

        (
            ["pix", "pagamento", "pagar", "taxa", "boleto"],
            25,
            "A mensagem envolve solicitação de pagamento."
        ),

        (
            ["clique aqui", "acesse", "link", "http://", "https://"],
            20,
            "A mensagem tenta induzir o usuário a acessar um link."
        ),

        (
            ["ganhou", "prêmio", "sorteio", "parabéns", "premiado"],
            20,
            "A mensagem contém promessa de prêmio ou benefício."
        ),

        (
            ["bloqueado", "suspenso", "cancelado", "expirado"],
            20,
            "A mensagem utiliza ameaça de bloqueio ou cancelamento."
        ),

        (
            ["banco", "receita federal", "correios", "gov.br", "receita"],
            10,
            "A mensagem menciona uma instituição conhecida."
        )
    ]

    for palavras, pontos, motivo in regras:

        for palavra in palavras:
            if palavra in texto:

                score += pontos
                motivos.append(motivo)

                break

    if score > 100:
        score = 100

    motivos = list(dict.fromkeys(motivos))

    if score <= 25:
        nivel = "Baixo"

    elif score <= 50:
        nivel = "Moderado"

    elif score <= 75:
        nivel = "Alto"

    else:
        nivel = "Crítico"

    if not motivos:
        motivos.append(
            "Nenhum dos principais padrões de golpe cadastrados foi identificado."
        )

    return score, nivel, motivos


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/analisar", methods=["GET", "POST"])
def analisar():

    if request.method == "POST":

        mensagem = request.form["mensagem"]

        score, nivel, motivos = analisar_mensagem(mensagem)
        categorias = identificar_golpe(
    mensagem
)
        data = datetime.now().strftime("%d/%m/%Y %H:%M")

        conexao = sqlite3.connect("database.db")
        cursor = conexao.cursor()

        cursor.execute("""
            INSERT INTO analises
            (mensagem, score, nivel, motivos, data)
            VALUES (?, ?, ?, ?, ?)
        """, (
            mensagem,
            score,
            nivel,
            " | ".join(motivos),
            data
        ))

        conexao.commit()
        conexao.close()

        return render_template(
            "resultado.html",
            mensagem=mensagem,
            score=score,
            nivel=nivel,
            motivos=motivos,
            categorias=categorias
        )

    return render_template("analisar.html")
def analisar_link(url):

    score = 0
    motivos = []

    url = url.strip()

    # adiciona protocolo temporariamente para conseguir analisar
    url_analise = url

    if not url.startswith(("http://", "https://")):
        url_analise = "http://" + url

    try:
        partes = urlparse(url_analise)
        dominio = partes.hostname or ""
    except:
        dominio = ""

    # REGRA 1 - HTTP sem HTTPS
    if url_analise.startswith("http://"):
        score += 20
        motivos.append(
            "O endereço não utiliza HTTPS."
        )

    # REGRA 2 - URL muito longa
    if len(url) > 80:
        score += 15
        motivos.append(
            "O endereço possui um tamanho incomum."
        )

    # REGRA 3 - muitos hífens
    if dominio.count("-") >= 2:
        score += 15
        motivos.append(
            "O domínio possui vários hífens, característica comum em endereços falsificados."
        )

    # REGRA 4 - muitos subdomínios
    if dominio.count(".") >= 3:
        score += 15
        motivos.append(
            "O endereço possui muitos subdomínios."
        )

    # REGRA 5 - presença de endereço IP
    padrao_ip = r"^\d{1,3}(\.\d{1,3}){3}$"

    if re.match(padrao_ip, dominio):
        score += 30
        motivos.append(
            "O endereço utiliza um IP diretamente em vez de um domínio."
        )

    # REGRA 6 - palavras típicas de phishing
    palavras_suspeitas = [
        "login",
        "verify",
        "verificar",
        "seguro",
        "conta",
        "update",
        "atualizar",
        "premio",
        "premiado",
        "pix",
        "pagamento",
        "confirmar",
        "senha",
        "banco",
        "correios"
    ]

    for palavra in palavras_suspeitas:
        if palavra in url.lower():

            score += 10

            motivos.append(
                f"O endereço contém o termo suspeito: '{palavra}'."
            )

            break

    # REGRA 7 - caractere @
    if "@" in url:
        score += 25
        motivos.append(
            "O endereço contém o caractere @, que pode ser usado para mascarar o destino."
        )

    # REGRA 8 - muitos números no domínio
    quantidade_numeros = sum(
        caractere.isdigit()
        for caractere in dominio
    )

    if quantidade_numeros >= 5:

        score += 10

        motivos.append(
            "O domínio possui uma quantidade incomum de números."
        )

    if score > 100:
        score = 100

    if score <= 25:
        nivel = "Baixo"

    elif score <= 50:
        nivel = "Moderado"

    elif score <= 75:
        nivel = "Alto"

    else:
        nivel = "Crítico"

    if not motivos:
        motivos.append(
            "Nenhum padrão estrutural suspeito foi identificado."
        )

    return score, nivel, motivos, dominio

@app.route("/historico")
def historico():

    conexao = sqlite3.connect("database.db")
    conexao.row_factory = sqlite3.Row

    cursor = conexao.cursor()

    cursor.execute("""
        SELECT *
        FROM analises
        ORDER BY id DESC
    """)

    analises = cursor.fetchall()

    conexao.close()

    return render_template(
        "historico.html",
        analises=analises
    )

@app.route("/link", methods=["GET", "POST"])
def link():

    if request.method == "POST":

        url = request.form["url"]

        score, nivel, motivos, dominio = analisar_link(url)

        data = datetime.now().strftime(
            "%d/%m/%Y %H:%M"
        )

        conexao = sqlite3.connect("database.db")
        cursor = conexao.cursor()

        cursor.execute("""
            INSERT INTO analises
            (mensagem, score, nivel, motivos, data)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "LINK: " + url,
            score,
            nivel,
            " | ".join(motivos),
            data
        ))

        conexao.commit()
        conexao.close()

        return render_template(
            "resultado_link.html",
            url=url,
            dominio=dominio,
            score=score,
            nivel=nivel,
            motivos=motivos
        )

    return render_template(
        "analisar_link.html"
    )
@app.route("/qrcode", methods=["GET", "POST"])
def qrcode():

    if request.method == "POST":

        if "arquivo" not in request.files:

            return render_template(
                "qrcode.html",
                erro="Nenhum arquivo foi enviado."
            )

        arquivo = request.files["arquivo"]

        if arquivo.filename == "":

            return render_template(
                "qrcode.html",
                erro="Selecione uma imagem."
            )

        extensoes = (
            ".png",
            ".jpg",
            ".jpeg",
            ".webp"
        )

        if not arquivo.filename.lower().endswith(
            extensoes
        ):

            return render_template(
                "qrcode.html",
                erro="Formato de imagem inválido."
            )

        nome_seguro = (
            str(datetime.now().timestamp())
            .replace(".", "")
            + ".png"
        )

        caminho = os.path.join(
            app.config["UPLOAD_FOLDER"],
            nome_seguro
        )

        arquivo.save(caminho)

        conteudo = ler_qrcode(caminho)

        try:
            os.remove(caminho)
        except:
            pass

        if not conteudo:

            return render_template(
                "qrcode.html",
                erro="Não foi possível identificar um QR Code nesta imagem."
            )

        # verifica se conteúdo parece URL

        if conteudo.startswith(
            ("http://", "https://")
        ):

            score, nivel, motivos, dominio = analisar_link(
                conteudo
            )

        else:

            score = 10
            nivel = "Baixo"
            dominio = "Não se aplica"

            motivos = [
                "O QR Code contém texto, mas não foi identificado como um endereço web."
            ]

        data = datetime.now().strftime(
            "%d/%m/%Y %H:%M"
        )

        conexao = sqlite3.connect(
            "database.db"
        )

        cursor = conexao.cursor()

        cursor.execute("""
            INSERT INTO analises
            (mensagem, score, nivel, motivos, data)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "QR CODE: " + conteudo,
            score,
            nivel,
            " | ".join(motivos),
            data
        ))

        conexao.commit()
        conexao.close()

        return render_template(
            "resultado_qr.html",
            conteudo=conteudo,
            score=score,
            nivel=nivel,
            motivos=motivos,
            dominio=dominio
        )

    return render_template(
        "qrcode.html"
    )

def identificar_golpe(texto):

    texto = texto.lower()

    categorias = []

    if any(
        palavra in texto
        for palavra in [
            "senha",
            "login",
            "confirmar conta",
            "acesse sua conta"
        ]
    ):

        categorias.append(
            "Phishing / Roubo de credenciais"
        )

    if any(
        palavra in texto
        for palavra in [
            "pix",
            "transferência",
            "pagamento"
        ]
    ):

        categorias.append(
            "Golpe financeiro / PIX"
        )

    if any(
        palavra in texto
        for palavra in [
            "encomenda",
            "entrega",
            "correios",
            "taxa alfandegária"
        ]
    ):

        categorias.append(
            "Golpe de falsa entrega"
        )

    if any(
        palavra in texto
        for palavra in [
            "prêmio",
            "ganhou",
            "premiado",
            "sorteio"
        ]
    ):

        categorias.append(
            "Golpe de falso prêmio"
        )

    if any(
        palavra in texto
        for palavra in [
            "banco",
            "conta bancária",
            "cartão"
        ]
    ):

        categorias.append(
            "Possível falsificação bancária"
        )

    if not categorias:

        categorias.append(
            "Não identificado"
        )
    return categorias

criar_banco()


if __name__ == "__main__":
    app.run(debug=False)