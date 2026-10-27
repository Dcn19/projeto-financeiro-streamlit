"""Rodar com: python -m unittest discover -s tests -v"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from financeiro import ErroLancamento, validar_lancamento


def exemplo():
    return {
        "fornecedor_nome": "Oficina e Máquinas Ltda",
        "fornecedor_documento": "12.345.678/0001-90",
        "faturado_nome": "Beltrano Silva",
        "faturado_documento": "999.999.999-99",
        "numero_nota": "000000123",
        "data_emissao": "27/10/2026",
        "descricao": "Manutenção de tratores",
        "valor_total": 1500.00,
        "classificacoes": ["MANUTENÇÃO E OPERAÇÃO", "IMPOSTOS E TAXAS"],
        "parcelas": [
            {"numero": 1, "vencimento": "01/11/2026", "valor": 500},
            {"numero": 2, "vencimento": "01/12/2026", "valor": 1000},
        ],
    }


class TesteValidacao(unittest.TestCase):
    def test_dados_validos(self):
        result = validar_lancamento(exemplo())
        self.assertEqual(result["fornecedor_documento"], "12345678000190")
        self.assertEqual(len(result["parcelas"]), 2)
        self.assertEqual(len(result["classificacoes"]), 2)
        self.assertEqual(len(result["chave_origem"]), 64)

    def test_faltando_cnpj(self):
        entrada = exemplo()
        entrada["fornecedor_documento"] = ""
        with self.assertRaises(ErroLancamento):
            validar_lancamento(entrada)

    def test_faltando_faturado(self):
        entrada = exemplo()
        entrada["faturado_documento"] = None
        with self.assertRaises(ErroLancamento):
            validar_lancamento(entrada)

    def test_soma_divergente(self):
        entrada = exemplo()
        entrada["parcelas"][1]["valor"] = 999
        with self.assertRaises(ErroLancamento):
            validar_lancamento(entrada)

    def test_parcelas_repetidas(self):
        entrada = exemplo()
        entrada["parcelas"][1]["numero"] = 1
        with self.assertRaises(ErroLancamento):
            validar_lancamento(entrada)

    def test_numero_zero_nao_e_corrigido_silenciosamente(self):
        entrada = exemplo()
        entrada["parcelas"][0]["numero"] = 0
        with self.assertRaises(ErroLancamento):
            validar_lancamento(entrada)

    def test_sem_vencimento(self):
        entrada = exemplo()
        entrada["parcelas"][0]["vencimento"] = ""
        with self.assertRaises(ErroLancamento):
            validar_lancamento(entrada)

    def test_categoria_vazia(self):
        entrada = exemplo()
        entrada["classificacoes"] = []
        with self.assertRaises(ErroLancamento):
            validar_lancamento(entrada)

    def test_mesma_nota_gera_mesma_chave(self):
        original = validar_lancamento(exemplo())
        segunda = exemplo()
        segunda["fornecedor_documento"] = "12345678000190"
        self.assertEqual(original["chave_origem"], validar_lancamento(segunda)["chave_origem"])

    def test_notas_diferentes_geram_chave_diferente(self):
        original = validar_lancamento(exemplo())
        segunda = exemplo()
        segunda["numero_nota"] = "124"
        self.assertNotEqual(original["chave_origem"], validar_lancamento(segunda)["chave_origem"])


if __name__ == "__main__":
    unittest.main()
