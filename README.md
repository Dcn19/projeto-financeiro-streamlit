# Projeto Administrativo-Financeiro — Etapa 1

Aplicação Web desenvolvida em **Python + Streamlit** para processar uma nota
fiscal em PDF com o **Gemini** e devolver os dados extraídos em formato
estruturado e JSON.

## Recursos da versão atual

- Login único, sem banco de dados.
- Usuário e senha armazenados fora do código-fonte.
- Chave padrão do Gemini armazenada fora do código-fonte.
- Possibilidade de informar uma API Key temporária pela barra lateral.
- ID do modelo Gemini configurável pela barra lateral durante a sessão.
- A chave temporária e o ID do modelo podem ser trocados sem alterar o código entregue.
- Identificação da versão da aplicação.
- Exibição do commit Git usado pela aplicação, quando o ambiente disponibiliza o repositório.
- Compatibilidade com execução local e Streamlit Community Cloud.
- Dependências fixadas em versões específicas para facilitar a reprodução da entrega.

## O que a aplicação faz

1. O usuário acessa a aplicação com a credencial configurada.
2. Seleciona uma nota fiscal em PDF.
3. Clica em **EXTRAIR DADOS**.
4. O PDF é enviado ao Gemini para leitura e interpretação.
5. O sistema extrai:
   - Fornecedor:
     - Razão social
     - Nome fantasia
     - CNPJ
   - Faturado:
     - Nome completo
     - CPF
   - Número da nota fiscal
   - Data de emissão
   - Descrição dos produtos
   - Quantidade de parcelas
   - Parcelas e vencimentos
   - Valor total
   - Classificação da despesa
6. O resultado aparece em duas abas:
   - Visualização formatada
   - JSON

## Requisitos

- Python 3.11 ou superior
- Chave da Gemini API

## 1. Criar o ambiente virtual

No terminal, dentro da pasta do projeto:

```powershell
python -m venv .venv
```

Ative o ambiente no PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

No Prompt de Comando (CMD):

```cmd
.venv\Scripts\activate.bat
```

## 2. Instalar as dependências

```powershell
python -m pip install -r requirements.txt
```

## 3. Configurar o ambiente local

Copie `.env.example` para `.env`:

```powershell
Copy-Item .env.example .env
```

Edite o `.env` e configure:

```env
GEMINI_API_KEY=SUA_CHAVE_REAL
GEMINI_MODEL=gemini-3.8-flash
APP_USERNAME=SEU_USUARIO
APP_PASSWORD=SUA_SENHA
APP_VERSION=1.0.0
GIT_COMMIT=
```

O `.env` real não deve ser publicado no GitHub.

## 4. Executar

```powershell
python -m streamlit run app.py
```

Normalmente o endereço local será:

```text
http://localhost:8501
```

## Alteração da API Key e do ID do Gemini

Depois do login, abra a barra lateral da aplicação.

Na seção **Configuração do Gemini** existem dois campos:

- **API Key do Gemini (opcional):** se ficar vazio, a aplicação usa a chave
  padrão configurada no `.env` ou nos Secrets do Streamlit. Se o professor
  informar uma chave, ela passa a ser usada temporariamente somente naquela
  sessão.
- **ID do modelo Gemini:** permite trocar o modelo em uso sem editar o código.

Após preencher os campos desejados, clique em **Aplicar configuração**.

A chave temporária fica apenas no estado da sessão do Streamlit; ela não é
gravada no código-fonte, no GitHub, no `.env` ou em banco de dados. Ao clicar
em **Sair**, a chave temporária é removida da sessão.

Quando uma chave temporária estiver ativa, o botão **Voltar para a chave do
projeto** restaura imediatamente a chave padrão configurada na hospedagem ou no
ambiente local.

O modelo padrão continua sendo definido por `GEMINI_MODEL` no `.env` ou nos
Secrets da hospedagem.

## Login

O projeto utiliza somente uma credencial. Não existe banco de dados de
usuários.

As variáveis utilizadas são:

```text
APP_USERNAME
APP_PASSWORD
```

A autenticação é mantida na sessão do Streamlit. O botão **Sair** encerra a
sessão atual.

## Versionamento Git

O rodapé e a barra lateral mostram:

- versão da aplicação (`APP_VERSION`);
- commit Git da execução.

A aplicação tenta executar automaticamente:

```text
git rev-parse --short=8 HEAD
```

Se o ambiente de hospedagem não disponibilizar os metadados Git, pode ser
configurado o fallback `GIT_COMMIT` nos Secrets.

Na entrega final, a recomendação é:

1. finalizar o projeto;
2. gerar o commit de entrega;
3. criar uma tag, por exemplo `v1.0.0`;
4. manter uma branch específica, por exemplo `entrega-final`;
5. hospedar essa branch no Streamlit Community Cloud.

## Streamlit Community Cloud

O projeto já está preparado para receber as mesmas configurações pelo sistema
de Secrets do Streamlit.

Existe um exemplo em:

```text
.streamlit/secrets.toml.example
```

No painel do Streamlit Community Cloud, copie as configurações para a área de
Secrets e substitua os valores de exemplo pelos valores reais.

Nunca publique um arquivo `.streamlit/secrets.toml` contendo chaves ou senhas.

## Estrutura do projeto

```text
projeto_financeiro_streamlit/
├── .streamlit/
│   └── secrets.toml.example
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── README_ENTREGA.txt
└── COMO_EXECUTAR_PROJETO.txt
```

## Segurança

Não devem ser publicados no GitHub:

- `.env`;
- `.streamlit/secrets.toml`;
- chaves reais da Gemini API;
- senhas reais da aplicação;
- `.venv`;
- `__pycache__`;
- `README_ENTREGA.txt` quando ele contiver as credenciais do professor.
