-- Projeto Administrativo-Financeiro | N2 Etapa 2
-- As tabelas usam nomes do enunciado. Cadastro é excluído apenas logicamente.

CREATE TABLE IF NOT EXISTS pessoas (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tipo VARCHAR(24) NOT NULL CHECK (tipo IN ('CLIENTE-FORNECEDOR', 'FATURADO')),
    razao_social TEXT NOT NULL,
    nome_fantasia TEXT,
    documento VARCHAR(14) NOT NULL,
    status VARCHAR(7) NOT NULL DEFAULT 'ATIVO' CHECK (status IN ('ATIVO', 'INATIVO')),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_pessoas_tipo_documento ON pessoas(tipo, documento);

CREATE INDEX IF NOT EXISTS ix_pessoas_nome ON pessoas(tipo, razao_social);

CREATE TABLE IF NOT EXISTS classificacao (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tipo VARCHAR(12) NOT NULL CHECK (tipo IN ('DESPESA', 'RECEITA')),
    descricao TEXT NOT NULL,
    status VARCHAR(7) NOT NULL DEFAULT 'ATIVO' CHECK (status IN ('ATIVO', 'INATIVO')),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ux_classificacao_tipo_descricao UNIQUE(tipo, descricao)
);

CREATE TABLE IF NOT EXISTS movimentocontas (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tipo VARCHAR(10) NOT NULL CHECK (tipo IN ('APAGAR', 'ARECEBER')),
    fornecedor_id BIGINT NOT NULL REFERENCES pessoas(id) ON DELETE RESTRICT,
    faturado_id BIGINT NOT NULL REFERENCES pessoas(id) ON DELETE RESTRICT,
    numero_nota_fiscal TEXT NOT NULL,
    data_emissao DATE NOT NULL,
    descricao TEXT,
    valor_total NUMERIC(14,2) NOT NULL CHECK (valor_total > 0),
    chave_origem CHAR(64) NOT NULL UNIQUE,
    status VARCHAR(7) NOT NULL DEFAULT 'ATIVO' CHECK (status IN ('ATIVO', 'INATIVO')),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS movimentocontas_classificacao (
    movimento_id BIGINT NOT NULL REFERENCES movimentocontas(id) ON DELETE RESTRICT,
    classificacao_id BIGINT NOT NULL REFERENCES classificacao(id) ON DELETE RESTRICT,
    PRIMARY KEY(movimento_id, classificacao_id)
);

CREATE TABLE IF NOT EXISTS parcelacontas (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    movimento_id BIGINT NOT NULL REFERENCES movimentocontas(id) ON DELETE RESTRICT,
    identificacao TEXT NOT NULL UNIQUE,
    numero INTEGER NOT NULL CHECK (numero > 0),
    data_vencimento DATE NOT NULL,
    valor NUMERIC(14,2) NOT NULL CHECK (valor > 0),
    status VARCHAR(7) NOT NULL DEFAULT 'ATIVO' CHECK (status IN ('ATIVO', 'INATIVO')),
    criado_em TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ux_parcela_movimento_numero UNIQUE(movimento_id, numero)
);

CREATE INDEX IF NOT EXISTS ix_parcelas_vencimento ON parcelacontas(data_vencimento);

CREATE INDEX IF NOT EXISTS ix_movimento_data ON movimentocontas(data_emissao);
