"""Testes da resolução determinística de servidor responsável (src/core/routing.py)."""

from uuid import uuid4

import pytest

from src.core.routing import calcular_servidor_responsavel


def test_e_deterministico_para_o_mesmo_pedido():
    """Chamadas repetidas com o mesmo idPedido e N devem retornar sempre o mesmo índice."""
    id_pedido = uuid4()

    resultados = {calcular_servidor_responsavel(id_pedido, 5) for _ in range(100)}

    assert len(resultados) == 1


def test_resultado_esta_sempre_dentro_dos_limites():
    """O índice retornado nunca deve estourar o intervalo [0, n_servidores)."""
    for n_servidores in range(1, 20):
        for _ in range(50):
            indice = calcular_servidor_responsavel(uuid4(), n_servidores)
            assert 0 <= indice < n_servidores


def test_n_servidores_igual_a_um_sempre_retorna_zero():
    """Com um único servidor, todo pedido deve ser roteado para o índice 0."""
    assert calcular_servidor_responsavel(uuid4(), 1) == 0


@pytest.mark.parametrize("n_servidores", [0, -1, -10])
def test_n_servidores_invalido_gera_erro(n_servidores):
    """N não positivo deve falhar explicitamente em vez de gerar ZeroDivisionError."""
    with pytest.raises(ValueError):
        calcular_servidor_responsavel(uuid4(), n_servidores)
