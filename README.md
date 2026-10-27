# Projeto Administrativo-Financeiro · N2 — Etapa 2

Aplicação em **Python + Streamlit + Gemini + PostgreSQL** que extrai dados de notas fiscais em PDF, consulta cadastros e grava contas a pagar/parcelas. Esta versão preserva o fluxo de extração de PDF e login da Etapa 1.

## O que foi implementado

- Leitura do PDF pela API Gemini, com resposta JSON estruturada.
- Conferência e correção manual de fornecedor, faturado, nota fiscal, classes, valores e vencimentos.
- Consulta ao banco para mostrar `EXISTE — ID`, `NÃO EXISTE` ou `INATIVO — ID`.
- Cadastro automático e **reativação** de pessoas e classificações quando confirmado.
- Lançamento de contas a pagar em `movimentocontas` com suas parcelas em `parcelacontas`.
- Classificações múltiplas por movimento por meio da tabela auxiliar `movimentocontas_classificacao`.
- Registro **transacional** (se alguma gravação falhar, nenhuma das alterações é confirmada).
- Bloqueio de nota repetida por CNPJ do fornecedor + número da nota + data de emissão.
- Identificador exclusivo de parcela, por exemplo `MOV0000000001-P001`.
- Área de consulta de cadastros ativos/inativos, inativação e reativação (sem exclusão física), além de últimos movimentos.
- Versão e commit exibidos na tela principal e no rodapé.

## Pré-requisitos

- Python 3.11 ou superior
- Chave ativa da Gemini API
- Um PostgreSQL acessível de onde o Streamlit estiver hospedado
- Credenciais de login para o projeto

## Configurar o PostgreSQL

Pode ser utilizado PostgreSQL em Neon, Supabase ou servidor próprio, desde que tenha acesso pela rede do Streamlit. Crie um banco vazio e obtenha a URL de conexão do PostgreSQL. **Não use a URL de uma API REST do provedor**.

Exemplo da estrutura (substitua todos os campos):

```env
DATABASE_URL=postgresql://usuario:senha@host:5432/nome_do_banco?sslmode=require
```

> Se a senha contiver símbolos como `@`, `/`, `#` ou `:`, use a URL gerada pelo provedor ou codifique os caracteres especiais no componente da senha.

O programa cria automaticamente, **sem apagar registros existentes**, as tabelas e índices definidos em `sql/001_schema.sql`, na primeira operação com o banco configurado. Opcionalmente você pode executar esse arquivo no editor SQL do provedor para preparar as tabelas antecipadamente.

As tabelas são `pessoas`, `classificacao`, `movimentocontas`, `parcelacontas` e `movimentocontas_classificacao`.

## Rodar localmente no Windows

1. Descompacte este projeto.
2. Abra o PowerShell na pasta `projeto-financeiro-streamlit`.
3. Execute:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

4. Abra o arquivo `.env` e preencha `APP_USERNAME`, `APP_PASSWORD`, `GEMINI_API_KEY` e **`DATABASE_URL`**. Ajuste `GEMINI_MODEL` se necessário.
5. Inicie:

```powershell
python -m streamlit run app.py
```

6. Abra a URL exibida no terminal (normalmente `http://localhost:8501`).

**Nunca publique `.env`, uma chave da Gemini ou a URL real do PostgreSQL.**

## Hospedar no Streamlit Community Cloud

1. Envie **o código** para um repositório GitHub e escolha a branch correta na configuração do Streamlit.
2. Nas configurações do app no Streamlit Community Cloud, abra **Secrets** e configure (somente no painel de Secrets):

```toml
GEMINI_API_KEY = "sua-chave"
GEMINI_MODEL = "seu-modelo-funcional"
APP_USERNAME = "usuario-do-professor"
APP_PASSWORD = "senha-definida"
APP_VERSION = "2.0.0"
DATABASE_URL = "postgresql://usuario:senha@host:5432/banco?sslmode=require"
GIT_COMMIT = "hash-do-ultimo-commit"
```

3. Reinicie/reimplante o aplicativo e abra-o para verificar a conexão com o banco.
4. **Verifique a branch de deploy:** a entrega antiga utilizava `entrega-final`, e atualizar apenas `main` não atualiza automaticamente um deploy configurado para outra branch.
5. Faça o commit final e atualize `GIT_COMMIT` no Secrets com o hash **real** desse commit se o ambiente hospedado não disponibilizar o diretório `.git`. O programa tenta ler o commit real de `.git` primeiro.

## Teste do fluxo completo

1. Entre com login e senha.
2. Escolha/valide um modelo da Gemini e envie um PDF de nota fiscal.
3. Verifique os dados extraídos na tela; eles continuarão visíveis após as interações.
4. Na seção **Etapa 2**, revise os documentos, a data e a soma das parcelas.
5. Clique **1 · Consultar cadastros**: o sistema mostra o que já existe e o que será criado/reativado.
6. Clique **2 · Confirmar lançamento**: confirme o ID do movimento salvo.
7. Abra **Cadastros e movimentos registrados** e pesquise os registros.
8. Consulte novamente a mesma nota: ela deve ser detectada como **já lançada**, sem criar duplicidade.
9. Teste a alteração de status de pessoa/classificação e sua reativação.

### Regras e cuidados

- O sistema exige CNPJ com 14 dígitos para o fornecedor, CPF/CNPJ para faturado, número/data de emissão, classificação, valor positivo e parcelas com vencimento.
- As parcelas precisam somar **exatamente** o total informado antes do lançamento.
- Não são inventadas datas de vencimento quando a nota não as informa; complete manualmente.
- Os documentos são conferidos pela **quantidade de dígitos**; esta versão não faz validação matemática de dígitos verificadores CPF/CNPJ.
- `inativar` altera o status, não remove registros. Cadastro inativo encontrado no lançamento é reativado após a confirmação.
- Não foi criada rotina automática de conciliação bancária ou contas a receber: a Etapa 2 do PDF descreve o fluxo de `APAGAR`.

## Verificações automatizadas

```powershell
python -m unittest discover -s tests -v
python -m compileall -q .
```

Os testes automatizados cobrem validação dos dados **sem exigir banco/serviço Gemini**. O teste integrado de leitura de PDF e gravação real exige as credenciais e um banco PostgreSQL acessível.

## Entrega no Classroom

O professor pediu um arquivo `Readme.txt` contendo a URL hospedada, login, senha, chave LLM e o código do último commit do GitHub, que precisa aparecer na tela principal. Copie `Readme.MODELO.txt` para `Readme.txt`, preencha os dados reais e entregue o arquivo **privadamente no Classroom**. O nome `Readme.txt` está no `.gitignore` para não ser enviado ao GitHub sem querer. Se possível, utilize uma API Key exclusiva, com cota limitada, e revogue-a após a avaliação.

## Integrantes

- Danilo Couto Naves
- Fabiano Borges da Cunha Sobrinho
