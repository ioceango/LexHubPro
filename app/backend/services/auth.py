"""启动时引导管理员。保留 main.py / lambda 的 import 路径。"""

from services.schema_bootstrap import bootstrap_admin_if_configured


async def initialize_admin_user() -> None:
    await bootstrap_admin_if_configured()
