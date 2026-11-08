from __future__ import annotations

import uvicorn

from .config import get_settings


def main() -> None:
    s = get_settings()
    print("=" * 72)
    print("ManaTee — untrusted LLM proxy PoC")
    print(f"  upstream : {s.ollama_url}")
    print(f"  model    : {s.default_model}")
    print(f"  listen   : {s.host}:{s.port}")
    print(f"  admin UI : http://127.0.0.1:{s.port}/admin/ui")
    print(f"  admin tok: {s.admin_token}")
    print("=" * 72)
    uvicorn.run("manatee.app:app", host=s.host, port=s.port, log_level=s.log_level)


if __name__ == "__main__":
    main()
