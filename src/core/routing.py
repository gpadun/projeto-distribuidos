"""Deterministic routing for Tracker servers.

The PDF specification describes consistent hashing with virtual nodes:
hash(idServidor + "#" + indice) places tracker replicas on a logical ring, and
hash(idPedido) chooses the first clockwise virtual node.
"""

from hashlib import sha256
from functools import lru_cache
from uuid import UUID


def _hash_int(value: str) -> int:
    return int.from_bytes(sha256(value.encode("utf-8")).digest(), "big")


def calcular_servidor_responsavel(id_pedido: UUID, n_servidores: int) -> int:
    """Backward-compatible index route for older tests/docs."""
    if n_servidores <= 0:
        raise ValueError("n_servidores deve ser um inteiro positivo")
    return id_pedido.int % n_servidores


@lru_cache(maxsize=128)
def _construir_anel(
    servidores: tuple[str, ...],
    replicas_virtuais: int,
) -> tuple[tuple[int, str], ...]:
    anel: list[tuple[int, str]] = []
    for id_servidor in servidores:
        for indice in range(replicas_virtuais):
            anel.append((_hash_int(f"{id_servidor}#{indice}"), id_servidor))
    anel.sort(key=lambda item: item[0])
    return tuple(anel)


def escolher_servidor_consistent_hash(
    id_pedido: UUID,
    servidores: list[str],
    replicas_virtuais: int = 32,
) -> str:
    """Choose the tracker responsible for an order using consistent hashing."""
    if not servidores:
        raise ValueError("servidores deve conter ao menos um servidor")
    if replicas_virtuais <= 0:
        raise ValueError("replicas_virtuais deve ser positivo")

    anel = _construir_anel(tuple(sorted(servidores)), replicas_virtuais)

    posicao_pedido = _hash_int(str(id_pedido))
    for posicao_no, id_servidor in anel:
        if posicao_no >= posicao_pedido:
            return id_servidor
    return anel[0][1]
