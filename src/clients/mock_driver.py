"""Simulador de entregador (mock_driver).

Gera coordenadas GPS falsas periodicamente e publica LocalizacaoEntregador,
permitindo testes de carga e múltiplos entregadores ativos sem dispositivos reais.
"""


class MockDriver:
    """Simula um entregador enviando atualizações periódicas de localização."""

    def __init__(self, id_entregador: str, id_pedido: str):
        """Associa o mock a um entregador e ao pedido que ele está entregando."""
        raise NotImplementedError

    async def gerar_localizacao_falsa(self) -> tuple[float, float]:
        """Gera uma coordenada (latitude, longitude) falsa para simular movimento."""
        raise NotImplementedError

    async def enviar_localizacoes_periodicamente(self, intervalo_segundos: float) -> None:
        """Envia LocalizacaoEntregador ao Servidor Rastreador em intervalos regulares."""
        raise NotImplementedError


def main() -> None:
    """Ponto de entrada para executar o simulador de entregador via terminal."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
