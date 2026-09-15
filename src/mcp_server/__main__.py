"""`python -m src.mcp_server` 入口。

外部 MCP Client 通常以「指定 cwd + 启动子进程」的方式拉起 server，
这里显式把项目根目录放进 sys.path，避免 cwd 不是仓库根时 `import src.*` 失败。
"""
from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.mcp_server.server import main  # noqa: E402

if __name__ == "__main__":
    main()
