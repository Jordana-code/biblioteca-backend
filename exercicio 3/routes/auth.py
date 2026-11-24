import re
import sqlite3

from flask import Blueprint, abort, current_app, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required
)
from werkzeug.security import check_password_hash, generate_password_hash

from database import conectar_banco

auth_bp = Blueprint("auth", __name__)

PERFIS_PERMITIDOS = ("usuario", "admin")

# Formato simples de e-mail: texto@texto, sem espaços (ex.: aluno@teste.com)
FORMATO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+$")


def ler_json():
    dados = request.get_json(silent=True)

    if not isinstance(dados, dict):
        abort(400, description="Envie os dados no corpo da requisição em formato JSON")

    return dados


def texto_preenchido(valor):
    return isinstance(valor, str) and valor.strip() != ""


# ----------------------------------------------------------
# POST /cadastro - CADASTRAR USUÁRIO (público)
# ----------------------------------------------------------

@auth_bp.route("/cadastro", methods=["POST"])
def cadastrar_usuario():
    dados = ler_json()

    nome = dados.get("nome")
    email = dados.get("email")
    senha = dados.get("senha")
    perfil = dados.get("perfil") or "usuario"

    faltando = [
        campo
        for campo, valor in (("nome", nome), ("email", email), ("senha", senha))
        if not texto_preenchido(valor)
    ]

    if faltando:
        abort(400, description="Campos obrigatórios ausentes ou inválidos: " + ", ".join(faltando))

    nome = nome.strip()
    email = email.strip().lower()

    if not FORMATO_EMAIL.match(email):
        abort(400, description="E-mail inválido")

    if not isinstance(perfil, str) or perfil.strip().lower() not in PERFIS_PERMITIDOS:
        abort(400, description="Perfil inválido. Use 'usuario' ou 'admin'")

    perfil = perfil.strip().lower()

    # A senha nunca vai para o banco em texto puro: só o hash
    senha_hash = generate_password_hash(senha)

    conexao = conectar_banco()

    try:
        cursor = conexao.execute("""
            INSERT INTO usuarios (nome, email, senha, perfil)
            VALUES (?, ?, ?, ?)
        """, (nome, email, senha_hash, perfil))

        conexao.commit()

        usuario_id = cursor.lastrowid

    except sqlite3.IntegrityError:
        # Violou o UNIQUE da coluna email: e-mail já cadastrado
        conexao.rollback()
        abort(409, description="E-mail já cadastrado")

    except sqlite3.Error:
        conexao.rollback()
        current_app.logger.exception("Erro ao cadastrar usuário")
        abort(500, description="Não foi possível cadastrar o usuário")

    finally:
        conexao.close()

    # A resposta não devolve a senha (nem o hash)
    return jsonify({
        "mensagem": "Usuário cadastrado com sucesso",
        "usuario": {
            "id": usuario_id,
            "nome": nome,
            "email": email,
            "perfil": perfil
        }
    }), 201


# ----------------------------------------------------------
# POST /login - VALIDAR CREDENCIAIS E GERAR O TOKEN (público)
# ----------------------------------------------------------

@auth_bp.route("/login", methods=["POST"])
def login():
    dados = ler_json()

    email = dados.get("email")
    senha = dados.get("senha")

    if not texto_preenchido(email) or not texto_preenchido(senha):
        abort(400, description="Informe o e-mail e a senha")

    email = email.strip().lower()

    conexao = conectar_banco()

    try:
        usuario = conexao.execute("""
            SELECT id, nome, email, senha, perfil
            FROM usuarios
            WHERE email = ?
        """, (email,)).fetchone()

    except sqlite3.Error:
        current_app.logger.exception("Erro ao consultar usuário no login")
        abort(500, description="Não foi possível realizar o login")

    finally:
        conexao.close()

    # Mesma mensagem para e-mail inexistente e senha errada,
    # para não revelar quais e-mails estão cadastrados
    if usuario is None or not check_password_hash(usuario["senha"], senha):
        abort(401, description="E-mail ou senha inválidos")

    token = create_access_token(
        identity=str(usuario["id"]),  # a identidade (sub) do JWT deve ser texto
        additional_claims={
            "nome": usuario["nome"],
            "email": usuario["email"],
            "perfil": usuario["perfil"]
        }
    )

    return jsonify({
        "mensagem": "Login realizado com sucesso",
        "access_token": token,
        "usuario": {
            "id": usuario["id"],
            "nome": usuario["nome"],
            "email": usuario["email"],
            "perfil": usuario["perfil"]
        }
    }), 200


# ----------------------------------------------------------
# GET /meu-acesso - IDENTIDADE DO USUÁRIO LOGADO (autenticado)
# ----------------------------------------------------------

@auth_bp.route("/meu-acesso", methods=["GET"])
@jwt_required()
def meu_acesso():
    identidade = get_jwt_identity()   # id do usuário gravado no token
    dados_token = get_jwt()           # demais informações do token

    return jsonify({
        "mensagem": "Acesso autorizado",
        "usuario": {
            "id": int(identidade),
            "nome": dados_token.get("nome"),
            "email": dados_token.get("email"),
            "perfil": dados_token.get("perfil")
        }
    }), 200
