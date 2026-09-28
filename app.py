import base64
import hashlib
import hmac
import html
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Literal, Optional

import streamlit as st
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field


# ============================================================
# CONFIGURAÇÃO DA APLICAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

st.set_page_config(
    page_title="Extração de Dados de Nota Fiscal",
    page_icon="📄",
    layout="centered",
)


def obter_configuracao(nome: str, padrao: Optional[str] = None) -> Optional[str]:
    """Lê uma configuração do Streamlit Secrets e, em seguida, do .env."""
    try:
        if nome in st.secrets:
            valor = st.secrets[nome]
            if valor is not None and str(valor).strip():
                return str(valor).strip()
    except Exception:
        # Localmente pode não existir um arquivo de secrets.
        pass

    valor_ambiente = os.getenv(nome)

    if valor_ambiente is not None and valor_ambiente.strip():
        return valor_ambiente.strip()

    return padrao


GEMINI_API_KEY_PROJETO = obter_configuracao("GEMINI_API_KEY")
GEMINI_MODEL_PADRAO = obter_configuracao(
    "GEMINI_MODEL",
    "gemini-3.6-flash",
)

APP_USERNAME = obter_configuracao("APP_USERNAME")
APP_PASSWORD = obter_configuracao("APP_PASSWORD")
APP_VERSION = obter_configuracao("APP_VERSION", "1.1.0")
GIT_COMMIT_CONFIGURADO = obter_configuracao("GIT_COMMIT")


# ============================================================
# ESTILO VISUAL
# ============================================================

st.markdown(
    """
<style>
.block-container {
    max-width: 980px;
    padding-top: 2.2rem;
    padding-bottom: 2.5rem;
}

.project-badge {
    display: inline-block;
    padding: 0.35rem 0.75rem;
    border-radius: 999px;
    background: rgba(49, 51, 63, 0.08);
    font-size: 0.82rem;
    font-weight: 600;
    margin-bottom: 0.8rem;
}

.hero-title {
    text-align: center;
    font-size: 2.35rem;
    font-weight: 800;
    line-height: 1.15;
    margin-bottom: 0.55rem;
}

.hero-subtitle {
    text-align: center;
    font-size: 1rem;
    opacity: 0.75;
    margin-bottom: 1.6rem;
}

.section-title {
    font-size: 1.05rem;
    font-weight: 700;
    margin-bottom: 0.35rem;
}

.section-description {
    font-size: 0.92rem;
    opacity: 0.72;
    margin-bottom: 0.6rem;
}

.login-note {
    text-align: center;
    font-size: 0.86rem;
    opacity: 0.68;
    margin-top: 0.8rem;
}

.stButton > button {
    min-height: 3rem;
    font-weight: 700;
    border-radius: 0.55rem;
}

.stDownloadButton > button {
    min-height: 2.7rem;
    border-radius: 0.55rem;
    font-weight: 600;
}

div[data-testid="stFileUploader"] {
    border-radius: 0.7rem;
}

div[data-testid="stMetric"] {
    border: 1px solid rgba(128, 128, 128, 0.20);
    border-radius: 0.65rem;
    padding: 0.75rem 0.9rem;
}

.result-caption {
    font-size: 0.88rem;
    opacity: 0.68;
    margin-top: -0.25rem;
    margin-bottom: 0.7rem;
}

.small-note {
    font-size: 0.84rem;
    opacity: 0.68;
}

.version-footer {
    text-align: center;
    color: #8b8f98;
    font-size: 0.78rem;
    margin-top: 0.25rem;
}
</style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# AUTENTICAÇÃO
# ============================================================


def credenciais_configuradas() -> bool:
    return bool(APP_USERNAME and APP_PASSWORD)


def mostrar_tela_login() -> None:
    st.markdown(
        """
<div style="text-align:center;">
    <span class="project-badge">
        Projeto Administrativo-Financeiro · Etapa 1
    </span>
</div>

<div class="hero-title">
    Acesso ao Sistema
</div>

<div class="hero-subtitle">
    Informe o usuário e a senha para acessar a aplicação.
</div>
        """,
        unsafe_allow_html=True,
    )

    if not credenciais_configuradas():
        st.error(
            "As credenciais de acesso ainda não foram configuradas. "
            "Defina APP_USERNAME e APP_PASSWORD no arquivo .env "
            "ou nos Secrets da hospedagem."
        )
        st.stop()

    with st.form("form_login", clear_on_submit=False):
        usuario = st.text_input(
            "Usuário",
            placeholder="Digite o usuário",
            autocomplete="username",
        )

        senha = st.text_input(
            "Senha",
            type="password",
            placeholder="Digite a senha",
            autocomplete="current-password",
        )

        entrar = st.form_submit_button(
            "ENTRAR",
            type="primary",
            use_container_width=True,
        )

    if entrar:
        usuario_ok = hmac.compare_digest(
            usuario.strip(),
            APP_USERNAME,
        )

        senha_ok = hmac.compare_digest(
            senha,
            APP_PASSWORD,
        )

        if usuario_ok and senha_ok:
            st.session_state["autenticado"] = True
            st.session_state["usuario_logado"] = APP_USERNAME
            st.rerun()

        st.error("Usuário ou senha inválidos.")

    st.markdown(
        '<div class="login-note">'
        "A autenticação utiliza uma única credencial configurada "
        "fora do código-fonte."
        "</div>",
        unsafe_allow_html=True,
    )


def exigir_autenticacao() -> None:
    if not st.session_state.get("autenticado", False):
        mostrar_tela_login()
        st.stop()


def limpar_estado_gemini() -> None:
    chaves = [
        "gemini_model",
        "gemini_model_manual",
        "gemini_modo_manual",
        "gemini_modelos",
        "gemini_modelos_fingerprint",
        "gemini_origem_modelos",
        "gemini_feedback_modelos",
        "gemini_status_teste",
        "gemini_tentativa_projeto_realizada",
        "gemini_carregamento_pendente",
    ]

    for chave in chaves:
        st.session_state.pop(chave, None)


def encerrar_sessao() -> None:
    limpar_estado_gemini()

    chaves_sessao = [
        "autenticado",
        "usuario_logado",
        "gemini_api_key_temporaria",
        "gemini_api_key_input",
    ]

    for chave in chaves_sessao:
        st.session_state.pop(chave, None)

    st.rerun()


# ============================================================
# VERSIONAMENTO
# ============================================================


def obter_commit_git() -> str:
    """Obtém o commit real do repositório; usa configuração como fallback."""
    try:
        processo = subprocess.run(
            ["git", "rev-parse", "--short=8", "HEAD"],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        )

        commit = processo.stdout.strip()

        if commit:
            return commit
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass

    if GIT_COMMIT_CONFIGURADO:
        return GIT_COMMIT_CONFIGURADO

    return "não publicado"


# ============================================================
# MODELOS DA RESPOSTA
# ============================================================

CategoriaDespesa = Literal[
    "INSUMOS AGRÍCOLAS",
    "MANUTENÇÃO E OPERAÇÃO",
    "RECURSOS HUMANOS",
    "SERVIÇOS OPERACIONAIS",
    "INFRAESTRUTURA E UTILIDADES",
    "ADMINISTRATIVAS",
    "SEGUROS E PROTEÇÃO",
    "IMPOSTOS E TAXAS",
    "INVESTIMENTOS",
]


class Fornecedor(BaseModel):
    razao_social: Optional[str] = Field(
        default=None,
        description="Razão social do fornecedor/emissor da nota fiscal.",
    )

    nome_fantasia: Optional[str] = Field(
        default=None,
        description=(
            "Nome fantasia do fornecedor. "
            "Retorne null quando não estiver explicitamente informado."
        ),
    )

    cnpj: Optional[str] = Field(
        default=None,
        description="CNPJ do fornecedor/emissor da nota fiscal.",
    )


class Faturado(BaseModel):
    nome_completo: Optional[str] = Field(
        default=None,
        description="Nome completo do faturado/destinatário da nota fiscal.",
    )

    cpf: Optional[str] = Field(
        default=None,
        description=(
            "CPF do faturado/destinatário. "
            "Retorne null quando não estiver explicitamente informado."
        ),
    )


class Parcela(BaseModel):
    numero: Optional[int] = Field(
        default=None,
        description="Número sequencial da parcela, quando identificado.",
    )

    data_vencimento: Optional[str] = Field(
        default=None,
        description="Data de vencimento no formato DD/MM/AAAA.",
    )

    valor: Optional[float] = Field(
        default=None,
        description="Valor da parcela em reais, como número decimal.",
    )


class NotaFiscalExtraida(BaseModel):
    fornecedor: Fornecedor
    faturado: Faturado

    numero_nota_fiscal: Optional[str] = Field(
        default=None,
        description="Número da nota fiscal.",
    )

    data_emissao: Optional[str] = Field(
        default=None,
        description="Data de emissão no formato DD/MM/AAAA.",
    )

    descricao_produtos: list[str] = Field(
        default_factory=list,
        description=(
            "Lista contendo somente as descrições dos produtos ou serviços "
            "identificados na nota fiscal."
        ),
    )

    quantidade_parcelas: int = Field(
        default=0,
        ge=0,
        description="Quantidade de parcelas identificadas na nota fiscal.",
    )

    parcelas: list[Parcela] = Field(
        default_factory=list,
        description="Lista de parcelas identificadas na nota fiscal.",
    )

    valor_total: Optional[float] = Field(
        default=None,
        description=(
            "Valor total da nota fiscal em reais. "
            "Priorize o campo VALOR TOTAL DA NOTA quando existir."
        ),
    )

    classificacao_despesa: list[CategoriaDespesa] = Field(
        default_factory=list,
        description=(
            "Uma ou mais categorias de despesa inferidas a partir "
            "dos produtos ou serviços da nota."
        ),
    )


# ============================================================
# PROMPT DA EXTRAÇÃO
# ============================================================

CATEGORIAS_DESPESA = """
CATEGORIAS PERMITIDAS:

1. INSUMOS AGRÍCOLAS
   - Sementes
   - Fertilizantes
   - Defensivos agrícolas
   - Corretivos

2. MANUTENÇÃO E OPERAÇÃO
   - Combustíveis e lubrificantes
   - Peças, parafusos e componentes mecânicos
   - Manutenção de máquinas e equipamentos
   - Pneus, filtros e correias
   - Ferramentas e utensílios

3. RECURSOS HUMANOS
   - Mão de obra temporária
   - Salários e encargos

4. SERVIÇOS OPERACIONAIS
   - Frete e transporte
   - Colheita terceirizada
   - Secagem e armazenagem
   - Pulverização e aplicação

5. INFRAESTRUTURA E UTILIDADES
   - Energia elétrica
   - Arrendamento de terras
   - Construções e reformas
   - Materiais de construção

6. ADMINISTRATIVAS
   - Honorários contábeis, advocatícios e agronômicos
   - Despesas bancárias e financeiras

7. SEGUROS E PROTEÇÃO
   - Seguro agrícola
   - Seguro de ativos, máquinas ou veículos
   - Seguro prestamista

8. IMPOSTOS E TAXAS
   - ITR
   - IPTU
   - IPVA
   - INCRA-CCIR

9. INVESTIMENTOS
   - Aquisição de máquinas e implementos
   - Aquisição de veículos
   - Aquisição de imóveis
   - Infraestrutura rural
"""


PROMPT_EXTRACAO = f"""
Você é responsável por extrair dados de uma nota fiscal brasileira
para um sistema administrativo-financeiro.

Analise o PDF recebido e devolva SOMENTE os dados solicitados pelo
esquema estruturado.

REGRAS OBRIGATÓRIAS:

1. Não invente informações.

2. Quando um dado não estiver explicitamente presente ou não puder ser
   identificado com segurança, retorne null no campo correspondente.

3. O FORNECEDOR é a empresa emissora/vendedora da nota fiscal.
   Extraia:
   - razão social;
   - nome fantasia;
   - CNPJ.

4. O FATURADO é o destinatário da nota fiscal.
   Extraia:
   - nome completo;
   - CPF.

5. Extraia o número da nota fiscal e a data de emissão.

6. Em descricao_produtos, retorne somente as descrições dos produtos
   ou serviços. Não crie cadastro, código ou entidade de produto.

7. Identifique as parcelas na seção FATURA, DUPLICATAS ou equivalente.
   Mesmo que exista somente uma parcela, devolva o campo parcelas como lista.

8. quantidade_parcelas deve corresponder ao número de parcelas identificadas.

9. O valor_total deve corresponder ao VALOR TOTAL DA NOTA.
   Não confunda com valor total dos produtos, base de ICMS ou outro subtotal.

10. A classificação da despesa NÃO é um texto que deve ser simplesmente
    extraído da nota. Ela deve ser INTERPRETADA a partir dos produtos
    ou serviços adquiridos.

11. Use exclusivamente as categorias fornecidas abaixo.
    Nesta etapa normalmente haverá uma categoria por nota, mas
    classificacao_despesa deve continuar sendo uma lista para permitir
    múltiplas categorias futuramente.

12. Se os itens não permitirem uma classificação segura, retorne
    classificacao_despesa como lista vazia.

13. Retorne datas no formato DD/MM/AAAA.

14. Retorne valores monetários como números decimais, sem "R$" e sem
    separador de milhar.

{CATEGORIAS_DESPESA}
"""


# ============================================================
# GEMINI: CHAVE, MODELOS E DISPONIBILIDADE
# ============================================================


def obter_chave_gemini_ativa() -> Optional[str]:
    """Retorna a chave temporária da sessão ou, na ausência dela, a chave do projeto."""
    chave_temporaria = st.session_state.get("gemini_api_key_temporaria")

    if chave_temporaria and str(chave_temporaria).strip():
        return str(chave_temporaria).strip()

    return GEMINI_API_KEY_PROJETO


def usando_chave_temporaria() -> bool:
    chave_temporaria = st.session_state.get("gemini_api_key_temporaria")
    return bool(chave_temporaria and str(chave_temporaria).strip())


def fingerprint_chave(api_key: str) -> str:
    """Gera uma impressão digital curta sem expor a API Key."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:16]


def normalizar_id_modelo(nome: Optional[str]) -> str:
    if not nome:
        return ""

    nome_normalizado = str(nome).strip()

    if nome_normalizado.startswith("models/"):
        nome_normalizado = nome_normalizado.split("/", 1)[1]

    return nome_normalizado


def modelo_candidato_para_documentos(
    modelo_id: str,
    acoes_suportadas: set[str],
) -> bool:
    """
    Filtra modelos Gemini gerais que suportam geração de conteúdo.

    models.list() não informa diretamente se um modelo aceita PDF pela
    Interactions API. Por isso, removemos famílias claramente voltadas a
    imagem, áudio, TTS, live, embedding e outras modalidades específicas.
    O teste opcional do modelo confirma se o ID selecionado responde pela
    Interactions API antes de o usuário enviar um PDF.
    """
    if "generateContent" not in acoes_suportadas:
        return False

    if not modelo_id.startswith("gemini-"):
        return False

    termos_excluidos = (
        "image",
        "imagen",
        "tts",
        "live",
        "audio",
        "embedding",
        "embed",
        "robotics",
        "computer-use",
        "computer_use",
        "veo",
        "lyria",
    )

    return not any(termo in modelo_id.lower() for termo in termos_excluidos)


def prioridade_modelo(modelo_id: str) -> tuple[int, str]:
    preferidos = [
        GEMINI_MODEL_PADRAO or "",
        "gemini-3.6-flash",
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.5-pro",
    ]

    try:
        indice = preferidos.index(modelo_id)
    except ValueError:
        indice = len(preferidos)

    return indice, modelo_id


def listar_modelos_gemini(api_key: str) -> list[dict]:
    """Lista modelos disponíveis para a chave e filtra os candidatos ao projeto."""
    if not api_key or not api_key.strip():
        raise ValueError("Informe uma API Key do Gemini válida.")

    client = genai.Client(api_key=api_key.strip())
    modelos_encontrados: dict[str, dict] = {}

    for modelo in client.models.list():
        modelo_id = normalizar_id_modelo(getattr(modelo, "name", None))
        acoes = set(getattr(modelo, "supported_actions", None) or [])

        if not modelo_candidato_para_documentos(modelo_id, acoes):
            continue

        modelos_encontrados[modelo_id] = {
            "id": modelo_id,
            "nome": getattr(modelo, "display_name", None) or modelo_id,
            "descricao": getattr(modelo, "description", None) or "",
            "input_token_limit": getattr(modelo, "input_token_limit", None),
            "output_token_limit": getattr(modelo, "output_token_limit", None),
            "acoes": sorted(acoes),
        }

    modelos = sorted(
        modelos_encontrados.values(),
        key=lambda item: prioridade_modelo(item["id"]),
    )

    if not modelos:
        raise RuntimeError(
            "A chave foi consultada, mas nenhum modelo Gemini compatível com "
            "geração de conteúdo foi encontrado para esta aplicação."
        )

    return modelos


def escolher_modelo_inicial(modelos: list[dict]) -> str:
    ids = [modelo["id"] for modelo in modelos]
    modelo_atual = st.session_state.get("gemini_model")

    candidatos = [
        modelo_atual,
        GEMINI_MODEL_PADRAO,
        "gemini-3.6-flash",
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.5-pro",
    ]

    for candidato in candidatos:
        if candidato and candidato in ids:
            return candidato

    return ids[0]


def salvar_modelos_na_sessao(
    modelos: list[dict],
    api_key: str,
    origem: str,
) -> None:
    st.session_state["gemini_modelos"] = modelos
    st.session_state["gemini_modelos_fingerprint"] = fingerprint_chave(api_key)
    st.session_state["gemini_origem_modelos"] = origem
    st.session_state["gemini_model"] = escolher_modelo_inicial(modelos)
    st.session_state.pop("gemini_status_teste", None)
    st.session_state["gemini_modo_manual"] = False
    st.session_state["gemini_model_manual"] = st.session_state["gemini_model"]


def solicitar_validacao_chave_temporaria() -> None:
    """Marca a nova chave para validação após Enter ou perda de foco do campo."""
    chave = str(st.session_state.get("gemini_api_key_input", "")).strip()

    if chave:
        st.session_state["gemini_carregamento_pendente"] = "temporaria"
        st.session_state.pop("gemini_feedback_modelos", None)
        st.session_state.pop("gemini_status_teste", None)


def voltar_para_chave_projeto() -> None:
    """Remove a chave temporária e agenda o carregamento da chave do projeto."""
    st.session_state.pop("gemini_api_key_temporaria", None)
    st.session_state["gemini_api_key_input"] = ""
    st.session_state.pop("gemini_modelos", None)
    st.session_state.pop("gemini_modelos_fingerprint", None)
    st.session_state.pop("gemini_origem_modelos", None)
    st.session_state.pop("gemini_status_teste", None)
    st.session_state.pop("gemini_feedback_modelos", None)
    st.session_state["gemini_modo_manual"] = False
    st.session_state["gemini_tentativa_projeto_realizada"] = False

    if GEMINI_API_KEY_PROJETO:
        st.session_state["gemini_carregamento_pendente"] = "projeto"


def solicitar_recarregamento_modelos() -> None:
    """Agenda uma nova consulta de modelos para a chave atualmente ativa."""
    if usando_chave_temporaria():
        st.session_state["gemini_carregamento_pendente"] = "temporaria"
    elif GEMINI_API_KEY_PROJETO:
        st.session_state["gemini_carregamento_pendente"] = "projeto"

    st.session_state.pop("gemini_feedback_modelos", None)
    st.session_state.pop("gemini_status_teste", None)


def obter_codigo_erro_gemini(erro: Exception) -> Optional[int]:
    for atributo in ("code", "status_code"):
        valor = getattr(erro, atributo, None)

        try:
            if valor is not None:
                codigo = int(valor)
                if 100 <= codigo <= 599:
                    return codigo
        except (TypeError, ValueError):
            pass

    texto = str(erro)
    correspondencia = re.search(
        r"\b(400|401|403|404|408|409|429|500|502|503|504)\b",
        texto,
    )

    if correspondencia:
        return int(correspondencia.group(1))

    return None


def mensagem_amigavel_erro_gemini(
    erro: Exception,
    contexto: str = "uso",
) -> tuple[str, str]:
    codigo = obter_codigo_erro_gemini(erro)
    texto = str(erro).lower()

    if "api_key_invalid" in texto or "api key not valid" in texto:
        return (
            "API Key inválida",
            "A chave informada não foi aceita pelo Gemini. Confira a chave e tente novamente.",
        )

    if codigo in (400, 401) and "key" in texto:
        return (
            "Não foi possível validar a API Key",
            "Confira se a chave foi copiada corretamente e se pertence a um projeto com acesso à Gemini API.",
        )

    if codigo == 403:
        return (
            "Projeto sem permissão para usar o Gemini",
            "A API Key foi reconhecida, mas o projeto associado teve o acesso negado. "
            "Use outra chave/projeto ou verifique as permissões no Google AI Studio.",
        )

    if codigo == 404:
        return (
            "Modelo indisponível",
            "O modelo selecionado não foi encontrado ou não está disponível para esta chave/API.",
        )

    if codigo == 429:
        return (
            "Limite de uso atingido",
            "A cota ou o limite de requisições do modelo foi atingido. "
            "Aguarde a renovação da cota, escolha outro modelo ou use outra API Key.",
        )

    if codigo == 503:
        return (
            "Modelo temporariamente sobrecarregado",
            "O Gemini informou alta demanda. Aguarde alguns minutos ou escolha outro modelo para evitar novas tentativas desnecessárias.",
        )

    if codigo in (500, 502, 504):
        return (
            "Serviço do Gemini temporariamente indisponível",
            "O serviço apresentou uma falha temporária. Tente novamente mais tarde ou selecione outro modelo.",
        )

    if contexto == "listagem":
        return (
            "Não foi possível carregar os modelos",
            "A consulta de modelos falhou. Confira a API Key e tente novamente.",
        )

    if contexto == "teste":
        return (
            "Não foi possível testar o modelo",
            "O modelo não respondeu ao teste nesta sessão.",
        )

    return (
        "Não foi possível processar a nota fiscal",
        "O Gemini retornou um erro inesperado. Consulte os detalhes técnicos abaixo.",
    )


def carregar_modelos_para_chave(
    api_key: str,
    origem: str,
) -> bool:
    try:
        modelos = listar_modelos_gemini(api_key)
        salvar_modelos_na_sessao(modelos, api_key, origem)

        if origem == "temporaria":
            st.session_state["gemini_api_key_temporaria"] = api_key.strip()

        st.session_state["gemini_feedback_modelos"] = {
            "tipo": "success",
            "mensagem": (
                f"Chave validada. {len(modelos)} modelo(s) compatível(is) "
                "com geração de conteúdo foram carregados."
            ),
        }
        return True

    except Exception as erro:
        titulo, mensagem = mensagem_amigavel_erro_gemini(
            erro,
            contexto="listagem",
        )
        st.session_state["gemini_feedback_modelos"] = {
            "tipo": "error",
            "mensagem": f"{titulo}. {mensagem}",
            "detalhes": str(erro),
        }
        return False


def testar_modelo_gemini(
    modelo_gemini: str,
    api_key_gemini: str,
) -> None:
    """Faz uma chamada mínima e opcional pela Interactions API."""
    client = genai.Client(api_key=api_key_gemini.strip())

    interaction = client.interactions.create(
        model=modelo_gemini.strip(),
        input="Responda somente com a palavra OK.",
        store=False,
    )

    if interaction.output_text is None:
        raise RuntimeError("O modelo respondeu sem conteúdo de texto.")


# ============================================================
# FUNÇÕES AUXILIARES DA EXTRAÇÃO
# ============================================================


def validar_pdf(pdf_bytes: bytes) -> None:
    if not pdf_bytes:
        raise ValueError("O arquivo selecionado está vazio.")

    if not pdf_bytes.startswith(b"%PDF"):
        raise ValueError("O arquivo selecionado não parece ser um PDF válido.")

    tamanho_mb = len(pdf_bytes) / (1024 * 1024)

    if tamanho_mb > 50:
        raise ValueError("O arquivo ultrapassa o limite de 50 MB desta aplicação.")


def extrair_nota_fiscal(
    pdf_bytes: bytes,
    modelo_gemini: str,
    api_key_gemini: Optional[str],
) -> NotaFiscalExtraida:
    if not api_key_gemini or not api_key_gemini.strip():
        raise RuntimeError(
            "Nenhuma chave do Gemini está disponível. "
            "Configure GEMINI_API_KEY no .env/Secrets ou informe uma "
            "chave temporária na barra lateral."
        )

    if not modelo_gemini.strip():
        raise ValueError("Informe um ID de modelo Gemini válido.")

    validar_pdf(pdf_bytes)

    client = genai.Client(api_key=api_key_gemini.strip())

    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

    # A lógica de leitura do PDF foi mantida pela Interactions API.
    interaction = client.interactions.create(
        model=modelo_gemini.strip(),
        input=[
            {
                "type": "document",
                "data": pdf_base64,
                "mime_type": "application/pdf",
            },
            {
                "type": "text",
                "text": PROMPT_EXTRACAO,
            },
        ],
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": NotaFiscalExtraida.model_json_schema(),
        },
        store=False,
    )

    if not interaction.output_text:
        raise RuntimeError("O Gemini não retornou dados para a nota fiscal.")

    return NotaFiscalExtraida.model_validate_json(
        interaction.output_text
    )


def formatar_moeda(valor: Optional[float]) -> str:
    if valor is None:
        return "Não identificado"

    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")

    return f"R$ {texto}"


def texto_ou_padrao(valor: Optional[str]) -> str:
    if valor is None or not str(valor).strip():
        return "Não identificado"

    return str(valor)


def resultado_para_json(resultado: NotaFiscalExtraida) -> str:
    return json.dumps(
        resultado.model_dump(),
        ensure_ascii=False,
        indent=2,
    )


def mostrar_resultado(resultado: NotaFiscalExtraida) -> None:
    st.markdown("### Dados extraídos")

    st.markdown(
        '<div class="result-caption">'
        "Confira abaixo os dados identificados na nota fiscal."
        "</div>",
        unsafe_allow_html=True,
    )

    aba_dados, aba_json = st.tabs(
        ["Visualização formatada", "JSON"]
    )

    with aba_dados:
        st.subheader("Fornecedor")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Razão social**")
            st.write(
                texto_ou_padrao(
                    resultado.fornecedor.razao_social
                )
            )

            st.write("**CNPJ**")
            st.write(
                texto_ou_padrao(
                    resultado.fornecedor.cnpj
                )
            )

        with col2:
            st.write("**Nome fantasia**")
            st.write(
                texto_ou_padrao(
                    resultado.fornecedor.nome_fantasia
                )
            )

        st.divider()

        st.subheader("Faturado")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Nome completo**")
            st.write(
                texto_ou_padrao(
                    resultado.faturado.nome_completo
                )
            )

        with col2:
            st.write("**CPF**")
            st.write(
                texto_ou_padrao(
                    resultado.faturado.cpf
                )
            )

        st.divider()

        st.subheader("Nota fiscal")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Número",
                texto_ou_padrao(
                    resultado.numero_nota_fiscal
                ),
            )

        with col2:
            st.metric(
                "Data de emissão",
                texto_ou_padrao(
                    resultado.data_emissao
                ),
            )

        with col3:
            st.metric(
                "Valor total",
                formatar_moeda(
                    resultado.valor_total
                ),
            )

        st.divider()

        st.subheader("Produtos / serviços")

        if resultado.descricao_produtos:
            for produto in resultado.descricao_produtos:
                st.write(f"• {produto}")
        else:
            st.info(
                "Nenhum produto ou serviço foi identificado."
            )

        st.divider()

        st.subheader("Parcelas")

        st.write(
            f"**Quantidade de parcelas:** "
            f"{resultado.quantidade_parcelas}"
        )

        if resultado.parcelas:
            dados_parcelas = []

            for parcela in resultado.parcelas:
                dados_parcelas.append(
                    {
                        "Parcela": parcela.numero,
                        "Vencimento": parcela.data_vencimento,
                        "Valor": formatar_moeda(
                            parcela.valor
                        ),
                    }
                )

            st.table(dados_parcelas)

        else:
            st.info(
                "Nenhuma parcela foi identificada."
            )

        st.divider()

        st.subheader(
            "Classificação da despesa"
        )

        if resultado.classificacao_despesa:
            for classificacao in resultado.classificacao_despesa:
                st.success(classificacao)

            st.caption(
                "A classificação é interpretada pelo Gemini "
                "com base nos produtos ou serviços da nota fiscal."
            )

        else:
            st.warning(
                "Não foi possível classificar a despesa "
                "com segurança."
            )

    with aba_json:
        json_texto = resultado_para_json(
            resultado
        )

        st.code(
            json_texto,
            language="json",
        )

        st.download_button(
            label="Baixar JSON",
            data=json_texto,
            file_name="nota_fiscal_extraida.json",
            mime="application/json",
            use_container_width=True,
        )


def mostrar_identificacao_alunos(
    modelo_gemini: str,
) -> None:
    commit_git = obter_commit_git()

    st.divider()

    st.markdown(
        "<p style='text-align:center; color:#8b8f98; "
        "font-size:0.78rem; letter-spacing:0.08em; "
        "text-transform:uppercase; margin-bottom:0.35rem;'>"
        "Desenvolvido por"
        "</p>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<p style='text-align:center; font-size:0.95rem; "
        "font-weight:600; line-height:1.65; margin:0;'>"
        "Danilo Couto Naves<br>"
        "Fabiano Borges da Cunha Sobrinho"
        "</p>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<p style='text-align:center; color:#8b8f98; "
        "font-size:0.82rem; margin-top:0.35rem; margin-bottom:0.1rem;'>"
        "Engenharia de Software · Projeto Administrativo-Financeiro"
        "</p>",
        unsafe_allow_html=True,
    )

    versao_segura = html.escape(APP_VERSION or "não definida")
    commit_seguro = html.escape(commit_git)
    modelo_seguro = html.escape(modelo_gemini or "não selecionado")

    st.markdown(
        f'<div class="version-footer">'
        f"Versão {versao_segura} · Commit Git: {commit_seguro} · "
        f"Modelo Gemini: {modelo_seguro}"
        "</div>",
        unsafe_allow_html=True,
    )


# ============================================================
# INÍCIO DA ÁREA AUTENTICADA
# ============================================================

exigir_autenticacao()

if "gemini_model" not in st.session_state:
    st.session_state["gemini_model"] = GEMINI_MODEL_PADRAO

if "gemini_api_key_input" not in st.session_state:
    st.session_state["gemini_api_key_input"] = ""

if "gemini_modelos" not in st.session_state:
    st.session_state["gemini_modelos"] = []

if "gemini_modo_manual" not in st.session_state:
    st.session_state["gemini_modo_manual"] = False

if "gemini_model_manual" not in st.session_state:
    st.session_state["gemini_model_manual"] = st.session_state["gemini_model"]

if "gemini_tentativa_projeto_realizada" not in st.session_state:
    st.session_state["gemini_tentativa_projeto_realizada"] = False


# ============================================================
# BARRA LATERAL
# ============================================================

with st.sidebar:
    st.markdown("### Sessão")
    st.caption(
        f"Usuário: {st.session_state.get('usuario_logado', APP_USERNAME)}"
    )

    if st.button(
        "Sair",
        use_container_width=True,
    ):
        encerrar_sessao()

    st.divider()

    st.markdown("### Configuração do Gemini")
    st.caption(
        "Cole uma API Key para validar a chave e carregar automaticamente "
        "os modelos disponíveis. Depois de colar, pressione Enter ou clique "
        "fora do campo."
    )

    st.text_input(
        "API Key do Gemini (opcional)",
        key="gemini_api_key_input",
        type="password",
        placeholder="Deixe vazio para usar a chave do projeto",
        help=(
            "A chave informada é validada consultando os modelos disponíveis. "
            "Se for aceita, ela fica somente na sessão atual e não é gravada "
            "no código, GitHub, .env ou banco de dados."
        ),
        on_change=solicitar_validacao_chave_temporaria,
    )

    origem_pendente = st.session_state.pop(
        "gemini_carregamento_pendente",
        None,
    )

    if origem_pendente == "temporaria":
        chave_pendente = str(
            st.session_state.get("gemini_api_key_input", "")
        ).strip()

        if chave_pendente:
            with st.spinner("Validando chave e carregando modelos..."):
                carregar_modelos_para_chave(
                    chave_pendente,
                    origem="temporaria",
                )

    elif origem_pendente == "projeto" and GEMINI_API_KEY_PROJETO:
        with st.spinner("Carregando modelos da chave do projeto..."):
            carregar_modelos_para_chave(
                GEMINI_API_KEY_PROJETO,
                origem="projeto",
            )
            st.session_state["gemini_tentativa_projeto_realizada"] = True

    if (
        not st.session_state.get("gemini_modelos")
        and GEMINI_API_KEY_PROJETO
        and not st.session_state.get("gemini_tentativa_projeto_realizada", False)
        and not usando_chave_temporaria()
    ):
        with st.spinner("Carregando modelos da chave do projeto..."):
            carregar_modelos_para_chave(
                GEMINI_API_KEY_PROJETO,
                origem="projeto",
            )
            st.session_state["gemini_tentativa_projeto_realizada"] = True

    feedback_modelos = st.session_state.get("gemini_feedback_modelos")

    if feedback_modelos:
        tipo = feedback_modelos.get("tipo")
        mensagem = feedback_modelos.get("mensagem", "")

        if tipo == "success":
            st.success(mensagem)
        elif tipo == "warning":
            st.warning(mensagem)
        else:
            st.error(mensagem)

        detalhes = feedback_modelos.get("detalhes")
        if detalhes:
            with st.expander("Detalhes técnicos"):
                st.code(detalhes)

    modelos_disponiveis = st.session_state.get("gemini_modelos", [])
    ids_modelos = [modelo["id"] for modelo in modelos_disponiveis]

    if modelos_disponiveis:
        st.caption(
            "Os modelos abaixo foram retornados pela API para a chave em uso "
            "e filtrados para modelos Gemini gerais com suporte a geração de conteúdo."
        )

        st.toggle(
            "Informar ID manualmente (avançado)",
            key="gemini_modo_manual",
            help=(
                "Use somente se precisar testar um ID que não apareceu na lista. "
                "A opção só é liberada depois que a chave e os modelos forem carregados."
            ),
        )

        if st.session_state["gemini_modo_manual"]:
            st.text_input(
                "ID manual do modelo Gemini",
                key="gemini_model_manual",
                placeholder="Ex.: gemini-3.6-flash",
            )

            if st.button(
                "Aplicar ID manual",
                use_container_width=True,
            ):
                modelo_manual = str(
                    st.session_state.get("gemini_model_manual", "")
                ).strip()

                if not modelo_manual:
                    st.error("Informe um ID de modelo válido.")
                else:
                    st.session_state["gemini_model"] = modelo_manual
                    st.session_state.pop("gemini_status_teste", None)
                    st.success("ID manual aplicado para esta sessão.")

        else:
            modelo_atual = st.session_state.get("gemini_model")

            if modelo_atual not in ids_modelos:
                modelo_atual = escolher_modelo_inicial(modelos_disponiveis)
                st.session_state["gemini_model"] = modelo_atual

            indice_atual = ids_modelos.index(modelo_atual)

            def rotulo_modelo(modelo_id: str) -> str:
                detalhe = next(
                    (
                        item
                        for item in modelos_disponiveis
                        if item["id"] == modelo_id
                    ),
                    None,
                )

                if not detalhe:
                    return modelo_id

                nome = str(detalhe.get("nome") or "").strip()

                if nome and nome.lower() != modelo_id.lower():
                    return f"{nome} · {modelo_id}"

                return modelo_id

            modelo_selecionado = st.selectbox(
                "Modelo Gemini",
                options=ids_modelos,
                index=indice_atual,
                format_func=rotulo_modelo,
                help=(
                    "A lista é obtida pela API usando a chave ativa. "
                    "A leitura do PDF continua sendo feita pela Interactions API."
                ),
            )

            if modelo_selecionado != st.session_state.get("gemini_model"):
                st.session_state["gemini_model"] = modelo_selecionado
                st.session_state["gemini_model_manual"] = modelo_selecionado
                st.session_state.pop("gemini_status_teste", None)

            detalhe_selecionado = next(
                (
                    item
                    for item in modelos_disponiveis
                    if item["id"] == st.session_state["gemini_model"]
                ),
                None,
            )

            if detalhe_selecionado:
                metadados = []
                limite_entrada = detalhe_selecionado.get("input_token_limit")
                limite_saida = detalhe_selecionado.get("output_token_limit")

                if limite_entrada:
                    metadados.append(f"entrada: {limite_entrada:,} tokens")

                if limite_saida:
                    metadados.append(f"saída: {limite_saida:,} tokens")

                if metadados:
                    st.caption(" · ".join(metadados))

        chave_ativa = obter_chave_gemini_ativa()

        if st.button(
            "Testar modelo selecionado",
            use_container_width=True,
            disabled=not bool(chave_ativa),
            help="O teste faz uma chamada curta e pode consumir uma requisição da cota.",
        ):
            if not chave_ativa:
                st.session_state["gemini_status_teste"] = {
                    "tipo": "error",
                    "mensagem": "Nenhuma API Key está ativa.",
                }
            else:
                with st.spinner("Testando o modelo pela Interactions API..."):
                    try:
                        testar_modelo_gemini(
                            st.session_state["gemini_model"],
                            chave_ativa,
                        )
                        st.session_state["gemini_status_teste"] = {
                            "tipo": "success",
                            "mensagem": (
                                f"{st.session_state['gemini_model']} respondeu normalmente."
                            ),
                        }
                    except Exception as erro:
                        titulo, mensagem = mensagem_amigavel_erro_gemini(
                            erro,
                            contexto="teste",
                        )
                        st.session_state["gemini_status_teste"] = {
                            "tipo": "error",
                            "mensagem": f"{titulo}. {mensagem}",
                            "detalhes": str(erro),
                        }

        status_teste = st.session_state.get("gemini_status_teste")

        if status_teste:
            if status_teste.get("tipo") == "success":
                st.success(status_teste.get("mensagem", "Modelo disponível."))
            else:
                st.warning(status_teste.get("mensagem", "Falha no teste do modelo."))

            if status_teste.get("detalhes"):
                with st.expander("Detalhes técnicos do teste"):
                    st.code(status_teste["detalhes"])

    else:
        st.selectbox(
            "Modelo Gemini",
            options=["Carregue uma API Key primeiro"],
            disabled=True,
        )
        st.caption(
            "O seletor de modelos só é liberado depois que uma chave válida "
            "for consultada e os modelos forem carregados."
        )

    col_recarregar, col_restaurar = st.columns(2)

    with col_recarregar:
        st.button(
            "Recarregar modelos",
            use_container_width=True,
            disabled=not bool(obter_chave_gemini_ativa()),
            on_click=solicitar_recarregamento_modelos,
        )

    with col_restaurar:
        st.button(
            "Chave do projeto",
            use_container_width=True,
            disabled=not usando_chave_temporaria(),
            on_click=voltar_para_chave_projeto,
            help="Remove a chave temporária e volta para a chave configurada no projeto.",
        )

    if usando_chave_temporaria():
        st.caption("Chave em uso: `chave temporária validada`")
    elif GEMINI_API_KEY_PROJETO:
        st.caption("Chave em uso: `chave do projeto`")
    else:
        st.caption("Chave em uso: `nenhuma chave configurada`")

    if st.session_state.get("gemini_modelos"):
        st.caption(
            f"Modelos carregados: `{len(st.session_state['gemini_modelos'])}`"
        )

    st.caption(
        f"Modelo em uso: `{st.session_state.get('gemini_model', 'não selecionado')}`"
    )

    st.divider()

    st.markdown("### Versionamento")
    st.caption(f"Versão: `{APP_VERSION}`")
    st.caption(f"Commit Git: `{obter_commit_git()}`")


# ============================================================
# INTERFACE PRINCIPAL
# ============================================================

st.markdown(
    """
<div style="text-align:center;">
    <span class="project-badge">
        Projeto Administrativo-Financeiro · Etapa 1
    </span>
</div>

<div class="hero-title">
    Extração de Dados de Nota Fiscal
</div>

<div class="hero-subtitle">
    Carregue uma nota fiscal em PDF e extraia os dados
    automaticamente utilizando IA.
</div>
    """,
    unsafe_allow_html=True,
)

configuracao_gemini_pronta = bool(
    obter_chave_gemini_ativa()
    and st.session_state.get("gemini_model")
    and st.session_state.get("gemini_modelos")
)

if not configuracao_gemini_pronta:
    st.info(
        "A configuração do Gemini ainda não está pronta. Abra a barra lateral, "
        "valide uma API Key e aguarde o carregamento dos modelos."
    )

with st.container(border=True):
    st.markdown(
        '<div class="section-title">Upload do PDF</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-description">'
        "Selecione o arquivo PDF da nota fiscal que será analisada."
        "</div>",
        unsafe_allow_html=True,
    )

    arquivo = st.file_uploader(
        "Selecione o arquivo PDF",
        type=["pdf"],
        help="Selecione uma nota fiscal em formato PDF.",
        label_visibility="collapsed",
    )

    if arquivo is not None:
        tamanho_kb = len(
            arquivo.getvalue()
        ) / 1024

        st.info(
            f"Arquivo selecionado: **{arquivo.name}** "
            f"({tamanho_kb:.1f} KB)"
        )

    botao_extrair = st.button(
        "EXTRAIR DADOS",
        type="primary",
        use_container_width=True,
        disabled=(arquivo is None or not configuracao_gemini_pronta),
    )

st.markdown(
    '<div class="small-note" style="text-align:center; margin-top:0.55rem;">'
    "O PDF é processado pelo Gemini para extração e interpretação "
    "dos dados financeiros. "
    f"Modelo atual: <strong>{html.escape(st.session_state.get('gemini_model') or 'não selecionado')}</strong>."
    "</div>",
    unsafe_allow_html=True,
)

st.write("")

if botao_extrair and arquivo is not None:
    try:
        with st.spinner(
            "Analisando a nota fiscal com o Gemini..."
        ):
            resultado = extrair_nota_fiscal(
                arquivo.getvalue(),
                st.session_state["gemini_model"],
                obter_chave_gemini_ativa(),
            )

        st.success(
            "Dados extraídos com sucesso."
        )

        with st.container(border=True):
            mostrar_resultado(
                resultado
            )

    except ValueError as erro:
        st.error(
            str(erro)
        )

    except Exception as erro:
        titulo, mensagem = mensagem_amigavel_erro_gemini(
            erro,
            contexto="extracao",
        )
        st.error(f"{titulo}. {mensagem}")

        with st.expander(
            "Detalhes técnicos do erro"
        ):
            st.code(
                str(erro)
            )


# ============================================================
# IDENTIFICAÇÃO DOS ALUNOS E VERSÃO
# ============================================================

mostrar_identificacao_alunos(
    st.session_state.get("gemini_model", "não selecionado")
)
