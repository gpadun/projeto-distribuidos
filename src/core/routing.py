"""Resolução determinística de qual Servidor Rastreador é responsável por um pedido.

Baseado em docs/especificacao.md: servidorResponsavel = hash(idPedido) mod N,
permitindo que qualquer componente calcule o servidor responsável sem consultar
um coordenador central.
"""

from uuid import UUID


def calcular_servidor_responsavel(id_pedido: UUID, n_servidores: int) -> int:
    """Calcula o índice do Servidor Rastreador responsável por `id_pedido`.

    Usa o inteiro subjacente do UUID (id_pedido.int) como entrada do hash, em vez
    da função hash() nativa, pois hash() não é garantida como estável entre
    processos diferentes (PYTHONHASHSEED) — o que quebraria a premissa de que
    qualquer componente deve chegar à mesma conclusão de forma independente.

    Args:
        id_pedido: Identificador único (UUID) do pedido.
        n_servidores: Quantidade de Servidores Rastreadores ativos no momento.

    Returns:
        Índice (0 a n_servidores - 1) do servidor responsável.

    Raises:
        ValueError: Se `n_servidores` não for um inteiro positivo.
    """
    if n_servidores <= 0:
        raise ValueError("n_servidores deve ser um inteiro positivo")

    return id_pedido.int % n_servidores
