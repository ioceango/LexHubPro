# 完成清单：FEAT-006 后端四层与表命名规约

- [x] `.agent/architecture.md` 写明四层铁律与 `tb_*` + 注释
- [x] `.agent/rules.md` 分层表改为 api / services / repositories / models
- [x] `.agent/constraints.md` 删除 models 禁改与「禁止写入 models」
- [x] `AGENTS.md` / `CLAUDE.md` / `.grok/rules/00-legalguard-rules.md` 红线摘要同步
- [x] `docs/rules/01`、`06`、`07`、`04` 与模板、`docs/README.md` 同步
- [x] `.atoms/ATOMS.md`、`ARCHITECTURE.md`、`PROGRESS.md` 同步
- [x] `app/backend/api/`、`repositories/` 包就绪
- [x] `main.py` 扫描 `api` 包
- [x] 存量表改为 `tb_*`，启动可 RENAME 旧名
- [x] HTTP 模块迁入 `api/`，`routers/` 仅留空包
- [x] 删除 `local_auth/`、`local_data/` 旁路包
- [x] pytest 37 passed
- [x] `bash scripts/verify.sh --docs-only`（见 test-report）
