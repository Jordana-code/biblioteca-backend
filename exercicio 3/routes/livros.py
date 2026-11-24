import sqlite3
from datetime import date

from flask import Blueprint, abort, current_app, jsonify, request
from flask_jwt_extended import jwt_required

from database import conectar_banco

livros_bp = Blueprint("livros", __name__)

# Maior número que cabe em uma coluna INTEGER do SQLite
LIMITE_INTEIRO = 2 ** 63 - 1


def ler_json():
    dados = request.get_json(silent=True)

    if not isinstance(dados, dict):
        abort(400, description="Envie os dados no corpo da requisição em formato JSON")

    return dados


def converter_inteiro(valor):
    # Aceita 10 ou "10". Para qualquer outra coisa devolve None.
    if isinstance(valor, bool):  # true/false não são números válidos aqui
        return None

    if isinstance(valor, str):
        try:
            valor = int(valor.strip())
        except ValueError:
            return None

    if isinstance(valor, int) and abs(valor) <= LIMITE_INTEIRO:
        return valor

    return None


def validar_livro(dados):
    titulo = dados.get("titulo")
    autor_id = converter_inteiro(dados.get("autor_id"))
    ano = dados.get("ano")

    if not isinstance(titulo, str) or titulo.strip() == "":
        abort(400, description="O campo 'titulo' é obrigatório e não pode ser vazio")

    if autor_id is None or autor_id <= 0:
        abort(400, description="O campo 'autor_id' é obrigatório e deve ser um número inteiro positivo")

    # O ano é opcional, mas, se vier, precisa ser um ano válido
    if ano is not None:
        ano_atual = date.today().year
        ano = converter_inteiro(ano)

        if ano is None or ano < 1 or ano > ano_atual:
            abort(400, description=f"O campo 'ano' deve ser um número inteiro entre 1 e {ano_atual}")

    return titulo.strip(), ano, autor_id


def buscar_autor_por_id(conexao, autor_id):
    return conexao.execute("""
        SELECT id, nome
        FROM autores
        WHERE id = ?
    """, (autor_id,)).fetchone()


# ----------------------------------------------------------
# GET /livros - LISTAR LIVROS COM O AUTOR (público)
# ----------------------------------------------------------

@livros_bp.route("/livros", methods=["GET"])
def listar_livros():
    conexao = conectar_banco()

    try:
        livros = conexao.execute("""
            SELECT
                livros.id,
                livros.titulo,
                livros.ano,
                livros.autor_id,
                autores.nome AS autor
            FROM livros
            JOIN autores
                ON livros.autor_id = autores.id
            ORDER BY livros.id
        """).fetchall()

    except sqlite3.Error:
        current_app.logger.exception("Erro ao listar livros")
        abort(500, description="Não foi possível listar os livros")

    finally:
        conexao.close()

    return jsonify([dict(livro) for livro in livros]), 200


# ----------------------------------------------------------
# GET /livros/<id> - BUSCAR LIVRO POR ID (público)
# ----------------------------------------------------------

@livros_bp.route("/livros/<int:id>", methods=["GET"])
def buscar_livro(id):
    conexao = conectar_banco()

    try:
        livro = conexao.execute("""
            SELECT
                livros.id,
                livros.titulo,
                livros.ano,
                livros.autor_id,
                autores.nome AS autor
            FROM livros
            JOIN autores
                ON livros.autor_id = autores.id
            WHERE livros.id = ?
        """, (id,)).fetchone()

    except sqlite3.Error:
        current_app.logger.exception("Erro ao buscar livro")
        abort(500, description="Não foi possível buscar o livro")

    finally:
        conexao.close()

    if livro is None:
        abort(404, description="Livro não encontrado")

    return jsonify(dict(livro)), 200


# ----------------------------------------------------------
# POST /livros - CADASTRAR LIVRO (autenticado)
# ----------------------------------------------------------

@livros_bp.route("/livros", methods=["POST"])
@jwt_required()
def cadastrar_livro():
    dados = ler_json()
    titulo, ano, autor_id = validar_livro(dados)

    conexao = conectar_banco()

    try:
        autor = buscar_autor_por_id(conexao, autor_id)

        if autor is None:
            abort(404, description="Autor não encontrado: informe um autor_id existente")

        cursor = conexao.execute("""
            INSERT INTO livros (titulo, ano, autor_id)
            VALUES (?, ?, ?)
        """, (titulo, ano, autor_id))

        conexao.commit()

        livro_id = cursor.lastrowid

    except sqlite3.Error:
        conexao.rollback()
        current_app.logger.exception("Erro ao cadastrar livro")
        abort(500, description="Não foi possível cadastrar o livro")

    finally:
        conexao.close()

    return jsonify({
        "mensagem": "Livro cadastrado com sucesso",
        "livro": {
            "id": livro_id,
            "titulo": titulo,
            "ano": ano,
            "autor_id": autor_id,
            "autor": autor["nome"]
        }
    }), 201


# ----------------------------------------------------------
# PUT /livros/<id> - ATUALIZAR LIVRO (autenticado)
# ----------------------------------------------------------

@livros_bp.route("/livros/<int:id>", methods=["PUT"])
@jwt_required()
def atualizar_livro(id):
    dados = ler_json()
    titulo, ano, autor_id = validar_livro(dados)

    conexao = conectar_banco()

    try:
        livro = conexao.execute("""
            SELECT id
            FROM livros
            WHERE id = ?
        """, (id,)).fetchone()

        if livro is None:
            abort(404, description="Livro não encontrado")

        autor = buscar_autor_por_id(conexao, autor_id)

        if autor is None:
            abort(404, description="Autor não encontrado: informe um autor_id existente")

        conexao.execute("""
            UPDATE livros
            SET titulo = ?, ano = ?, autor_id = ?
            WHERE id = ?
        """, (titulo, ano, autor_id, id))

        conexao.commit()

    except sqlite3.Error:
        conexao.rollback()
        current_app.logger.exception("Erro ao atualizar livro")
        abort(500, description="Não foi possível atualizar o livro")

    finally:
        conexao.close()

    return jsonify({
        "mensagem": "Livro atualizado com sucesso",
        "livro": {
            "id": id,
            "titulo": titulo,
            "ano": ano,
            "autor_id": autor_id,
            "autor": autor["nome"]
        }
    }), 200


# ----------------------------------------------------------
# DELETE /livros/<id> - EXCLUIR LIVRO (autenticado)
# ----------------------------------------------------------

@livros_bp.route("/livros/<int:id>", methods=["DELETE"])
@jwt_required()
def excluir_livro(id):
    conexao = conectar_banco()

    try:
        resultado = conexao.execute("""
            DELETE FROM livros
            WHERE id = ?
        """, (id,))

        conexao.commit()

        excluidos = resultado.rowcount

    except sqlite3.Error:
        conexao.rollback()
        current_app.logger.exception("Erro ao excluir livro")
        abort(500, description="Não foi possível excluir o livro")

    finally:
        conexao.close()

    if excluidos == 0:
        abort(404, description="Livro não encontrado")

    return jsonify({
        "mensagem": "Livro excluído com sucesso",
        "id": id
    }), 200
