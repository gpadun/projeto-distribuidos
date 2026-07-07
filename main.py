import os

import uvicorn


def main():
    reload_enabled = os.getenv("UVICORN_RELOAD", "").lower() in {"1", "true", "yes"}
    uvicorn.run("src.api:app", host="127.0.0.1", port=8000, reload=reload_enabled)


if __name__ == "__main__":
    main()
