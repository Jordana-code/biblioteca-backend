import sqlite3

from flask import Blueprint, abort, current_app, jsonify, request
from flask_jwt_extended import jwt_required

from database import conectar_banco

autores_bp = Blueprint("autores", __name__)


def ler_json():
    dados = request.get_json(silent=True)

    if not isinstance(dados, dict):
        abort(400, description="Envie os dados no corpo da requisição em formato JSON")

    return dados


def validar_autor(dados):
    nome = dados.get("nome")
    nacionalidade = dados.get("nacionalidade")

    if not isinstance(nome, str) or nome.strip() == "":
        abort(400, description="O campo 'nome' é obrigatório e não pode ser vazio")

    if nacionalidade is not None and not isinstance(nacionalidade, str):
        abort(400, description="O campo 'nacionalidade' deve ser um texto")

    if nacionalidade is not None:
        nacionalidade = nacionalidade.strip() or None

    return nome.strip(), nacionalidade


def autor_para_dict(autor):
    return {
        "id": autor["id"],
        "nome": autor["nome"],
        "nacionalidade": autor["nacionalidade"]
    }


# ----------------------------------------------------------
# GET /autores - LISTAR AUTORES (público)
# ----------------------------------------------------------

@autores_bp.route("/autores", methods=["GET"])
def listar_autores():
    conexao = conectar_banco()

    try:
        autores = conexao.execute("""
            SELECT id, nome, nacionalidade
            FROM autores
            ORDER BY id
        """).fetchall()

    except sqlite3.Error:
        current_app.logger.exception("Erro ao listar autores")
        abort(500, description="Não foi possível listar os autores")

    finally:
        conexao.close()

    return jsonify([autor_para_dict(autor) for autor in autores]), 200


# ----------------------------------------------------------
# GET /autores/<id> - BUSCAR AUTOR POR ID (público)
# ----------------------------------------------------------

@autores_bp.route("/autores/<int:id>", methods=["GET"])
def buscar_autor(id):
    conexao = conectar_banco()

    try:
        autor = conexao.execute("""
            SELECT id, nome, nacionalidade
            FROM autores
            WHERE id = ?
        """, (id,)).fetchone()

    except sqlite3.Error:
        current_app.logger.exception("Erro ao buscar autor")
        abort(500, description="Não foi possível buscar o autor")

    finally:
        conexao.close()

    if autor is None:
        abort(404, description="Autor não encontrado")

    return jsonify(autor_para_dict(autor)), 200


# ----------------------------------------------------------
# POST /autores - CADASTRAR AUTOR (autenticado)
# ----------------------------------------------------------

@autores_bp.route("/autores", methods=["POST"])
@jwt_required()
def cadastrar_autor():
    dados = ler_json()
    nome, nacionalidade = validar_autor(dados)

    conexao = conectar_banco()

    try:
        cursor = conexao.execute("""
            INSERT INTO autores (nome, nacionalidade)
            VALUES (?, ?)
        """, (nome, nacionalidade))

        conexao.commit()

        autor_id = cursor.lastrowid

    except sqlite3.Error:
        conexao.rollback()
        current_app.logger.exception("Erro ao cadastrar autor")
        abort(500, description="Não foi possível cadastrar o autor")

    finally:
        conexao.close()

    return jsonify({
        "mensagem": "Autor cadastrado com sucesso",
        "autor": {
            "id": autor_id,
            "nome": nome,
            "nacionalidade": nacionalidade
        }
    }), 201


# ----------------------------------------------------------
# PUT /autores/<id> - ATUALIZAR AUTOR (autenticado)
# ----------------------------------------------------------

@autores_bp.route("/autores/<int:id>", methods=["PUT"])
@jwt_required()
def atualizar_autor(id):
    dados = ler_json()
    nome, nacionalidade = validar_autor(dados)

    conexao = conectar_banco()

    try:
        resultado = conexao.execute("""
            UPDATE autores
            SET nome = ?, nacionalidade = ?
            WHERE id = ?
        """, (nome, nacionalidade, id))

        conexao.commit()

        alterados = resultado.rowcount

    except sqlite3.Error:
        conexao.rollback()
        current_app.logger.exception("Erro ao atualizar autor")
        abort(500, description="Não foi possível atualizar o autor")

    finally:
        conexao.close()

    if alterados == 0:
        abort(404, description="Autor não encontrado")

    return jsonify({
        "mensagem": "Autor atualizado com sucesso",
        "autor": {
            "id": id,
            "nome": nome,
            "nacionalidade": nacionalidade
        }
    }), 200


# ----------------------------------------------------------
# DELETE /autores/<id> - EXCLUIR AUTOR (autenticado)
# ----------------------------------------------------------

@autores_bp.route("/autores/<int:id>", methods=["DELETE"])
@jwt_required()
def excluir_autor(id):
    conexao = conectar_banco()

    try:
        resultado = conexao.execute("""
            DELETE FROM autores
            WHERE id = ?
        """, (id,))

        conexao.commit()

        excluidos = resultado.rowcount

    except sqlite3.IntegrityError:
        # FOREIGN KEY: o autor ainda possui livros cadastrados
        conexao.rollback()
        abort(409, description="Não é possível excluir o autor: existem livros vinculados a ele")

    except sqlite3.Error:
        conexao.rollback()
        current_app.logger.exception("Erro ao excluir autor")
        abort(500, description="Não foi possível excluir o autor")

    finally:
        conexao.close()

    if excluidos == 0:
        abort(404, description="Autor não encontrado")

    return jsonify({
        "mensagem": "Autor excluído com sucesso",
        "id": id
    }), 200
