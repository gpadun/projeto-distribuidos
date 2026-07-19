import httpx
from src.core.models import (
    KeepAlive,
    IniciarEleicao,
    RespostaEleicao,
    NovoLider,
    ReplicacaoRoteamento,
)
from src.core.serialization import to_message_dict
from src.servers.adm_server import ADMServer


class ADMHttpTransport:
    """HTTP client for ADM-to-ADM messages; ignores unreachable peers."""

    def __init__(self, enderecos_adm: dict[str, str], timeout: float = 2.0):
        self.enderecos_adm = enderecos_adm
        self.timeout = timeout

    def _url(self, id_destino: str, path: str) -> str:
        base = self.enderecos_adm[id_destino].rstrip("/")
        return f"{base}{path}"

    async def enviar_keepalive(self, id_destino: str, mensagem: KeepAlive) -> None:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                await client.post(
                    self._url(id_destino, "/infra/keepalive"),
                    json=to_message_dict(mensagem),
                )
        except httpx.HTTPError:
            return

    async def enviar_eleicao(
        self,
        id_destino: str,
        mensagem: IniciarEleicao | RespostaEleicao | NovoLider,
    ) -> None:
        if isinstance(mensagem, IniciarEleicao):
            path = "/infra/eleicao/iniciar"
        elif isinstance(mensagem, RespostaEleicao):
            path = "/infra/eleicao/resposta"
        else:
            path = "/infra/eleicao/novo-lider"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                await client.post(
                    self._url(id_destino, path),
                    json=to_message_dict(mensagem),
                )
        except httpx.HTTPError:
            return

    async def enviar_replicacao_roteamento(
        self,
        id_destino: str,
        mensagem: ReplicacaoRoteamento,
    ) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self._url(id_destino, "/infra/replicar-roteamento"),
                    json=to_message_dict(mensagem),
                )
                return response.status_code < 400
        except httpx.HTTPError:
            return False

    async def consultar_estado(self, id_destino: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self._url(id_destino, "/estado"))
            response.raise_for_status()
            return response.json()

def criar_adm_com_transporte_http(
    id_servidor: str,
    enderecos_adm: dict[str, str],
    servidores_adm: list[str],
    **kwargs,
) -> ADMServer:
    transport = ADMHttpTransport(enderecos_adm)

    adm = ADMServer(
        id_servidor=id_servidor,
        servidores_adm=servidores_adm,
        keepalive_sender=transport.enviar_keepalive,
        election_sender=transport.enviar_eleicao,
        replication_sender=transport.enviar_replicacao_roteamento,
        state_fetcher=transport.consultar_estado,
        **kwargs,
    )

    async def on_lider_caiu(_: str):
        await adm.iniciar_eleicao()

    adm.on_lider_caiu = on_lider_caiu
    return adm
