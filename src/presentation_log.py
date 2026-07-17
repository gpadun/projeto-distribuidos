"""Structured console logs for live demonstrations."""

import os


def log_apresentacao(prefixo: str, mensagem: str) -> None:
    """Print a tagged log line unless PRESENTATION_LOG=0."""
    if os.getenv("PRESENTATION_LOG", "1") == "0":
        return
    print(f"[{prefixo}] {mensagem}", flush=True)
