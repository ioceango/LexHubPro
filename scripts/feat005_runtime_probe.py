"""FEAT-005 阶段四/五运行期探针（一次性验证脚本）。

**为何需要单独脚本而非单元测试**：这些断言依赖「进程启动时的环境变量组合」，
每个用例都必须在干净的子进程里重新加载配置与模块，放在同一测试进程里
会被前一个用例已缓存的 settings 污染，结论不可信。

覆盖的实测点：
1. `AUTH_MODE=local` 缺少签名密钥时，启动自检必须失败并给出配置项名称；
2. 密钥过短时必须失败（防暴力枚举），且失败信息不得回显密钥取值；
3. `STORAGE_MODE=minio` 凭据/端点不可达时，连通性探测必须使启动失败；
4. 预签名有效期必须被裁剪到上限，寻址风格必须为 path-style；
5. 配置占位符 `$$X$$` 必须等同「未配置」。

用法：python scripts/feat005_runtime_probe.py
退出码非 0 表示存在不符合预期的行为。
"""

import json
import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "app" / "backend"

# 32 位以上的测试用密钥。仅用于本地探针，不进入任何配置文件。
VALID_SECRET = "probe-secret-value-for-feat005-check-0123456789"
SHORT_SECRET = "too-short"


def _run_case(name: str, env: dict, snippet: str) -> dict:
    """在干净子进程中执行一个用例，返回结构化结果。"""
    child_env = {
        key: value
        for key, value in os.environ.items()
        # 清掉宿主进程里可能已存在的同类配置，避免污染用例前提
        if not key.startswith(("AUTH_MODE", "STORAGE_MODE", "LOCAL_AUTH_", "MINIO_"))
    }
    child_env.update(env)
    child_env["PYTHONPATH"] = str(BACKEND_DIR)

    proc = subprocess.run(
        [sys.executable, "-c", snippet],
        cwd=str(BACKEND_DIR),
        env=child_env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return {
        "case": name,
        "exit_code": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip()[-800:],
    }


STARTUP_SNIPPET = """
import asyncio, json
from services.startup_check import run_startup_check

async def main():
    try:
        result = await run_startup_check(strict=True)
        return {"ok": True, "auth_mode": result.auth_mode, "storage_mode": result.storage_mode}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}

print("PROBE_JSON " + json.dumps(asyncio.run(main()), ensure_ascii=False))
"""

PROVIDER_SNIPPET = """
import json
from storage_providers.minio_provider import MinioStorageProvider, MAX_PRESIGN_EXPIRES_SECONDS

provider = MinioStorageProvider()
url = provider._client.generate_presigned_url(
    "get_object",
    Params={"Bucket": "contracts", "Key": "u1/demo.pdf"},
    ExpiresIn=provider._default_expires,
)
print("PROBE_JSON " + json.dumps({
    "default_expires": provider._default_expires,
    "max_expires": MAX_PRESIGN_EXPIRES_SECONDS,
    "addressing_style": provider._addressing_style,
    "path_style_url": url.split("?")[0],
    "has_signature": "X-Amz-Signature=" in url,
    "has_expires": "X-Amz-Expires=" in url,
}, ensure_ascii=False))
"""

PLACEHOLDER_SNIPPET = """
import json
from utils.config_reader import is_placeholder, read_str, ConfigError, require_str

outcome = {"is_placeholder": is_placeholder("$$MINIO_ACCESS_KEY$$")}
outcome["read_str_fallback"] = read_str("minio_access_key", "FALLBACK")
try:
    require_str("minio_access_key")
    outcome["require_raised"] = False
except ConfigError as exc:
    outcome["require_raised"] = True
    outcome["message"] = str(exc)
print("PROBE_JSON " + json.dumps(outcome, ensure_ascii=False))
"""


def _payload(result: dict) -> dict:
    """从子进程输出中取出结构化结果。"""
    for line in result["stdout"].splitlines():
        if line.startswith("PROBE_JSON "):
            return json.loads(line[len("PROBE_JSON ") :])
    return {}


def main() -> int:
    """执行全部用例并打印判定结论。"""
    failures: list[str] = []

    cases = [
        (
            "C1 local 模式缺失签名密钥应启动失败",
            {"AUTH_MODE": "local", "STORAGE_MODE": "platform"},
            STARTUP_SNIPPET,
        ),
        (
            "C2 签名密钥过短应启动失败且不回显取值",
            {
                "AUTH_MODE": "local",
                "STORAGE_MODE": "platform",
                "LOCAL_AUTH_SECRET_KEY": SHORT_SECRET,
            },
            STARTUP_SNIPPET,
        ),
        (
            "C3 minio 端点不可达应启动失败",
            {
                "AUTH_MODE": "local",
                "STORAGE_MODE": "minio",
                "LOCAL_AUTH_SECRET_KEY": VALID_SECRET,
                "MINIO_ENDPOINT": "http://127.0.0.1:19",
                "MINIO_ACCESS_KEY": "probe-access",
                "MINIO_SECRET_KEY": "probe-secret",
                "MINIO_VERIFY_TLS": "false",
            },
            STARTUP_SNIPPET,
        ),
        (
            "C4 预签名有效期裁剪与 path-style 寻址",
            {
                "STORAGE_MODE": "minio",
                "MINIO_ENDPOINT": "http://minio:9000",
                "MINIO_ACCESS_KEY": "probe-access",
                "MINIO_SECRET_KEY": "probe-secret",
                "MINIO_PRESIGN_EXPIRES_SECONDS": "99999999",
                "MINIO_VERIFY_TLS": "false",
            },
            PROVIDER_SNIPPET,
        ),
        (
            "C5 占位符等同未配置",
            {"MINIO_ACCESS_KEY": "$$MINIO_ACCESS_KEY$$"},
            PLACEHOLDER_SNIPPET,
        ),
    ]

    results = []
    for name, env, snippet in cases:
        result = _run_case(name, env, snippet)
        result["payload"] = _payload(result)
        results.append(result)

    # ---- C1 ----
    p1 = results[0]["payload"]
    if p1.get("ok") is not False or "LOCAL_AUTH_SECRET_KEY" not in p1.get("error", ""):
        failures.append("C1 未按预期因缺失 LOCAL_AUTH_SECRET_KEY 而失败")

    # ---- C2 ----
    p2 = results[1]["payload"]
    error2 = p2.get("error", "")
    if p2.get("ok") is not False or "32" not in error2:
        failures.append("C2 未按预期因密钥长度不足而失败")
    if SHORT_SECRET in error2:
        failures.append("C2 失败信息回显了密钥取值（违反脱敏要求）")

    # ---- C3 ----
    p3 = results[2]["payload"]
    error3 = p3.get("error", "")
    if p3.get("ok") is not False or "connectivity" not in error3.lower():
        failures.append("C3 未按预期因对象存储不可达而失败")
    if "probe-secret" in error3 or VALID_SECRET in error3:
        failures.append("C3 失败信息回显了凭据（违反脱敏要求）")

    # ---- C4 ----
    p4 = results[3]["payload"]
    if p4.get("default_expires") != p4.get("max_expires"):
        failures.append("C4 预签名有效期未被裁剪到上限")
    if p4.get("addressing_style") != "path":
        failures.append("C4 寻址风格不是 path-style")
    if p4.get("path_style_url") != "http://minio:9000/contracts/u1/demo.pdf":
        failures.append(f"C4 预签名 URL 结构异常: {p4.get('path_style_url')}")
    if not p4.get("has_signature") or not p4.get("has_expires"):
        failures.append("C4 预签名 URL 缺少签名或有效期参数")

    # ---- C5 ----
    p5 = results[4]["payload"]
    if not p5.get("is_placeholder") or p5.get("read_str_fallback") != "FALLBACK":
        failures.append("C5 占位符未被识别为未配置")
    if not p5.get("require_raised"):
        failures.append("C5 占位符未触发必填校验失败")

    for result in results:
        print(f"[{result['case']}] exit={result['exit_code']} payload={result['payload']}")
        if not result["payload"] and result["stderr"]:
            print(f"  stderr: {result['stderr']}")

    if failures:
        print("\nPROBE_RESULT FAIL")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("\nPROBE_RESULT PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())