"""注册邮箱域名白名单与 SMTP 预设。

支持的收件箱：163（163.com / 126.com / yeah.net）与 Gmail。
发信预设：163 用 465+SSL，Gmail 用 587+STARTTLS，本地用 Mailpit。
"""

from utils.config_reader import read_bool, read_int, read_str

SUPPORTED_MAILBOX_DOMAINS = frozenset(
    {
        "163.com",
        "126.com",
        "yeah.net",
        "gmail.com",
        "googlemail.com",
    }
)

UNSUPPORTED_MAILBOX_HINT = "请使用 163 或 Gmail 邮箱，例如 name@163.com 或 name@gmail.com"

SMTP_PRESETS = {
    "163": {"host": "smtp.163.com", "port": 465, "ssl": True, "starttls": False},
    "gmail": {"host": "smtp.gmail.com", "port": 587, "ssl": False, "starttls": True},
    "mailpit": {"host": "mailpit", "port": 1025, "ssl": False, "starttls": False},
}


def mailbox_domain(email: str) -> str:
    parts = (email or "").strip().lower().split("@")
    return parts[-1] if len(parts) == 2 else ""


def smtp_provider_name() -> str:
    explicit = read_str("smtp_provider", "").strip().lower()
    if explicit:
        return explicit
    host = read_str("smtp_host", "").lower()
    if "gmail" in host:
        return "gmail"
    if "163.com" in host:
        return "163"
    if host in {"mailpit", "localhost", "127.0.0.1"}:
        return "mailpit"
    return ""


def is_supported_mailbox(email: str) -> bool:
    if read_bool("auth_mailbox_allow_all", False):
        return True
    return mailbox_domain(email) in SUPPORTED_MAILBOX_DOMAINS


def resolve_smtp() -> dict:
    """合并 SMTP_PROVIDER 预设与显式环境变量。空端口视为未覆盖。"""
    preset = SMTP_PRESETS.get(smtp_provider_name(), {})
    explicit_port = read_int("smtp_port", 0)
    ssl_raw = read_str("smtp_ssl", "")
    tls_raw = read_str("smtp_starttls", "")
    host = read_str("smtp_host", "") or str(preset.get("host") or "")
    port = explicit_port if explicit_port > 0 else int(preset.get("port") or 587)
    use_ssl = read_bool("smtp_ssl", bool(preset.get("ssl"))) if ssl_raw else bool(preset.get("ssl"))
    use_tls = (
        read_bool("smtp_starttls", bool(preset.get("starttls")))
        if tls_raw
        else bool(preset.get("starttls"))
    )
    user = read_str("smtp_user", "")
    password = read_str("smtp_password", "")
    default_from = user if user else "noreply@lexhubpro.local"
    return {
        "provider": smtp_provider_name(),
        "host": host,
        "port": port,
        "ssl": use_ssl,
        "starttls": use_tls and not use_ssl,
        "user": user,
        "password": password,
        "from_addr": read_str("smtp_from", "") or default_from,
    }


def smtp_ready() -> bool:
    cfg = resolve_smtp()
    if not cfg["host"]:
        return False
    if cfg["provider"] in {"163", "gmail"} and not (cfg["user"] and cfg["password"]):
        return False
    return True
