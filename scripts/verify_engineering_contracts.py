"""从真实 Owner 派生工程信任检查，不维护中央主张清单。"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DECISIONS_PATH = Path("docs/develop-guides/decisions")
FORBIDDEN_CENTRAL_INVENTORIES = (Path("docs/develop-guides/engineering-claims.json"),)
DECISION_FILE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9][a-z0-9-]*\.md$")
DECISION_REQUIRED_HEADINGS = {
    "implemented": ("## 问题", "## 决策", "## 替代方案", "## 后果", "## 验证"),
    "proposed": ("## 问题", "## 提案", "## 替代方案", "## 验收标准", "## 风险"),
    "rejected": ("## 问题", "## 提案", "## 替代方案", "## 拒绝理由"),
    "archived": ("## 问题", "## 决策", "## 替代方案", "## 后果", "## 验证"),
}
IMPLEMENTED_BANNED_HEADINGS = (
    "## 提案",
    "## 实施步骤",
    "## 迁移步骤",
    "## Checklist",
    "## 进度",
)
ROUTER_DB_METHODS = frozenset(
    {
        "execute",
        "scalar",
        "scalars",
        "get",
        "add",
        "add_all",
        "delete",
        "flush",
        "merge",
    }
)
ROUTER_DB_RECEIVERS = frozenset({"db", "session", "connection", "database"})
DIRECT_WEB_API_LITERAL = re.compile(r"(?P<quote>['\"`])/api(?:[/ ?]|(?P=quote))")


@dataclass(frozen=True)
class WorkflowContract:
    """由 workflow 文件自身拥有的最小可执行接线要求。"""

    path: str
    commands: tuple[str, ...]
    required_paths: tuple[str, ...] = ()
    unfiltered_pull_request: bool = False


WORKFLOW_CONTRACTS = (
    WorkflowContract(
        path=".github/workflows/trust.yml",
        commands=(
            "python3 scripts/verify_engineering_contracts.py",
            "python3 -m unittest scripts.test_verify_engineering_contracts",
        ),
        unfiltered_pull_request=True,
    ),
    WorkflowContract(
        path=".github/workflows/test.yml",
        commands=(
            "uv run pytest test/unit -m 'not slow' -q",
            "pwsh -NoProfile -File scripts/test_init_security.ps1",
        ),
        required_paths=(
            ".env.template",
            "backend/**",
            "scripts/init.sh",
            "scripts/init.ps1",
            "scripts/test_init_security.ps1",
            ".github/workflows/test.yml",
        ),
    ),
    WorkflowContract(
        path=".github/workflows/web.yml",
        commands=("pnpm run lint:check && pnpm run test:unit && pnpm run build",),
        required_paths=("web/**", ".github/workflows/web.yml"),
    ),
    WorkflowContract(
        path=".github/workflows/system-tests.yml",
        commands=(
            "docker compose exec -T api uv run pytest test/integration/api/test_system_router_api.py::test_health_endpoint_is_public test/integration/api/test_system_router_api.py::test_readiness_endpoint_proves_core_runtime_dependencies test/integration/api/test_system_router_api.py::test_discovery_declares_cli_knowledge_capabilities test/integration/api/test_system_router_api.py::test_lite_startup_does_not_create_knowledge_schema -q",
            "docker compose exec -T api uv run pytest test/integration/services/test_agent_request_queue_concurrency.py -q",
            "docker compose exec -T api uv run pytest test/integration/services/test_agent_run_lease.py -q",
            "docker compose exec -T api uv run pytest test/integration/api/test_agent_run_result_causality.py -q",
            "docker compose exec -T api uv run pytest test/integration/services/test_identity_admin_service.py test/integration/services/test_api_key_schema_migration.py test/integration/services/test_api_key_user_lifecycle.py test/integration/api/test_apikey_router.py -q",
        ),
        required_paths=(
            "backend/package/yuxi/**",
            "backend/server/**",
            "backend/test/integration/**",
            ".github/workflows/system-tests.yml",
        ),
    ),
)


def _require_repository_path(
    root: Path,
    raw_path: object,
    label: str,
    errors: list[str],
    *,
    file_only: bool = False,
) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        errors.append(f"{label} 必须是非空仓库相对路径")
        return None
    path = Path(raw_path)
    if path.is_absolute() or ".." in path.parts:
        errors.append(f"{label} 必须位于仓库内：{raw_path}")
        return None
    resolved = root / path
    if not resolved.resolve().is_relative_to(root.resolve()):
        errors.append(f"{label} 不得通过符号链接逃逸仓库：{raw_path}")
        return None
    if not resolved.exists():
        errors.append(f"{label} 引用不存在：{raw_path}")
        return None
    if file_only and not resolved.is_file():
        errors.append(f"{label} 必须引用文件：{raw_path}")
        return None
    return resolved


def _normalized(text: str) -> str:
    return " ".join(text.split())


def _yaml_scalar(value: str) -> str:
    return value.strip().strip("'\"").strip()


def _literal_expression(value: str, expected: str) -> bool:
    normalized = _yaml_scalar(value).lower()
    if normalized.startswith("${{") and normalized.endswith("}}"):
        normalized = normalized[3:-2].strip()
    return normalized == expected


def _workflow_run_steps(text: str) -> list[dict[str, str]]:
    """提取真实 ``run`` step，以及 step/job 层的条件和吞错配置。"""

    lines = text.splitlines()
    steps: list[dict[str, str]] = []
    index = 0
    while index < len(lines):
        match = re.match(r"^(\s*)(-\s+)?run:\s*(.*?)\s*$", lines[index])
        if not match:
            index += 1
            continue

        run_index = index
        list_item = match.group(2) is not None
        indentation = len(match.group(1)) + (2 if list_item else 0)
        value = match.group(3)
        if value in {"|", "|-", "|+", ">", ">-", ">+"}:
            index += 1
            block_lines: list[str] = []
            while index < len(lines):
                line = lines[index]
                if line.strip() and len(line) - len(line.lstrip()) <= indentation:
                    break
                block_lines.append(line.strip())
                index += 1
            command = "\n".join(block_lines)
        else:
            command = _yaml_scalar(value) if value else ""
            index += 1

        step_start = run_index
        step_indent: int | None = len(match.group(1)) if list_item else None
        if not list_item:
            for candidate in range(run_index - 1, -1, -1):
                line = lines[candidate]
                if not line.strip():
                    continue
                candidate_indent = len(line) - len(line.lstrip())
                if candidate_indent < indentation and line.lstrip().startswith("- "):
                    step_start = candidate
                    step_indent = candidate_indent
                    break
                if candidate_indent < indentation and line.lstrip().endswith(":"):
                    break

        step_end = index
        if step_indent is not None:
            step_end = len(lines)
            for candidate in range(index, len(lines)):
                line = lines[candidate]
                if not line.strip():
                    continue
                candidate_indent = len(line) - len(line.lstrip())
                if candidate_indent < step_indent or (
                    candidate_indent == step_indent and line.lstrip().startswith("- ")
                ):
                    step_end = candidate
                    break

        options: dict[str, str] = {"command": command}
        for line in lines[step_start:step_end]:
            content = line.lstrip()
            effective_indentation = len(line) - len(content)
            if content.startswith("- "):
                content = content[2:]
                effective_indentation += 2
            option = (
                re.match(r"^(if|continue-on-error):\s*(.*?)\s*$", content)
                if effective_indentation == indentation
                else None
            )
            if option:
                options[option.group(1)] = option.group(2)

        jobs_index: int | None = None
        jobs_indent = 0
        for candidate in range(run_index - 1, -1, -1):
            jobs_match = re.match(r"^(\s*)jobs:\s*$", lines[candidate])
            if jobs_match:
                jobs_index = candidate
                jobs_indent = len(jobs_match.group(1))
                break
        if jobs_index is not None:
            job_indent: int | None = None
            job_start: int | None = None
            for candidate in range(jobs_index + 1, run_index):
                line = lines[candidate]
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                candidate_indent = len(line) - len(line.lstrip())
                if candidate_indent <= jobs_indent:
                    break
                if job_indent is None:
                    job_indent = candidate_indent
                if candidate_indent == job_indent and re.match(
                    r"^\s*[^:#][^:]*:\s*(?:#.*)?$", line
                ):
                    job_start = candidate
            if job_start is not None and job_indent is not None:
                property_indent = job_indent + 2
                for line in lines[job_start + 1 : run_index]:
                    option = re.match(
                        rf"^\s{{{property_indent}}}(if|continue-on-error):\s*(.*?)\s*$",
                        line,
                    )
                    if option:
                        options[f"job-{option.group(1)}"] = option.group(2)
        steps.append(options)
    return steps


def _run_step_is_blocking(step: dict[str, str]) -> bool:
    if step.get("if") or step.get("job-if"):
        return False
    for key in ("continue-on-error", "job-continue-on-error"):
        value = step.get(key)
        if value and not _literal_expression(value, "false"):
            return False
    return True


def _command_swallows_failure(command: str) -> bool:
    normalized = _normalized(command)
    return bool(
        re.search(r"(?:\|\||;)\s*(?:true|:)(?:\s|$)", normalized)
        or re.search(r"(?:^|[;&])\s*set\s+\+e(?:\s|$)", normalized)
        or re.search(r"(?:^|[;&])\s*exit\s+0(?:\s|$)", normalized)
    )


def _inline_yaml_list(value: str) -> list[str] | None:
    normalized = value.strip()
    if not (normalized.startswith("[") and normalized.endswith("]")):
        return None
    inner = normalized[1:-1].strip()
    if not inner:
        return []
    return [_yaml_scalar(item) for item in inner.split(",") if _yaml_scalar(item)]


def _workflow_pull_request_filters(
    text: str,
) -> tuple[bool, list[str] | None, list[str]]:
    """返回是否监听 PR，以及 paths / paths-ignore。"""

    lines = text.splitlines()
    on_index: int | None = None
    on_indent = 0
    on_value = ""
    for index, line in enumerate(lines):
        match = re.match(r"^(\s*)on:\s*(.*?)\s*$", line)
        if match:
            on_index = index
            on_indent = len(match.group(1))
            on_value = match.group(2)
            break
    if on_index is None:
        return False, None, []
    if on_value:
        inline_events = _inline_yaml_list(on_value)
        if inline_events is not None:
            return "pull_request" in inline_events, None, []
        return _yaml_scalar(on_value) == "pull_request", None, []

    block_end = len(lines)
    for index in range(on_index + 1, len(lines)):
        line = lines[index]
        if line.strip() and len(line) - len(line.lstrip()) <= on_indent:
            block_end = index
            break

    event_index: int | None = None
    event_indent: int | None = None
    event_value = ""
    for index in range(on_index + 1, block_end):
        match = re.match(r"^(\s*)pull_request:\s*(.*?)\s*$", lines[index])
        if match:
            event_index = index
            event_indent = len(match.group(1))
            event_value = match.group(2)
            break
    if event_index is None or event_indent is None:
        return False, None, []
    if event_value and _yaml_scalar(event_value) not in {"", "{}", "null", "~"}:
        return True, [], []

    event_end = block_end
    for index in range(event_index + 1, block_end):
        line = lines[index]
        if line.strip() and len(line) - len(line.lstrip()) <= event_indent:
            event_end = index
            break

    def read_filter(name: str) -> tuple[bool, list[str]]:
        for filter_index in range(event_index + 1, event_end):
            match = re.match(
                rf"^(\s*){re.escape(name)}:\s*(.*?)\s*$", lines[filter_index]
            )
            if not match or len(match.group(1)) <= event_indent:
                continue
            value = match.group(2)
            inline = _inline_yaml_list(value)
            if inline is not None:
                return True, inline
            if value:
                return True, [_yaml_scalar(value)]

            filter_indent = len(match.group(1))
            patterns: list[str] = []
            for item_index in range(filter_index + 1, event_end):
                line = lines[item_index]
                if not line.strip():
                    continue
                item_indent = len(line) - len(line.lstrip())
                if item_indent <= filter_indent:
                    break
                item = re.match(r"^\s*-\s*(.*?)\s*$", line)
                if item and _yaml_scalar(item.group(1)):
                    patterns.append(_yaml_scalar(item.group(1)))
            return True, patterns
        return False, []

    has_paths, paths = read_filter("paths")
    _, paths_ignore = read_filter("paths-ignore")
    return True, paths if has_paths else None, paths_ignore


def _validate_workflows(root: Path, errors: list[str]) -> list[dict[str, Any]]:
    projection: list[dict[str, Any]] = []
    for contract in WORKFLOW_CONTRACTS:
        workflow = _require_repository_path(
            root, contract.path, "workflow", errors, file_only=True
        )
        if workflow is None:
            continue
        text = workflow.read_text(encoding="utf-8")
        steps = _workflow_run_steps(text)
        for command in contract.commands:
            if _command_swallows_failure(command):
                errors.append(
                    f"workflow contract 不得登记吞错命令：{contract.path} -> {command}"
                )
            normalized_command = _normalized(command)
            matching = [
                step
                for step in steps
                if _normalized(step["command"]) == normalized_command
            ]
            if not matching:
                swallowing = [
                    step
                    for step in steps
                    if normalized_command in _normalized(step["command"])
                    and _command_swallows_failure(step["command"])
                ]
                if swallowing:
                    errors.append(
                        f"workflow 命令不得吞掉失败：{contract.path} -> {command}"
                    )
                else:
                    errors.append(
                        f"workflow 缺少实际 run step：{contract.path} -> {command}"
                    )
            elif not any(_run_step_is_blocking(step) for step in matching):
                errors.append(
                    f"workflow 命令只存在于被跳过或吞错的 step：{contract.path} -> {command}"
                )

        has_pr, paths, paths_ignore = _workflow_pull_request_filters(text)
        if not has_pr:
            errors.append(f"workflow 不监听 pull_request：{contract.path}")
        if contract.unfiltered_pull_request and (paths is not None or paths_ignore):
            errors.append(f"全仓信任 workflow 不得使用 path filter：{contract.path}")
        if paths_ignore:
            errors.append(
                f"阻断 workflow 不得用 paths-ignore 隐藏变更：{contract.path}"
            )
        if contract.required_paths:
            actual_paths = set(paths or [])
            missing_paths = sorted(set(contract.required_paths) - actual_paths)
            if missing_paths:
                errors.append(
                    f"workflow PR paths 缺少 owning scope：{contract.path} -> {missing_paths}"
                )
        projection.append(
            {
                "path": contract.path,
                "pull_request_paths": paths,
                "commands": [step["command"] for step in steps],
            }
        )
    return projection


def _visible_markdown_lines(text: str) -> list[str]:
    visible: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        marker = line.lstrip()[:3]
        if marker in {"```", "~~~"}:
            fence = None if fence == marker else marker if fence is None else fence
            continue
        if fence is None:
            visible.append(line)
    return visible


def _metadata(lines: list[str], label: str) -> str | None:
    for line in lines:
        if line.startswith(label):
            return line.removeprefix(label).strip()
    return None


def _decision_sections(lines: list[str]) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in lines:
        if line.startswith("## "):
            current = line.strip()
            sections.setdefault(current, [])
        elif current is not None:
            sections[current].append(line)
    return sections


def _validate_decisions(root: Path, errors: list[str]) -> list[dict[str, str]]:
    decisions_root = root / DECISIONS_PATH
    projection: list[dict[str, str]] = []
    if not decisions_root.is_dir():
        errors.append(f"缺少决策记录目录：{DECISIONS_PATH}")
        return projection

    for lifecycle, headings in DECISION_REQUIRED_HEADINGS.items():
        lifecycle_dir = decisions_root / lifecycle
        if not lifecycle_dir.is_dir():
            errors.append(f"缺少决策 lifecycle 目录：{lifecycle_dir.relative_to(root)}")
            continue
        for path in sorted(lifecycle_dir.glob("*.md")):
            relative = path.relative_to(root)
            if not DECISION_FILE_PATTERN.fullmatch(path.name):
                errors.append(f"决策记录文件名必须是 YYYY-MM-DD-topic.md：{relative}")
            lines = _visible_markdown_lines(path.read_text(encoding="utf-8"))
            sections = _decision_sections(lines)
            status = _metadata(lines, "状态：")
            if status != lifecycle:
                errors.append(f"{relative} 状态必须是 {lifecycle}，实际为 {status!r}")
            owner = _metadata(lines, "Owner：")
            _require_repository_path(
                root, owner, f"{relative} Owner", errors, file_only=True
            )
            for heading in headings:
                if heading not in sections:
                    errors.append(f"{relative} 缺少标题：{heading}")
                elif not any(
                    line.strip() and not line.lstrip().startswith("<!--")
                    for line in sections[heading]
                ):
                    errors.append(f"{relative} 标题下没有内容：{heading}")
            if lifecycle in {"implemented", "archived"}:
                for heading in IMPLEMENTED_BANNED_HEADINGS:
                    if heading in sections:
                        errors.append(
                            f"当前/归档记录不能保留提案或进度标题：{relative} -> {heading}"
                        )
            projection.append(
                {
                    "path": str(relative),
                    "status": status or "missing",
                    "owner": owner or "missing",
                }
            )
    if not projection:
        errors.append("至少需要一份 tracked decision record")
    return projection


def _attribute_root_name(node: ast.expr) -> str | None:
    while isinstance(node, ast.Attribute):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def _validate_router_boundaries(root: Path, errors: list[str]) -> int:
    routers_root = root / "backend/server/routers"
    checked = 0
    for path in sorted(routers_root.rglob("*.py")):
        checked += 1
        relative = path.relative_to(root)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(relative))
        except SyntaxError as exc:
            errors.append(f"router 无法解析：{relative}:{exc.lineno} {exc.msg}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                modules = (
                    [alias.name for alias in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module or ""]
                )
                if not any(
                    module == "sqlalchemy" or module.startswith("sqlalchemy.")
                    for module in modules
                ):
                    continue
                allowed_async_session = (
                    isinstance(node, ast.ImportFrom)
                    and node.module == "sqlalchemy.ext.asyncio"
                    and {alias.name for alias in node.names} <= {"AsyncSession"}
                )
                if not allowed_async_session:
                    errors.append(
                        f"router 不得拥有 SQLAlchemy query builder：{relative}:{node.lineno}"
                    )
            if not isinstance(node, ast.Call) or not isinstance(
                node.func, ast.Attribute
            ):
                continue
            receiver = _attribute_root_name(node.func.value)
            if receiver in ROUTER_DB_RECEIVERS and node.func.attr in ROUTER_DB_METHODS:
                errors.append(
                    f"router 不得直接执行持久化操作：{relative}:{node.lineno} -> {receiver}.{node.func.attr}"
                )
    return checked


def _validate_web_api_boundary(root: Path, errors: list[str]) -> int:
    source_root = root / "web/src"
    checked = 0
    for path in sorted(source_root.rglob("*")):
        if not path.is_file() or path.suffix not in {".js", ".ts", ".vue"}:
            continue
        if (source_root / "apis") in path.parents:
            continue
        checked += 1
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if DIRECT_WEB_API_LITERAL.search(line):
                errors.append(
                    f"web/src/apis 外不得拥有 /api 路径：{path.relative_to(root)}:{line_number}"
                )
    return checked


def verify(root: Path) -> tuple[list[str], dict[str, Any]]:
    """验证 Owner-local 契约，并返回按需派生的审计投影。"""

    resolved_root = root.resolve()
    errors: list[str] = []
    for forbidden in FORBIDDEN_CENTRAL_INVENTORIES:
        if (resolved_root / forbidden).exists():
            errors.append(
                f"禁止手工中央主张清单；主张必须在语义 Owner 处闭合：{forbidden}"
            )
    decisions = _validate_decisions(resolved_root, errors)
    workflows = _validate_workflows(resolved_root, errors)
    router_files = _validate_router_boundaries(resolved_root, errors)
    web_files = _validate_web_api_boundary(resolved_root, errors)
    projection = {
        "derived": True,
        "authority": "owner-local code, tests, decisions and workflows",
        "decisions": decisions,
        "workflows": workflows,
        "boundaries": {
            "router_files_checked": router_files,
            "web_source_files_checked": web_files,
        },
    }
    return errors, projection


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        action="store_true",
        help="打印从当前 Owner 派生的临时 JSON 审计视图",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    errors, projection = verify(root)
    if args.report:
        print(json.dumps(projection, ensure_ascii=False, indent=2))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"工程信任检查失败：{len(errors)} 个问题", file=sys.stderr)
        return 1
    if not args.report:
        print(
            "工程信任检查通过："
            f"{len(projection['decisions'])} decisions / "
            f"{len(projection['workflows'])} workflows / "
            f"{projection['boundaries']['router_files_checked']} routers / "
            f"{projection['boundaries']['web_source_files_checked']} web sources"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
