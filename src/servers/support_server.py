"""Servidor de Suporte (SUP).

Responsabilidades (docs/especificacao.md):
1. Enviar sua versão da lista de rastreio quando notar falha do seu Servidor R associado.
2. Caso o Servidor R associado retorne rapidamente, pode enviar uma lista temporária
   (possivelmente desatualizada) até que os Servidores ADM notem e remanejem os rastreios.
"""


class SupportServer:
    """Mantém uma cópia secundária (backup) dos rastreios de um Servidor Rastreador
    específico, para uso pelos Servidores ADM em caso de falha."""

    def __init__(self, id_servidor: str, id_servidor_rastreador_associado: str):
        """Inicializa o estado do servidor SUP e sua associação a um Servidor R."""
        raise NotImplementedError

    async def sincronizar_rastreios(self, rastreios: dict) -> None:
        """Atualiza a lista secundária de rastreios replicada a partir do Servidor R."""
        raise NotImplementedError

    async def enviar_lista_backup(self) -> dict:
        """Retorna a lista de rastreios mais recente conhecida por este SUP,
        solicitada pelo Servidor ADM após detectar falha do Servidor R associado."""
        raise NotImplementedError
