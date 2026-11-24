import os
import sqlite3


# ==========================================================
# CONEXÃO COM O BANCO DE DADOS
# ==========================================================

# O caminho é montado a partir da pasta deste arquivo: assim a API usa sempre
# o mesmo biblioteca.db, não importa de qual pasta ela seja executada.
CAMINHO_BANCO = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "biblioteca.db"
)


def conectar_banco():
    conexao = sqlite3.connect(CAMINHO_BANCO)

    # Permite acessar as colunas pelo nome: livro["titulo"]
    conexao.row_factory = sqlite3.Row

    # Ativa as chaves estrangeiras (no SQLite elas vêm desligadas)
    conexao.execute("PRAGMA foreign_keys = ON")

    return conexao


# ==========================================================
# CRIAÇÃO DAS TABELAS
# ==========================================================

def criar_tabelas():
    conexao = conectar_banco()

    try:
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS autores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                nacionalidade TEXT
            )
        """)

        # Regra do exercício: livro não pode ter título vazio
        # nem autor_id inexistente (garantido pela FOREIGN KEY)
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS livros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL CHECK (trim(titulo) <> ''),
                ano INTEGER,
                autor_id INTEGER NOT NULL,
                FOREIGN KEY (autor_id)
                    REFERENCES autores(id)
            )
        """)

        # email UNIQUE: não permite dois usuários com o mesmo e-mail
        # senha: guarda somente o hash, nunca a senha em texto puro
        # perfil: padrão 'usuario'; também aceita 'admin'
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                senha TEXT NOT NULL,
                perfil TEXT NOT NULL DEFAULT 'usuario'
                    CHECK (perfil IN ('usuario', 'admin'))
            )
        """)

        conexao.commit()

    except sqlite3.Error:
        conexao.rollback()
        raise

    finally:
        conexao.close()


# ==========================================================
# DADOS DE EXEMPLO (para testar a API)
# ==========================================================

def inserir_dados_exemplo():
    autores = [
        ("Machado de Assis", "Brasileira"),
        ("Clarice Lispector", "Brasileira"),
        ("José Saramago", "Portuguesa")
    ]

    livros = [
        ("Dom Casmurro", 1899, "Machado de Assis"),
        ("A Hora da Estrela", 1977, "Clarice Lispector"),
        ("Ensaio sobre a Cegueira", 1995, "José Saramago")
    ]

    conexao = conectar_banco()

    try:
        # Só insere o que ainda não existe (pode rodar mais de uma vez)
        for nome, nacionalidade in autores:
            conexao.execute("""
                INSERT INTO autores (nome, nacionalidade)
                SELECT ?, ?
                WHERE NOT EXISTS (
                    SELECT 1 FROM autores WHERE nome = ?
                )
            """, (nome, nacionalidade, nome))

        for titulo, ano, autor in livros:
            conexao.execute("""
                INSERT INTO livros (titulo, ano, autor_id)
                SELECT ?, ?, id
                FROM autores
                WHERE nome = ?
                AND NOT EXISTS (
                    SELECT 1 FROM livros WHERE titulo = ?
                )
            """, (titulo, ano, autor, titulo))

        conexao.commit()

    except sqlite3.Error:
        conexao.rollback()
        raise

    finally:
        conexao.close()


if __name__ == "__main__":
    criar_tabelas()
    inserir_dados_exemplo()
    print("Banco de dados pronto: tabelas criadas e dados de exemplo inseridos.")
