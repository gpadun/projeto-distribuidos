"""CLI entrypoint for the restaurant demo client."""

import argparse
import sys

from src.clients.restaurant_broker import RestaurantBrokerError, executar_restaurante_broker


def main() -> int:
    parser = argparse.ArgumentParser(description="Mock de restaurante via RabbitMQ")
    parser.add_argument("--id-restaurante", default="restaurante-1")
    parser.add_argument("--adm-url", default=None)
    parser.add_argument(
        "--sem-preparo-auto",
        action="store_true",
        help="ouve pedidos sem marcar automaticamente como preparado",
    )
    args = parser.parse_args()

    try:
        executar_restaurante_broker(
            id_restaurante=args.id_restaurante,
            adm_url=args.adm_url,
            preparar_automatico=not args.sem_preparo_auto,
        )
    except RestaurantBrokerError as exc:
        print(f"[restaurante] erro: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
