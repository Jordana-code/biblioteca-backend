# API Biblioteca — Exercício Prático 3

API em **Flask + SQLite** com rotas organizadas em **Blueprints** (Aula 7), **tratamento de erros e respostas HTTP padronizadas** (Aula 8) e **autenticação e autorização com JWT** (Aula 9).

## Estrutura

```
biblioteca_api/
├── app.py           → cria a API, configura o JWT, registra os 3 Blueprints,
│                      error handlers (JSON) e o after_request (X-API-Versao)
├── database.py      → conectar_banco() centralizada, criação das tabelas e dados de exemplo
├── biblioteca.db    → banco SQLite já criado, com 3 autores e 3 livros de exemplo
├── requirements.txt
├── Biblioteca_API.postman_collection.json → roteiro de testes pronto para o Postman
└── routes/
    ├── __init__.py
    ├── autores.py   → CRUD de autores
    ├── livros.py    → CRUD de livros
    └── auth.py      → /cadastro, /login e /meu-acesso
```

## Como executar

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

pip install -r requirements.txt
python app.py
```

A API sobe em `http://127.0.0.1:5000`.

- Para recriar o banco do zero: apague o `biblioteca.db` e rode `python database.py`.
- Use o `biblioteca.db` desta pasta. O banco antigo do repositório usa a coluna `autorid` e não tem e-mail único, por isso não é compatível com este código.

### Chave do JWT

A chave escrita no código serve **somente para rodar o exercício localmente**. Em produção, defina a variável de ambiente `JWT_SECRET_KEY` (o `app.py` dá preferência a ela):

```bash
set JWT_SECRET_KEY=uma-chave-longa-e-aleatoria        # Windows (cmd)
$env:JWT_SECRET_KEY="uma-chave-longa-e-aleatoria"     # Windows (PowerShell)
export JWT_SECRET_KEY="uma-chave-longa-e-aleatoria"   # Linux/macOS
```

O token vale por 1 hora.

## Rotas

| Método | Rota | Acesso | Sucesso | Erros tratados |
|---|---|---|---|---|
| POST | /cadastro | Público | 201 | 400 campos ausentes/inválidos · 409 e-mail já cadastrado |
| POST | /login | Público | 200 + token | 400 campos ausentes · 401 e-mail ou senha inválidos |
| GET | /meu-acesso | Autenticado | 200 | 401 token ausente, inválido ou expirado |
| GET | /livros | Público | 200 | — |
| GET | /livros/&lt;id&gt; | Público | 200 | 404 livro não encontrado |
| POST | /livros | Autenticado | 201 | 400 título vazio/autor_id inválido · 401 · 404 autor inexistente |
| PUT | /livros/&lt;id&gt; | Autenticado | 200 | 400 · 401 · 404 livro ou autor inexistente |
| DELETE | /livros/&lt;id&gt; | Autenticado | 200 | 401 · 404 |
| GET | /autores | Público | 200 | — |
| GET | /autores/&lt;id&gt; | Público | 200 | 404 |
| POST | /autores | Autenticado | 201 | 400 · 401 |
| PUT | /autores/&lt;id&gt; | Autenticado | 200 | 400 · 401 · 404 |
| DELETE | /autores/&lt;id&gt; | Autenticado | 200 | 401 · 404 · 409 autor com livros vinculados |

As rotas de escrita de autores também foram protegidas, seguindo o objetivo de proteger as operações de escrita.

Nas rotas autenticadas, envie o cabeçalho `Authorization: Bearer <token>`.

## Padrão das respostas

Sucesso:

```json
{ "mensagem": "Livro cadastrado com sucesso", "livro": { "id": 4, "titulo": "...", "ano": 2024, "autor_id": 1, "autor": "Machado de Assis" } }
```

Erro (mesmo formato para todos os erros, inclusive rota inexistente, método não permitido, erros do JWT e erro interno):

```json
{ "erro": true, "mensagem": "Livro não encontrado", "status": 404 }
```

Todas as respostas trazem o cabeçalho `X-API-Versao: 1.0`.

## Exemplos de corpo (JSON)

```json
POST /cadastro   { "nome": "Aluno Teste", "email": "aluno@teste.com", "senha": "Senha@123" }
                 (opcional: "perfil": "admin" — o padrão é "usuario")

POST /login      { "email": "aluno@teste.com", "senha": "Senha@123" }

POST /livros     { "titulo": "Livro de Teste", "ano": 2024, "autor_id": 1 }
                 ("ano" é opcional; "titulo" e "autor_id" são obrigatórios)

POST /autores    { "nome": "Jorge Amado", "nacionalidade": "Brasileira" }
```

## Como testar

**Postman:** Import → selecione `Biblioteca_API.postman_collection.json` → com a API rodando, abra a pasta *Roteiro do exercício* e clique em **Run**. O token do login e o id do livro criado são guardados automaticamente, e cada requisição já confere o status esperado e o cabeçalho `X-API-Versao`.

**Thunder Client:** importe o mesmo arquivo pela aba *Collections* (opção *Import*). Os scripts automáticos do Postman não rodam no Thunder Client: depois do login (teste 3), copie o `access_token` para a aba **Auth → Bearer** das requisições protegidas e, no teste 10, troque `{{livro_id}}` pelo id retornado no teste 8.

## Roteiro de testes — resultados obtidos

| Nº | Requisição | Resultado esperado | Obtido |
|---|---|---|---|
| 1 | POST /cadastro com dados válidos | 201 Created | **201 Created** — usuário criado; a resposta não traz a senha |
| 2 | POST /cadastro repetindo e-mail | 409 Conflict | **409 Conflict** — "E-mail já cadastrado" |
| 3 | POST /login com senha correta | 200 OK e token | **200 OK** — retornou o `access_token` (JWT) |
| 4 | POST /login com senha incorreta | 401 Unauthorized | **401 Unauthorized** — "E-mail ou senha inválidos" |
| 5 | GET /meu-acesso sem token | Acesso recusado | **401 Unauthorized** — "Acesso recusado: token não informado" |
| 6 | GET /meu-acesso com token válido | 200 OK | **200 OK** — id, nome, e-mail e perfil do usuário |
| 7 | POST /livros sem token | Acesso recusado | **401 Unauthorized** — "Acesso recusado: token não informado" |
| 8 | POST /livros com token e dados válidos | 201 Created | **201 Created** — livro criado |
| 9 | GET /livros/999 para ID inexistente | 404 Not Found | **404 Not Found** — "Livro não encontrado" |
| 10 | DELETE /livros/&lt;id&gt; com token | 204 ou 200 | **200 OK** — "Livro excluído com sucesso" |

Também foram verificados: token expirado, adulterado ou assinado com outra chave (401), título vazio (400), `autor_id` inexistente (404), e-mail repetido com letras maiúsculas (409), exclusão de autor com livros (409), rota inexistente (404), método não permitido (405), falha de banco com rollback (500 genérico, sem detalhes internos) e cabeçalho `X-API-Versao` em todas as respostas.

## Onde cada requisito foi atendido

| Requisito | Onde |
|---|---|
| Blueprints de autores, livros e auth registrados no app | `routes/*.py` e `app.register_blueprint(...)` no `app.py` |
| `conectar_banco()` centralizada | `database.py` |
| Tabela `usuarios` (email único, perfil padrão `usuario`, aceita `admin`) | `criar_tabelas()` no `database.py` |
| Senha com hash | `generate_password_hash()` / `check_password_hash()` em `routes/auth.py` |
| Token JWT e rotas protegidas | `create_access_token()` no `/login` e `@jwt_required()` nas rotas de escrita |
| 201 / 200 / 400 / 404 / 409 | retornos e `abort(...)` em cada rota |
| try/except/finally com rollback e fechamento da conexão | todas as operações com o banco nos três Blueprints |
| Error handler com resposta JSON padronizada | `tratar_erro_http` e `tratar_erro_inesperado` no `app.py` |
| Token ausente, inválido ou expirado | `unauthorized_loader`, `invalid_token_loader` e `expired_token_loader` no `app.py` |
| Cabeçalho `X-API-Versao: 1.0` | `@app.after_request` no `app.py` |
| SQL parametrizado com `?` | todas as consultas |
| Sem expor detalhes internos | erros de banco e exceções vão só para o log do servidor; o cliente recebe mensagem genérica |
| Chave JWT por variável de ambiente em produção | `os.environ.get("JWT_SECRET_KEY", ...)` no `app.py` |
