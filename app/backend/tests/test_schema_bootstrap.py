"""BUG-003 回归：COMMENT ON 必须用字面量，不能走绑定参数。"""

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.schema_bootstrap import (
    add_user_id_fk_sql,
    alter_user_id_to_integer_sql,
    comment_column_sql,
    comment_table_sql,
)


def test_comment_sql_uses_literal_not_placeholder():
    # BUG-003 回归
    sql = comment_table_sql("tb_auth_audit", "认证审计表：只记事件与脱敏哈希，不存密码或令牌明文。")
    assert ":c" not in sql
    assert "$1" not in sql
    assert sql.startswith("COMMENT ON TABLE tb_auth_audit IS '")
    assert "认证审计表" in sql


def test_comment_sql_escapes_quotes():
    # BUG-003 回归
    sql = comment_column_sql("tb_user", "email", "登录邮箱，含 O'Brien 类字符")
    assert "O''Brien" in sql
    assert "$1" not in sql


def test_owner_user_id_alter_sql_is_integer_cast():
    # BUG-007 回归
    sql = alter_user_id_to_integer_sql("tb_contract")
    assert "TYPE integer" in sql
    assert "USING user_id::integer" in sql
    assert ":" not in sql.replace("::integer", "")
    fk = add_user_id_fk_sql("tb_review_report")
    assert "REFERENCES tb_user(id) ON DELETE CASCADE" in fk
    assert "tb_review_report_user_id_fkey" in fk
