"""Data contracts for the delivery tracking system."""

from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class StatusPedido(str, Enum):
    """Order states used throughout the proof of concept."""

    RECEM_CRIADO = "RECEM_CRIADO"
    COM_ENTREGADOR = "COM_ENTREGADOR"
    COM_SERVIDOR_RASTREADOR = "COM_SERVIDOR_RASTREADOR"


class TipoServidor(str, Enum):
    """Server types declared by keepAlive messages in the PDF spec."""

    ADM = "ADM"
    RASTREADOR = "RASTREADOR"
    SUPORTE = "SUPORTE"


class CriarPedido(BaseModel):
    """Synchronous command sent by a customer to create an order."""

    idPedido: UUID
    idCliente: str
    idRestaurante: str
    timestamp: int


class AceitarPedido(BaseModel):
    """Synchronous command sent by a driver to accept an available order."""

    idPedido: UUID
    idEntregador: str
    timestamp: int


class ConfirmarEntrega(BaseModel):
    """Synchronous command sent by a customer to confirm delivery."""

    idPedido: UUID
    idCliente: str
    timestamp: int


class PedidoDisponivel(BaseModel):
    """Event published when an order still has no assigned driver."""

    idPedido: UUID
    idRestaurante: str
    timestamp: int


class LocalizacaoEntregador(BaseModel):
    """Event published by the driver with the newest GPS position."""

    idEntregador: str
    idPedido: UUID
    latitude: float
    longitude: float
    timestamp: int


class EventoLocalizacao(BaseModel):
    """Location event forwarded to tracking subscribers."""

    idPedido: UUID
    latitude: float
    longitude: float
    timestamp: int


class SubscribeRastreio(BaseModel):
    """Tracking subscription message described by the PDF spec."""

    idPedido: UUID
    idServidorRastreador: str


class EntregaConfirmada(BaseModel):
    """Event published after delivery confirmation."""

    idPedido: UUID
    timestamp: int


class KeepAlive(BaseModel):
    """Periodic heartbeat exchanged between system components."""

    idServidor: str
    tipoServidor: TipoServidor
    timestamp: int


class AtualizacaoRoteamento(BaseModel):
    """Internal message announcing which tracker owns an order."""

    idPedido: UUID
    idServidorRastreador: str
    idEntregador: str | None = None
    timestamp: int


class TipoMensagemEleicao(str, Enum):
    """Message kinds exchenged during Bully leader election."""

    INICAR = "INCIAR"
    RESPOSTA = "RESPOSTA"
    NOVO_LIDER = "NOVO_LIDER"


class IniciarEleicao(BaseModel):
    """Sent by an ADM to higher-ID peers to start leader election."""

    idServidorOrigem: str
    timestamp: int
    idServidorDestino: str | None = None
    idLiderAnterior: str | None = None


class RespostaEleicao(BaseModel):
    """Sent by a higher-ID ADM to confirm it is alive during election."""

    idServidorOrigem: str
    idServidorDestino: str
    timestamp: int


class NovoLider(BaseModel):
    """Announces the elected ADM leader to all peers"""

    idServidor: str
    timestamp: int
    idLiderAnterior: str | None = None


class ReplicacaoRoteamento(BaseModel):
    """Full ADM state snapshot sent from the leader to peers."""

    idServidorOrigem: str
    roteamento: dict[str, str]
    pedidos: dict[str, dict] = {}
    pedidosSemEntregador: list[str] = []
    timestamp: int


class Cliente(BaseModel):
    """Customer identity."""

    idCliente: str
    ip: str | None = None


class Entregador(BaseModel):
    """Driver identity."""

    idEntregador: str


class Restaurante(BaseModel):
    """Hardcoded restaurant identity for the proof of concept."""

    idRestaurante: str
    ip: str | None = None


class Pedido(BaseModel):
    """Complete order representation across its lifecycle."""

    idPedido: UUID
    idCliente: str
    idRestaurante: str
    timestamp: int
    status: StatusPedido = StatusPedido.RECEM_CRIADO
    idEntregador: str | None = None
    servidorRastreadorResponsavel: str | None = None


class ServidorRastreador(BaseModel):
    """Tracker server identity."""

    idServidor: str
    ip: str


class ServidorAdministrador(BaseModel):
    """Administrator server identity."""

    idServidor: str
    ip: str


class ServidorSuporte(BaseModel):
    """Support server identity, associated to one tracker server."""

    idServidor: str
    ip: str
    idServidorRastreadorAssociado: str
