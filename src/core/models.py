"""Estruturas de dados do sistema de rastreamento de entregas.

Modelos derivados diretamente das mensagens definidas em docs/especificacao.md:
mensagens de comando (request/response), mensagens de evento (publish-subscribe)
e mensagens internas de infraestrutura (servidor -> servidor).
"""

from enum import Enum
from uuid import UUID

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class StatusPedido(str, Enum):
    """Estados possíveis de um pedido ao longo do seu ciclo de vida."""

    RECEM_CRIADO = "RECEM_CRIADO"
    COM_ENTREGADOR = "COM_ENTREGADOR"
    COM_SERVIDOR_RASTREADOR = "COM_SERVIDOR_RASTREADOR"


# ---------------------------------------------------------------------------
# Mensagens de comando (request/response, Cliente/Entregador -> Servidor)
# ---------------------------------------------------------------------------

class CriarPedido(BaseModel):
    """Requisição síncrona do cliente para criar um novo pedido."""

    idPedido: UUID
    idCliente: str
    idRestaurante: str
    timestamp: int


class AceitarPedido(BaseModel):
    """Requisição síncrona do entregador para aceitar um pedido disponível."""

    idPedido: UUID
    idEntregador: str
    timestamp: int


class ConfirmarEntrega(BaseModel):
    """Requisição síncrona do cliente confirmando o recebimento do pedido."""

    idPedido: UUID
    idCliente: str
    timestamp: int


# ---------------------------------------------------------------------------
# Mensagens de evento (modelo Publish-Subscribe via Message Broker)
# ---------------------------------------------------------------------------

class PedidoDisponivel(BaseModel):
    """Evento publicado pelo Servidor ADM quando um pedido ainda não tem entregador."""

    idPedido: UUID
    idRestaurante: str
    timestamp: int


class LocalizacaoEntregador(BaseModel):
    """Evento publicado pelo entregador com sua posição GPS mais recente."""

    idEntregador: str
    idPedido: UUID
    latitude: float
    longitude: float
    timestamp: int


class EventoLocalizacao(BaseModel):
    """Evento entregue pelo broker aos clientes assinantes do rastreio de um pedido."""

    idPedido: UUID
    latitude: float
    longitude: float
    timestamp: int


class SubscribeRastreio(BaseModel):
    """Solicitação de um cliente para assinar as atualizações de rastreio de um pedido."""

    idPedido: UUID


class EntregaConfirmada(BaseModel):
    """Evento publicado após a confirmação de entrega, notificando o entregador."""

    idPedido: UUID
    timestamp: int


# ---------------------------------------------------------------------------
# Mensagens internas (infraestrutura do sistema, Servidor -> Servidor)
# ---------------------------------------------------------------------------

class KeepAlive(BaseModel):
    """Mensagem de heartbeat trocada entre servidores para detectar quedas."""

    idServidor: str
    timestamp: int


class AtualizacaoRoteamento(BaseModel):
    """Mensagem que atualiza qual servidor rastreador é responsável por quais pedidos."""

    idPedido: UUID
    idServidorRastreador: str
    timestamp: int


# ---------------------------------------------------------------------------
# Entidades nomeadas do sistema
# ---------------------------------------------------------------------------

class Cliente(BaseModel):
    """Identificação de um cliente: <ID/IP>."""

    idCliente: str
    ip: str | None = None


class Entregador(BaseModel):
    """Identificação de um entregador: <ID>. Seu IP pode mudar, pois está em movimento."""

    idEntregador: str


class Restaurante(BaseModel):
    """Identificação de um restaurante (pré-cadastrado/hardcoded): <ID/IP>."""

    idRestaurante: str
    ip: str | None = None


class Pedido(BaseModel):
    """Representação completa de um pedido e seu estágio no ciclo de vida.

    Reflete os esquemas de nomeação por atributos definidos na especificação:
    Pedido Recém Criado -> Pedido com Entregador -> Pedido com Servidor
    Rastreador Atribuído (campo servidorRastreadorResponsavel é mutável).
    """

    idPedido: UUID
    idCliente: str
    idRestaurante: str
    timestamp: int
    status: StatusPedido = StatusPedido.RECEM_CRIADO
    idEntregador: str | None = None
    servidorRastreadorResponsavel: str | None = None


class ServidorRastreador(BaseModel):
    """Identificação de um Servidor Rastreador (R): <ID/IP>."""

    idServidor: str
    ip: str


class ServidorAdministrador(BaseModel):
    """Identificação de um Servidor Administrador (ADM): <ID/IP>."""

    idServidor: str
    ip: str


class ServidorSuporte(BaseModel):
    """Identificação de um Servidor de Suporte (SUP): <ID/IP, ID_Servidor_Rastreio>.

    Cada Servidor de Suporte está associado a exatamente um Servidor Rastreador.
    """

    idServidor: str
    ip: str
    idServidorRastreadorAssociado: str
