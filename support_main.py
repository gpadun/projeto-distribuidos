"""Run one SUP process."""

import os
import uvicorn

from src.support_api import create_support_app

if __name__ == "__main__":
    id_servidor = os.getenv("SUP_ID", "sup-1")
    id_rastreador = os.getenv("SUP_RASTREADOR", "rastreador-1")
    port = int(os.getenv("SUP_PORT", "9101"))
    host = os.getenv("SUP_HOST", "127.0.0.1")

    app = create_support_app(id_servidor, id_rastreador)
    uvicorn.run(app, host=host, port=port)