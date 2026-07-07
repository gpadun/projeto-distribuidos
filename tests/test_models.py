"""Validation tests for src.core.models."""

from uuid import UUID, uuid4

from src.core.models import (
    CriarPedido,
    KeepAlive,
    LocalizacaoEntregador,
    Pedido,
    StatusPedido,
    SubscribeRastreio,
    TipoServidor,
)
from src.core.serialization import to_message_dict


def test_criar_pedido_valido():
    id_pedido = uuid4()

    pedido = CriarPedido(
        idPedido=str(id_pedido),
        idCliente="cliente-1",
        idRestaurante="restaurante-1",
        timestamp=1710000000,
    )

    assert pedido.idPedido == id_pedido
    assert isinstance(pedido.idPedido, UUID)


def test_pedido_inicia_como_recem_criado():
    pedido = Pedido(
        idPedido=uuid4(),
        idCliente="cliente-1",
        idRestaurante="restaurante-1",
        timestamp=1710000000,
    )

    assert pedido.status == StatusPedido.RECEM_CRIADO
    assert pedido.idEntregador is None
    assert pedido.servidorRastreadorResponsavel is None


def test_localizacao_entregador_aceita_coordenadas():
    localizacao = LocalizacaoEntregador(
        idEntregador="entregador-1",
        idPedido=uuid4(),
        latitude=-23.55,
        longitude=-46.63,
        timestamp=1710000002,
    )

    assert localizacao.latitude == -23.55
    assert localizacao.longitude == -46.63


def test_subscribe_rastreio_inclui_servidor_rastreador():
    assinatura = SubscribeRastreio(idPedido=uuid4(), idServidorRastreador="R1")

    assert assinatura.idServidorRastreador == "R1"


def test_keepalive_inclui_tipo_servidor():
    keepalive = KeepAlive(idServidor="R1", tipoServidor="RASTREADOR", timestamp=1710000004)

    assert keepalive.tipoServidor == TipoServidor.RASTREADOR


def test_serializacao_retorna_tipos_json_native():
    pedido = CriarPedido(
        idPedido=uuid4(),
        idCliente="cliente-1",
        idRestaurante="restaurante-1",
        timestamp=1710000000,
    )

    payload = to_message_dict(pedido)

    assert isinstance(payload["idPedido"], str)
