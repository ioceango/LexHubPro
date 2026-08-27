"""自托管容器启动入口。

**为何需要独立入口而不是改 `main.py`**：`main.py` 属平台维护文件（禁改清单），
其 lifespan 内容由平台生成，无法插入自托管专属的自检与建表步骤。
本入口在启动 web 服务**之前**完成两件事，任一失败即以非零码退出，
使容器编排能立刻发现配置错误，而不是让服务带着缺陷对外提供请求。

顺序固定为：配置自检 → 幂等建表 → 用 `exec` 交棒给 uvicorn。
用 `exec` 替换进程而非子进程启动，是为了让 uvicorn 直接成为 PID 1 的前台进程，
从而正确接收 `docker stop` 发出的 SIGTERM 并优雅退出。
"""

import asyncio
import logging
import os
import sys

logger = logging.getLogger(__name__)

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = "8000"


async def _prepare() -> None:
    """执行启动前置检查与建表，并释放本次使用的数据库连接。

    必须在 `exec` 之前释放连接：`exec` 会替换整个进程映像，
    残留的连接不会被正常关闭，会在数据库侧堆积为空闲连接。
    """
    from services.startup_check import ensure_app_ready

    await ensure_app_ready()

    from core.database import db_manager

    closer = getattr(db_manager, "close_db", None) or getattr(db_manager, "close", None)
    if callable(closer):
        result = closer()
        if asyncio.iscoroutine(result):
            await result


def main() -> None:
    """启动流程入口。"""
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
        asyncio.run(_prepare())
    except Exception as exc:  # 配置错误必须阻断启动，不能降级为告警
        logger.error("[BIZ] startup aborted: %s", exc)
        sys.exit(1)

    host = os.getenv("HOST", DEFAULT_HOST)
    port = os.getenv("PORT", DEFAULT_PORT)
    logger.info("[BIZ] startup checks passed, launching uvicorn on %s:%s", host, port)

    os.execvp(
        "uvicorn",
        ["uvicorn", "main:app", "--host", host, "--port", str(port), "--no-access-log"],
    )


if __name__ == "__main__":
    main()