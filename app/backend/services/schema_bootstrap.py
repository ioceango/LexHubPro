"""建表、存量状态收敛、表/字段 COMMENT ON 幂等补齐、管理员引导。"""

import logging
import re
from typing import Optional

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from core.database import Base, db_manager

logger = logging.getLogger(__name__)

LEGACY_TABLE_RENAMES = (
    ("local_auth_users", "tb_user"),
    ("local_auth_refresh_tokens", "tb_refresh_token"),
    ("local_auth_one_time_tokens", "tb_one_time_token"),
    ("local_auth_audits", "tb_auth_audit"),
    ("local_contracts", "tb_contract"),
    ("local_review_reports", "tb_review_report"),
    ("contracts", "tb_contract"),
    ("review_reports", "tb_review_report"),
)
LEGACY_EMPTY_DROPS = ("contracts", "review_reports", "tb_oidc_user", "tb_oidc_state", "users", "oidc_states")

_IDENT = re.compile(r"^[a-z][a-z0-9_]*$")


def _sql_str(value: str) -> str:
    """PostgreSQL 字符串字面量。COMMENT ON ... IS 不能用绑定参数。"""
    return "'" + value.replace("'", "''") + "'"


def comment_table_sql(table_name: str, comment: str) -> str:
    # BUG-003 回归：禁止 :c / $1，PG 会语法错误
    if not _IDENT.fullmatch(table_name):
        raise ValueError("unsafe table name")
    return f"COMMENT ON TABLE {table_name} IS {_sql_str(comment)}"


def comment_column_sql(table_name: str, column_name: str, comment: str) -> str:
    if not _IDENT.fullmatch(table_name) or not _IDENT.fullmatch(column_name):
        raise ValueError("unsafe identifier")
    return f"COMMENT ON COLUMN {table_name}.{column_name} IS {_sql_str(comment)}"


async def _resolve_engine() -> AsyncEngine:
    if db_manager.engine is None:
        await db_manager.init_db()
    if db_manager.engine is None:
        raise RuntimeError("Database engine is unavailable for schema bootstrap")
    return db_manager.engine


def _rename_legacy_tables(sync_conn) -> list[str]:
    existing = set(inspect(sync_conn).get_table_names())
    done: list[str] = []
    for old_name, new_name in LEGACY_TABLE_RENAMES:
        if old_name in existing and new_name not in existing:
            sync_conn.execute(text(f'ALTER TABLE "{old_name}" RENAME TO "{new_name}"'))
            existing.discard(old_name)
            existing.add(new_name)
            done.append(f"{old_name}->{new_name}")
    for leftover in LEGACY_EMPTY_DROPS:
        if leftover not in existing:
            continue
        count = sync_conn.execute(text(f'SELECT COUNT(*) FROM "{leftover}"')).scalar() or 0
        if count == 0:
            sync_conn.execute(text(f'DROP TABLE "{leftover}" CASCADE'))
            existing.discard(leftover)
            done.append(f"drop-empty:{leftover}")
    return done


def _normalize_contract_status(sync_conn) -> None:
    names = set(inspect(sync_conn).get_table_names())
    if "tb_contract" not in names:
        return
    sync_conn.execute(text("UPDATE tb_contract SET status = 'pending' WHERE status IN ('uploaded')"))
    sync_conn.execute(text("UPDATE tb_contract SET status = 'reviewing' WHERE status IN ('analyzing')"))
    try:
        sync_conn.execute(text("ALTER TABLE tb_contract DROP CONSTRAINT IF EXISTS ck_tb_contract_status"))
        sync_conn.execute(
            text(
                "ALTER TABLE tb_contract ADD CONSTRAINT ck_tb_contract_status "
                "CHECK (status IN ('pending', 'reviewing', 'completed', 'failed'))"
            )
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("[DB_OP] contract status check skipped type=%s", type(exc).__name__)


OWNER_USER_ID_TABLES = ("tb_contract", "tb_review_report")


def owner_user_fk_name(table_name: str) -> str:
    return f"{table_name}_user_id_fkey"


def alter_user_id_to_integer_sql(table_name: str) -> str:
    """BUG-007：存量 varchar user_id 转为 integer。"""
    if not _IDENT.fullmatch(table_name):
        raise ValueError("unsafe table name")
    return f"ALTER TABLE {table_name} ALTER COLUMN user_id TYPE integer USING user_id::integer"


def add_user_id_fk_sql(table_name: str) -> str:
    """BUG-007：合同/报告 user_id 指向 tb_user.id。"""
    if not _IDENT.fullmatch(table_name):
        raise ValueError("unsafe table name")
    fk_name = owner_user_fk_name(table_name)
    if not _IDENT.fullmatch(fk_name):
        raise ValueError("unsafe identifier")
    return (
        f"ALTER TABLE {table_name} ADD CONSTRAINT {fk_name} "
        "FOREIGN KEY (user_id) REFERENCES tb_user(id) ON DELETE CASCADE"
    )


def _column_type_is_integer(type_obj: object) -> bool:
    rendered = str(type_obj).lower()
    return rendered.startswith("int") or rendered.startswith("serial") or rendered.startswith("bigint")


def _align_owner_user_id_types(sync_conn) -> list[str]:
    """把合同/报告的 user_id 与 tb_user.id 对齐。仅 PostgreSQL 需要改存量表。"""
    if sync_conn.dialect.name != "postgresql":
        return []
    inspector = inspect(sync_conn)
    existing = set(inspector.get_table_names())
    done: list[str] = []
    for table in OWNER_USER_ID_TABLES:
        if table not in existing or "tb_user" not in existing:
            continue
        columns = {col["name"]: col for col in inspector.get_columns(table)}
        if "user_id" not in columns:
            continue
        fks = inspector.get_foreign_keys(table)
        has_user_fk = any(
            fk.get("referred_table") == "tb_user"
            and list(fk.get("constrained_columns") or []) == ["user_id"]
            for fk in fks
        )
        if not _column_type_is_integer(columns["user_id"]["type"]):
            bad = (
                sync_conn.execute(
                    text(
                        f"SELECT COUNT(*) FROM {table} "
                        "WHERE user_id IS NOT NULL AND user_id !~ '^[0-9]+$'"
                    )
                ).scalar()
                or 0
            )
            if bad:
                raise RuntimeError(f"{table}.user_id has non-numeric values count={bad}")
            orphans = (
                sync_conn.execute(
                    text(
                        f"SELECT COUNT(*) FROM {table} t WHERE NOT EXISTS "
                        "(SELECT 1 FROM tb_user u WHERE u.id = CAST(t.user_id AS integer))"
                    )
                ).scalar()
                or 0
            )
            if orphans:
                raise RuntimeError(f"{table}.user_id has orphan rows count={orphans}")
            sync_conn.execute(text(alter_user_id_to_integer_sql(table)))
            done.append(f"{table}.user_id:varchar->integer")
        if not has_user_fk:
            sync_conn.execute(text(add_user_id_fk_sql(table)))
            done.append(f"{table}.user_id_fkey")
    return done


def _apply_comments(sync_conn) -> int:
    applied = 0
    for table in Base.metadata.sorted_tables:
        table_comment = table.comment
        if table_comment:
            sync_conn.execute(text(comment_table_sql(table.name, table_comment)))
            applied += 1
        for column in table.columns:
            if column.comment:
                sync_conn.execute(text(comment_column_sql(table.name, column.name, column.comment)))
                applied += 1
    return applied


async def ensure_app_schema(engine: Optional[AsyncEngine] = None) -> list[str]:
    from models import AUTH_MODELS, DATA_MODELS

    target = [m.__table__ for m in AUTH_MODELS + DATA_MODELS]
    names = [t.name for t in target]
    active = engine or await _resolve_engine()
    async with active.begin() as conn:
        renamed = await conn.run_sync(_rename_legacy_tables)
        if renamed:
            logger.info("[DB_OP] renamed legacy tables %s", ",".join(renamed))
        await conn.run_sync(Base.metadata.create_all, tables=target, checkfirst=True)
        aligned = await conn.run_sync(_align_owner_user_id_types)
        if aligned:
            logger.info("[DB_OP] owner user_id aligned %s", ",".join(aligned))
        await conn.run_sync(_normalize_contract_status)
        n = await conn.run_sync(_apply_comments)
        logger.info("[DB_OP] table/column comments applied count=%s", n)
    logger.info("[DB_OP] app schema ensured tables=%s", ",".join(names))
    return names


async def ensure_local_auth_schema(engine: Optional[AsyncEngine] = None) -> list[str]:
    return await ensure_app_schema(engine)


async def ensure_local_data_schema(engine: Optional[AsyncEngine] = None) -> list[str]:
    return await ensure_app_schema(engine)


async def bootstrap_admin_if_configured() -> None:
    from repositories import user as repository
    from services.auth_accounts import current_tenant_id
    from utils.config_reader import read_str

    email = read_str("auth_bootstrap_admin_email", "").strip().lower()
    if not email:
        return
    engine = await _resolve_engine()
    async with AsyncSession(engine) as session:
        async with session.begin():
            user = await repository.get_user_by_email(session, current_tenant_id(), email)
            if user is None:
                logger.info("[BIZ] bootstrap admin skipped, account not registered yet")
                return
            await repository.update_user_fields(session, user.id, role="admin", status="active")
            logger.info("[BIZ] bootstrap admin applied")
