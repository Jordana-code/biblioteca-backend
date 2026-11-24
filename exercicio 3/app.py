import os
from datetime import timedelta

from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from werkzeug.exceptions import HTTPException

from database import criar_tabelas
from routes.autores import autores_bp
from routes.livros import livros_bp
from routes.auth import auth_bp

app = Flask(__name__)

# Respostas JSON com acentos legíveis ("não" em vez de "não")
# e com as chaves na mesma ordem em que foram escritas no código
app.json.ensure_ascii = False
app.json.sort_keys = False


# ==========================================================
# CONFIGURAÇÃO DO JWT
# ==========================================================

# Em produção a chave DEVE vir da variável de ambiente JWT_SECRET_KEY.
# O valor fixo abaixo só pode ser usado neste exercício local.
app.config["JWT_SECRET_KEY"] = os.environ.get(
    "JWT_SECRET_KEY",
    "chave-local-do-exercicio-3-nao-usar-em-producao"
)
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)

jwt = JWTManager(app)


# ==========================================================
# BLUEPRINTS
# ==========================================================

app.register_blueprint(autores_bp)
app.register_blueprint(livros_bp)
app.register_blueprint(auth_bp)


# ==========================================================
# PADRÃO DAS RESPOSTAS DE ERRO
# ==========================================================

def resposta_erro(mensagem, status):
    return jsonify({
        "erro": True,
        "mensagem": mensagem,
        "status": status
    }), status


# Mensagens para os erros gerados pelo próprio Flask
# (ex.: rota que não existe ou método não permitido)
MENSAGENS_PADRAO = {
    400: "Requisição inválida",
    401: "Acesso não autorizado",
    403: "Acesso proibido",
    404: "Rota não encontrada",
    405: "Método não permitido para esta rota",
    409: "Conflito com os dados existentes",
    415: "Tipo de conteúdo não suportado",
    500: "Erro interno no servidor"
}


@app.errorhandler(HTTPException)
def tratar_erro_http(erro):
    # As rotas usam abort(status, description="mensagem") e caem aqui.
    # Sem mensagem personalizada, usa a mensagem padrão em português.
    mensagem = erro.description

    if mensagem == type(erro).description:
        mensagem = MENSAGENS_PADRAO.get(erro.code, erro.name)

    return resposta_erro(mensagem, erro.code)


@app.errorhandler(Exception)
def tratar_erro_inesperado(erro):
    # O detalhe técnico fica só no log do servidor. O cliente recebe uma
    # mensagem genérica, sem SQL, caminhos de arquivos ou chaves.
    app.logger.exception("Erro inesperado")
    return resposta_erro("Erro interno no servidor", 500)


# ==========================================================
# RESPOSTAS DO JWT: TOKEN AUSENTE, INVÁLIDO OU EXPIRADO
# ==========================================================

@jwt.unauthorized_loader
def token_ausente(motivo):
    return resposta_erro("Acesso recusado: token não informado", 401)


@jwt.invalid_token_loader
def token_invalido(motivo):
    return resposta_erro("Acesso recusado: token inválido", 401)


@jwt.expired_token_loader
def token_expirado(cabecalho, dados):
    return resposta_erro("Acesso recusado: token expirado, faça login novamente", 401)


# ==========================================================
# CABEÇALHO ADICIONADO EM TODAS AS RESPOSTAS
# ==========================================================

@app.after_request
def adicionar_versao_api(resposta):
    resposta.headers["X-API-Versao"] = "1.0"
    return resposta


# ==========================================================
# ROTA INICIAL
# ==========================================================

@app.route("/", methods=["GET"])
def inicio():
    return jsonify({
        "api": "Biblioteca",
        "versao": "1.0",
        "recursos": ["/autores", "/livros", "/cadastro", "/login", "/meu-acesso"]
    }), 200


# Garante que as tabelas existam ao iniciar a API
criar_tabelas()


if __name__ == "__main__":
    # O modo debug pode expor detalhes internos: só liga com FLASK_DEBUG=1
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
