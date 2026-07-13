import os

import uvicorn


def main():
    port = int(os.getenv("ADM_PORT", "8000"))
    host = os.getenv("ADM_HOST", "127.0.0.1")
    uvicorn.run("src.api:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
