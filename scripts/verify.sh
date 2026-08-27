#!/usr/bin/env bash
# ==============================================================================
# LexHubPro 一键自动化验证脚本
# ------------------------------------------------------------------------------
# 职责：
#   ⓿ 文档合规 gate：校验 .agent/ 跨工具规约齐全性、各工具入口指针有效性，
#      以及 docs/features 与 docs/bug-fix 的编号目录结构、四份文档齐全性与
#      索引登记情况（.agent/verification.md §2、docs/rules/04-iteration-workflow.md §2）。
#   ①~⑤ 按 docs/rules/05-testing-and-automation.md §3 的固定顺序执行静态检查、
#      测试与构建，收集每步退出码与输出摘要，并生成测试验证报告骨架。
#
# 用法：
#   bash scripts/verify.sh --docs-only                    # 仅执行文档合规 gate
#   bash scripts/verify.sh                                # gate + 全量验证
#   bash scripts/verify.sh BUG-002-ai-review-failure      # 全量验证并写入该迭代报告
#   bash scripts/verify.sh FEAT-004-batch-review          # 同上（需求迭代）
#
# 约束：本脚本只读取与执行，不修改任何业务代码、不执行 git 操作。
# ==============================================================================

set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/app/backend"
FRONTEND_DIR="$ROOT_DIR/app/frontend"
FEATURES_DIR="$ROOT_DIR/docs/features"
BUGFIX_DIR="$ROOT_DIR/docs/bug-fix"
AGENT_DIR="$ROOT_DIR/.agent"
TMP_DIR="$(mktemp -d)"
SUMMARY_LINES=20

# 迭代四文档（缺一不可）
REQUIRED_DOCS=(spec.md plan.md checklist.md test-report.md)
# .agent/ 跨工具规约必需文件（缺一不可）
AGENT_SPEC_DOCS=(README.md architecture.md rules.md constraints.md workflow.md verification.md design.md)
# 各 AI 编码工具入口指针文件（必须存在、非空且指向 .agent/）
TOOL_POINTERS=(AGENTS.md CLAUDE.md .grok/rules/00-lexhubpro-rules.md)
# 视为「未完成占位」的标记
PLACEHOLDER_PATTERNS='TODO|待填写|待补充|FIXME|<占位|XXX-占位'

ITERATION=""
DOCS_ONLY=0

# 记录每一步的结果，用于最终汇总与报告生成
STEP_NAMES=()
STEP_CMDS=()
STEP_CODES=()
STEP_LOGS=()
FAILED_STEP=""

# 文档合规问题清单
DOC_ISSUES=()

cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

log_section() {
  printf '\n\033[1;36m==== %s ====\033[0m\n' "$1"
}

parse_args() {
  local arg
  for arg in "$@"; do
    case "$arg" in
      --docs-only) DOCS_ONLY=1 ;;
      -h|--help)
        sed -n '2,20p' "${BASH_SOURCE[0]}"
        exit 0
        ;;
      -*)
        echo "未知参数：$arg" >&2
        exit 2
        ;;
      *) ITERATION="$arg" ;;
    esac
  done
}

# ------------------------------------------------------------------------------
# ⓿ 文档合规 gate
# ------------------------------------------------------------------------------

add_issue() { DOC_ISSUES+=("$1"); }

# check_iteration_dir <目录绝对路径> <编号正则> <索引文件绝对路径> <索引相对路径>
# 校验单个编号目录：命名格式、四文档齐全、非空非占位、索引已登记
check_iteration_dir() {
  local dir="$1" pattern="$2" index_file="$3" index_rel="$4"
  local base doc doc_path
  base="$(basename "$dir")"

  if ! [[ "$base" =~ $pattern ]]; then
    add_issue "目录命名不合规：$base（应匹配 ${pattern}）"
    return
  fi

  for doc in "${REQUIRED_DOCS[@]}"; do
    doc_path="$dir/$doc"
    if [ ! -f "$doc_path" ]; then
      add_issue "缺少文档：$base/$doc"
      continue
    fi
    if [ ! -s "$doc_path" ]; then
      add_issue "文档为空：$base/$doc"
      continue
    fi
    if grep -Eq "$PLACEHOLDER_PATTERNS" "$doc_path"; then
      add_issue "文档仍含未完成占位标记：$base/$doc"
    fi
  done

  if [ -f "$index_file" ] && ! grep -q "$base" "$index_file"; then
    add_issue "未登记到索引 $index_rel：$base"
  fi
}

# scan_category <目录绝对路径> <编号正则> <索引相对路径> <类别名>
scan_category() {
  local root="$1" pattern="$2" index_rel="$3" label="$4"
  local index_file="$root/README.md"
  local dir count=0 ids=() id

  if [ ! -d "$root" ]; then
    add_issue "$label 目录不存在：$index_rel 的上级目录缺失"
    return
  fi
  if [ ! -f "$index_file" ]; then
    add_issue "$label 索引文件缺失：$index_rel"
  fi

  for dir in "$root"/*/; do
    [ -d "$dir" ] || continue
    count=$((count + 1))
    check_iteration_dir "${dir%/}" "$pattern" "$index_file" "$index_rel"
    id="$(basename "${dir%/}" | cut -d- -f1-2)"
    ids+=("$id")
  done

  # 编号唯一性校验
  if [ "${#ids[@]}" -gt 0 ]; then
    local dup
    dup="$(printf '%s\n' "${ids[@]}" | sort | uniq -d)"
    if [ -n "$dup" ]; then
      add_issue "$label 存在重复编号：$(echo "$dup" | tr '\n' ' ')"
    fi
  fi

  echo "  ${label} 发现 ${count} 个编号目录"
}

# 校验 .agent/ 跨工具规约：目录存在、六份必需文件存在且非空
check_agent_spec() {
  local doc doc_path present=0

  if [ ! -d "$AGENT_DIR" ]; then
    add_issue ".agent/ 规约目录缺失（跨工具单一事实源，必须存在）"
    return
  fi

  for doc in "${AGENT_SPEC_DOCS[@]}"; do
    doc_path="$AGENT_DIR/$doc"
    if [ ! -f "$doc_path" ]; then
      add_issue "缺少跨工具规约文件：.agent/$doc"
      continue
    fi
    if [ ! -s "$doc_path" ]; then
      add_issue "跨工具规约文件为空：.agent/$doc"
      continue
    fi
    present=$((present + 1))
  done

  echo "  跨工具规约(.agent)：$present/${#AGENT_SPEC_DOCS[@]} 份文件就绪"
}

# 校验各工具入口指针：存在、非空且确实指向 .agent/
check_tool_pointers() {
  local pointer pointer_path ok=0

  for pointer in "${TOOL_POINTERS[@]}"; do
    pointer_path="$ROOT_DIR/$pointer"
    if [ ! -f "$pointer_path" ]; then
      add_issue "缺少工具入口指针文件：$pointer"
      continue
    fi
    if [ ! -s "$pointer_path" ]; then
      add_issue "工具入口指针文件为空：$pointer"
      continue
    fi
    if ! grep -q '\.agent/' "$pointer_path"; then
      add_issue "工具入口指针未指向 .agent/：$pointer（须包含 .agent/ 必读清单）"
      continue
    fi
    if grep -q '^## 关键红线摘要' "$pointer_path"; then
      add_issue "工具入口指针含红线条款拷贝：$pointer（须为纯路标，条款只写在 .agent/）"
      continue
    fi
    ok=$((ok + 1))
  done

  echo "  工具入口指针：$ok/${#TOOL_POINTERS[@]} 份有效并指向 .agent/"
}

# 表 DDL/ER 目录：文件必须存在，且 models 中每个 __tablename__ 都出现在文档里
check_ddl_catalog() {
  local ddl_rel="docs/ddl/database-ddl-er.md"
  local ddl_path="$ROOT_DIR/$ddl_rel"
  local models_dir="$BACKEND_DIR/models"
  local table

  if [ ! -f "$ddl_path" ] || [ ! -s "$ddl_path" ]; then
    add_issue "缺少表结构目录：$ddl_rel（须含现行表 DDL 与 ER 图）"
    return
  fi
  if [ ! -d "$models_dir" ]; then
    return
  fi
  while IFS= read -r table; do
    [ -n "$table" ] || continue
    if ! grep -q "$table" "$ddl_path"; then
      add_issue "表目录未收录 ORM 表名 $table（应写入 $ddl_rel）"
    fi
  done < <(grep -RhoE '__tablename__\s*=\s*["'"'"'][a-z0-9_]+["'"'"']' "$models_dir" --include='*.py' \
    | sed -E 's/.*["'"'"']([a-z0-9_]+)["'"'"'].*/\1/' | sort -u)
  echo "  表 DDL/ER 目录：$ddl_rel 已检查"
}

# 仓库根 README：给人读的入口，须覆盖架构/功能/目录/TODO/部署/本地开发，并点名主流 vibe 工具与指针
check_root_readme() {
  local readme="$ROOT_DIR/README.md"
  local missing=()
  local topic tool pointer

  if [ ! -f "$readme" ] || [ ! -s "$readme" ]; then
    add_issue "缺少仓库根 README.md（须含架构、功能、目录、TODO、部署、本地开发）"
    return
  fi
  for topic in 架构 功能 目录 TODO 部署 本地开发; do
    if ! grep -q "$topic" "$readme"; then
      missing+=("$topic")
    fi
  done
  for tool in Codex Claude DeepSeek Trae Cursor; do
    if ! grep -q "$tool" "$readme"; then
      missing+=("$tool")
    fi
  done
  for pointer in AGENTS.md CLAUDE.md '.agent/' '.grok/rules'; do
    if ! grep -F -q "$pointer" "$readme"; then
      missing+=("$pointer")
    fi
  done
  if [ "${#missing[@]}" -gt 0 ]; then
    add_issue "根 README.md 缺少必需要素：${missing[*]}"
    return
  fi
  echo "  根 README.md：架构/功能/目录/TODO/部署/本地开发与 Codex/Claude/DeepSeek/Trae/Cursor 入口已覆盖"
}

# 执行文档合规校验，通过返回 0，否则返回 1
run_docs_gate() {
  log_section "⓿ 文档合规 gate"
  DOC_ISSUES=()

  check_agent_spec
  check_tool_pointers
  check_ddl_catalog
  check_root_readme
  scan_category "$FEATURES_DIR" '^FEAT-[0-9]{3}-[a-z0-9]+(-[a-z0-9]+)*$' "docs/features/README.md" "需求(FEAT)"
  scan_category "$BUGFIX_DIR" '^BUG-[0-9]{3}-[a-z0-9]+(-[a-z0-9]+)*$' "docs/bug-fix/README.md" "缺陷(BUG)"

  local log_file="$TMP_DIR/docs_gate.log"
  local code=0
  if [ "${#DOC_ISSUES[@]}" -gt 0 ]; then
    code=1
    {
      echo "文档合规校验未通过，共 ${#DOC_ISSUES[@]} 项问题："
      printf '  - %s\n' "${DOC_ISSUES[@]}"
    } | tee "$log_file"
    printf '\033[1;31m✗ ⓿ 文档合规 gate 失败（%s 项问题）\033[0m\n' "${#DOC_ISSUES[@]}"
  else
    echo ".agent 规约齐全、工具指针有效、根 README 覆盖、编号目录命名与四文档齐全性、非占位与索引登记全部通过" | tee "$log_file"
    printf '\033[1;32m✓ ⓿ 文档合规 gate 通过\033[0m\n'
  fi

  STEP_NAMES+=("⓿ 文档合规 gate")
  STEP_CMDS+=("verify.sh --docs-only")
  STEP_CODES+=("$code")
  STEP_LOGS+=("$log_file")

  if [ "$code" -ne 0 ]; then
    FAILED_STEP="⓿ 文档合规 gate"
    return 1
  fi
  return 0
}

# ------------------------------------------------------------------------------
# ①~⑤ 代码验证
# ------------------------------------------------------------------------------

# run_step <名称> <工作目录> <命令...>
# 执行单个验证步骤；失败立即终止后续步骤（快速失败，避免掩盖根因）。
run_step() {
  local name="$1"; shift
  local workdir="$1"; shift
  local cmd="$*"
  local log_file="$TMP_DIR/$(echo "$name" | tr ' /' '__').log"

  log_section "$name"
  echo "\$ (cd $workdir && $cmd)"

  local code=0
  if [ ! -d "$workdir" ]; then
    echo "目录不存在，跳过：$workdir" | tee "$log_file"
    code=0
  else
    ( cd "$workdir" && eval "$cmd" ) 2>&1 | tee "$log_file"
    code="${PIPESTATUS[0]}"
  fi

  STEP_NAMES+=("$name")
  STEP_CMDS+=("$cmd")
  STEP_CODES+=("$code")
  STEP_LOGS+=("$log_file")

  if [ "$code" -ne 0 ]; then
    FAILED_STEP="$name"
    printf '\033[1;31m✗ %s 失败（退出码 %s）\033[0m\n' "$name" "$code"
    return 1
  fi
  printf '\033[1;32m✓ %s 通过\033[0m\n' "$name"
  return 0
}

# 收集后端本次可编译校验的目标文件（业务层，排除平台托管目录）
collect_backend_targets() {
  ( cd "$BACKEND_DIR" 2>/dev/null && \
    ls api/*.py services/*.py repositories/*.py models/*.py schemas/*.py dependencies/*.py utils/*.py auth_providers/*.py storage_providers/*.py 2>/dev/null \
    | tr '\n' ' ' )
}

main() {
  # ⓿ 文档合规 gate：任何代码验证之前先卡文档
  run_docs_gate || finish

  if [ "$DOCS_ONLY" -eq 1 ]; then
    echo ""
    echo "仅执行文档合规 gate（--docs-only），跳过代码验证步骤"
    finish
  fi

  local backend_targets
  backend_targets="$(collect_backend_targets)"

  # ① 后端静态检查
  if [ -n "$backend_targets" ]; then
    run_step "① 后端静态检查" "$BACKEND_DIR" "python -m py_compile $backend_targets" || finish
  fi

  # ② 后端测试（无 tests 目录时视为跳过）
  if [ -d "$BACKEND_DIR/tests" ]; then
    run_step "② 后端测试" "$BACKEND_DIR" "python -m pytest tests -q" || finish
  else
    echo "未发现 app/backend/tests，跳过后端测试（新增测试后将自动纳入）"
  fi

  # ③ 前端依赖与 Lint
  run_step "③ 前端 Lint" "$FRONTEND_DIR" "pnpm i --silent && pnpm run lint" || finish

  # ④ 前端单元测试（package.json 中存在 test 脚本时执行）
  if [ -f "$FRONTEND_DIR/package.json" ] && grep -q '"test"' "$FRONTEND_DIR/package.json"; then
    run_step "④ 前端单元测试" "$FRONTEND_DIR" "pnpm run test -- --run" || finish
  else
    echo "未发现前端 test 脚本，跳过前端单元测试"
  fi

  # ⑤ 前端构建（最终门禁：捕获未解析导入等致命问题）
  run_step "⑤ 前端构建" "$FRONTEND_DIR" "pnpm run build" || finish

  # ⑥ Playwright 端到端：截图写入迭代 test-report/ 目录
  local shot_dir=""
  if [ -n "$ITERATION" ]; then
    shot_dir="$(resolve_iteration_dir)/test-report"
  fi
  if [ -x "$FRONTEND_DIR/node_modules/.bin/playwright" ]; then
    run_step "⑥ Playwright 端到端" "$FRONTEND_DIR" \
      "HTTP_PROXY= HTTPS_PROXY= http_proxy= https_proxy= NO_PROXY='*' E2E_SCREENSHOT_DIR='${shot_dir}' node_modules/.bin/playwright test" \
      || finish
  else
    run_step "⑥ Playwright 端到端" "$FRONTEND_DIR" \
      "HTTP_PROXY= HTTPS_PROXY= NO_PROXY='*' E2E_SCREENSHOT_DIR='${shot_dir}' pnpm run e2e" \
      || finish
  fi

  if [ -n "$ITERATION" ]; then
    check_numbered_screenshots "$(resolve_iteration_dir)" || finish
  fi

  finish
}

# 输出汇总，并在指定迭代时生成报告文件
finish() {
  log_section "验证汇总"
  local i
  for i in "${!STEP_NAMES[@]}"; do
    if [ "${STEP_CODES[$i]}" -eq 0 ]; then
      printf '  ✓ %-20s 退出码 %s\n' "${STEP_NAMES[$i]}" "${STEP_CODES[$i]}"
    else
      printf '  ✗ %-20s 退出码 %s\n' "${STEP_NAMES[$i]}" "${STEP_CODES[$i]}"
    fi
  done

  local conclusion="通过"
  [ -n "$FAILED_STEP" ] && conclusion="不通过（阻塞步骤：$FAILED_STEP）"
  echo ""
  echo "结论：$conclusion"

  if [ -n "$ITERATION" ] && [ "$DOCS_ONLY" -eq 0 ]; then
    write_report "$conclusion"
  fi

  [ -n "$FAILED_STEP" ] && exit 1
  exit 0
}

# 当前迭代必须有 test-report/Sxx-*.png，且文件名出现在 test-report.md
check_numbered_screenshots() {
  local dir="$1"
  local report="$dir/test-report.md"
  local shot_dir="$dir/test-report"
  local log_file="$TMP_DIR/screenshot_gate.log"
  local issues=() png name base

  log_section "⑥b 编号截图归档"

  if [ ! -d "$shot_dir" ]; then
    issues+=("缺少截图目录：${shot_dir#$ROOT_DIR/}")
  else
    shopt -s nullglob
    local pngs=("$shot_dir"/S[0-9][0-9]-*.png)
    shopt -u nullglob
    if [ "${#pngs[@]}" -eq 0 ]; then
      issues+=("截图目录为空，需要 S01-<slug>.png 起的编号 png：${shot_dir#$ROOT_DIR/}")
    else
      if [ ! -f "$report" ]; then
        issues+=("缺少 test-report.md，无法引用截图")
      else
        for png in "${pngs[@]}"; do
          name="$(basename "$png")"
          base="${name%.png}"
          if ! grep -q "$base" "$report"; then
            issues+=("test-report.md 未引用截图 $name")
          fi
        done
        if ! grep -Eq 'S0[0-9]' "$report"; then
          issues+=("test-report.md 没有编号截图表（应出现 S01 等）")
        fi
      fi
    fi
  fi

  local code=0
  if [ "${#issues[@]}" -gt 0 ]; then
    code=1
    {
      echo "编号截图校验未通过："
      printf '  - %s\n' "${issues[@]}"
    } | tee "$log_file"
    FAILED_STEP="⑥b 编号截图归档"
    printf '\033[1;31m✗ 编号截图归档失败\033[0m\n'
  else
    echo "编号截图目录存在，且 test-report.md 已引用 Sxx 文件" | tee "$log_file"
    printf '\033[1;32m✓ 编号截图归档通过\033[0m\n'
  fi

  STEP_NAMES+=("⑥b 编号截图归档")
  STEP_CMDS+=("check test-report/Sxx-*.png vs test-report.md")
  STEP_CODES+=("$code")
  STEP_LOGS+=("$log_file")
  return "$code"
}

# 依据迭代编号前缀解析报告输出目录（FEAT-* → docs/features，BUG-* → docs/bug-fix）
resolve_iteration_dir() {
  case "$ITERATION" in
    FEAT-*) echo "$FEATURES_DIR/$ITERATION" ;;
    BUG-*)  echo "$BUGFIX_DIR/$ITERATION" ;;
    *)      echo "" ;;
  esac
}

# 生成 <迭代目录>/test-report.md 的自动化执行部分
write_report() {
  local conclusion="$1"
  local out_dir out_file rel_path
  out_dir="$(resolve_iteration_dir)"

  if [ -z "$out_dir" ]; then
    echo "迭代编号不合规：$ITERATION（应为 FEAT-<3位>-<slug> 或 BUG-<3位>-<slug>），跳过报告生成" >&2
    FAILED_STEP="${FAILED_STEP:-报告生成}"
    return 1
  fi
  if [ ! -d "$out_dir" ]; then
    echo "迭代目录不存在：${out_dir#$ROOT_DIR/}，请先按 04 流程创建 spec.md / plan.md / checklist.md" >&2
    FAILED_STEP="${FAILED_STEP:-报告生成}"
    return 1
  fi

  out_file="$out_dir/test-report.md"
  rel_path="${out_file#$ROOT_DIR/}"

  {
    echo "# 测试验证报告：$ITERATION"
    echo ""
    echo "> 本文件的「自动化执行结果」由 scripts/verify.sh 生成，其余章节请依据"
    echo "> docs/templates/test-report-template.md 手工补全（验收对照、异常场景、缺陷清单等）。"
    echo ""
    echo "## 1. 报告信息"
    echo ""
    echo "| 项 | 内容 |"
    echo "|----|------|"
    echo "| 迭代编号 | \`$ITERATION\` |"
    echo "| 执行日期 | $(date '+%Y-%m-%d %H:%M:%S') |"
    echo "| 执行方式 | scripts/verify.sh |"
    echo "| 自动化结论 | $conclusion |"
    echo ""
    echo "## 2. 环境信息"
    echo ""
    echo "| 项 | 值 |"
    echo "|----|-----|"
    echo "| Node | $(node -v 2>/dev/null || echo 未安装) |"
    echo "| pnpm | $(pnpm -v 2>/dev/null || echo 未安装) |"
    echo "| Python | $(python -V 2>&1 || echo 未安装) |"
    echo ""
    echo "## 3. 自动化执行结果"
    echo ""
    echo "| 步骤 | 命令 | 退出码 | 结果 |"
    echo "|------|------|--------|------|"
    local i mark
    for i in "${!STEP_NAMES[@]}"; do
      mark="✅"
      [ "${STEP_CODES[$i]}" -ne 0 ] && mark="❌"
      echo "| ${STEP_NAMES[$i]} | \`${STEP_CMDS[$i]}\` | ${STEP_CODES[$i]} | $mark |"
    done
    echo ""
    echo "### 关键输出摘要"
    echo ""
    for i in "${!STEP_NAMES[@]}"; do
      echo "#### ${STEP_NAMES[$i]}"
      echo ""
      echo '```text'
      tail -n "$SUMMARY_LINES" "${STEP_LOGS[$i]}" 2>/dev/null || echo "(无输出)"
      echo '```'
      echo ""
    done
    echo "## 4. 人工补全章节"
    echo ""
    echo "- 测试用例统计与新增/回归用例清单"
    echo "- 验收标准（AC）逐条对照"
    echo "- 异常场景验证结果"
    echo "- 关键旅程走查结果"
    echo "- 缺陷清单与遗留风险"
    echo "- 规范符合性核对（01 / 02 / 03 / 06 / 07）"
    echo "- 最终结论（通过 / 有条件通过 / 不通过）"
  } > "$out_file"

  echo "报告已生成：$rel_path"
}

parse_args "$@"
main