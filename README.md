# Projeto Administrativo-Financeiro — Etapa 1

Aplicação Web desenvolvida em **Python + Streamlit** para processar uma nota
fiscal em PDF com o **Gemini** e devolver os dados extraídos em formato
estruturado e JSON.

## Recursos da versão 1.1.0

- Login único, sem banco de dados.
- Usuário e senha armazenados fora do código-fonte.
- Chave padrão do Gemini armazenada fora do código-fonte.
- Possibilidade de informar uma API Key temporária pela barra lateral.
- Validação da API Key por meio da consulta de modelos disponíveis.
- Carregamento automático dos modelos depois que a chave é validada.
- Seletor de modelo liberado somente depois do carregamento dos modelos.
- Filtro para modelos Gemini gerais que suportam `generateContent`.
- Opção avançada para informar um ID manual depois da validação da chave.
- Teste opcional do modelo selecionado usando a Interactions API.
- Tratamento amigável para erros comuns como 403, 404, 429 e 503.
- Leitura do PDF mantida pela **Interactions API**, com saída estruturada em JSON.
- Identificação da versão da aplicação e do commit Git.
- Compatibilidade com execução local e Streamlit Community Cloud.
- Dependências fixadas em versões específicas para facilitar a reprodução.

## Fluxo de configuração do Gemini

A aplicação usa a chave padrão configurada no `.env` ou nos Secrets da
hospedagem. Quando a aplicação é aberta, ela tenta consultar os modelos dessa
chave e carregar a lista automaticamente.

Também é possível informar outra API Key na barra lateral:

1. Cole a API Key no campo correspondente.
2. Pressione **Enter** ou clique fora do campo.
3. A aplicação consulta `client.models.list()` usando essa chave.
4. A chave só passa a ser usada se a consulta for aceita.
5. O seletor de modelos é liberado depois que a lista é carregada.
6. O usuário escolhe um modelo disponível.
7. Opcionalmente, pode clicar em **Testar modelo selecionado** antes de enviar o PDF.

A chave temporária é mantida apenas no estado da sessão do Streamlit. Ela não é
gravada no código-fonte, GitHub, `.env` ou banco de dados.

## Sobre a lista de modelos

O endpoint de modelos informa quais IDs estão visíveis para a chave e quais
ações cada modelo suporta. A aplicação filtra a resposta para modelos Gemini
gerais que suportam `generateContent` e remove famílias claramente voltadas a
imagem, TTS, áudio, live, embeddings e outras modalidades específicas.

A listagem não garante que o modelo esteja respondendo naquele exato momento.
Por isso existe o botão **Testar modelo selecionado**. Esse teste usa a
Interactions API e pode consumir uma requisição da cota do modelo.

## Leitura do PDF

A lógica principal de leitura da nota fiscal foi preservada. O PDF continua
sendo enviado como documento para:

```python
client.interactions.create(...)
```

O retorno continua sendo solicitado como JSON estruturado com o schema Pydantic
de `NotaFiscalExtraida`.

## O que a aplicação extrai

- Fornecedor:
  - Razão social
  - Nome fantasia
  - CNPJ
- Faturado:
  - Nome completo
  - CPF
- Número da nota fiscal
- Data de emissão
- Descrição dos produtos/serviços
- Quantidade de parcelas
- Parcelas e vencimentos
- Valor total
- Classificação da despesa

O resultado aparece em duas abas:

- Visualização formatada
- JSON

## Tratamento de erros do Gemini

A aplicação apresenta mensagens específicas para os principais erros:

- **403:** projeto sem permissão para utilizar a API.
- **404:** modelo não encontrado ou indisponível para a chave/API.
- **429:** limite de uso ou cota atingida.
- **503:** modelo temporariamente sobrecarregado.

Os detalhes técnicos continuam disponíveis em uma área expansível.

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
GEMINI_MODEL=gemini-3.6-flash
APP_USERNAME=SEU_USUARIO
APP_PASSWORD=SUA_SENHA
APP_VERSION=1.1.0
GIT_COMMIT=
```

`GEMINI_MODEL` funciona como modelo preferencial. Se esse modelo estiver na
lista retornada para a chave, ele será selecionado inicialmente. Caso não
esteja, a aplicação escolhe outro modelo disponível.

O `.env` real não deve ser publicado no GitHub.

## 4. Executar

```powershell
python -m streamlit run app.py
```

Normalmente o endereço local será:

```text
http://localhost:8501
```

## Chave padrão e chave temporária

- **Chave do projeto:** vem do `.env` ou dos Secrets do Streamlit.
- **Chave temporária:** é informada pelo usuário na barra lateral e usada
  somente durante a sessão.

Quando uma chave temporária estiver ativa, o botão **Chave do projeto** remove
a chave temporária e recarrega os modelos da chave padrão.

## Seleção de modelo

O campo de modelo fica bloqueado enquanto nenhuma lista válida de modelos foi
carregada.

Depois da validação da chave, o usuário pode:

- selecionar um modelo retornado pela API;
- recarregar a lista de modelos;
- testar o modelo selecionado;
- habilitar a opção avançada e informar manualmente um ID.

## Login

O projeto utiliza somente uma credencial. Não existe banco de dados de
usuários.

As variáveis utilizadas são:

```text
APP_USERNAME
APP_PASSWORD
```

A autenticação é mantida na sessão do Streamlit. O botão **Sair** encerra a
sessão atual e remove a chave temporária e as configurações de modelos.

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

Para uma nova entrega da versão 1.1.0, recomenda-se criar um novo commit e uma
nova tag, preservando a versão 1.0.0 já entregue anteriormente.

## Streamlit Community Cloud

O projeto está preparado para receber as configurações pelo sistema de Secrets
do Streamlit.

Existe um exemplo em:

```text
.streamlit/secrets.toml.example
```

No painel do Streamlit Community Cloud, copie as configurações para a área de
Secrets e substitua os valores de exemplo pelos valores reais.

Nunca publique um arquivo `.streamlit/secrets.toml` contendo chaves ou senhas.

## Estrutura do projeto

```text
projeto-financeiro-streamlit/
├── .streamlit/
│   └── secrets.toml.example
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── README_ENTREGA.txt
```

## Segurança

Não devem ser publicados no GitHub:

- `.env`;
- `.streamlit/secrets.toml`;
- chaves reais da Gemini API;
- senhas reais da aplicação;
- `.venv`;
- `__pycache__`;
- `README_ENTREGA.txt` quando ele contiver credenciais do professor.
