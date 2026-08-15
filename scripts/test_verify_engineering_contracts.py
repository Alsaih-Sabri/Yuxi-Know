"""Owner 派生工程信任 verifier 的负向测试。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.verify_engineering_contracts import verify


class EngineeringContractVerifierTest(unittest.TestCase):
    """证明 verifier 会从真实 Owner 检查接线与架构边界。"""

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self._write("owner.md", "owner\n")
        self._write(
            "backend/server/routers/valid_router.py",
            "async def route():\n    return None\n",
        )
        self._write(
            "web/src/components/ValidComponent.vue",
            "<template><div>ok</div></template>\n",
        )
        for lifecycle in ("proposed", "implemented", "rejected", "archived"):
            (self.root / "docs/develop-guides/decisions" / lifecycle).mkdir(
                parents=True
            )
        self._write(
            "docs/develop-guides/decisions/implemented/2026-08-15-valid-decision.md",
            """# 有效决策

状态：implemented
Owner：owner.md

## 问题
工程事实需要稳定的语义 Owner。

## 决策
从真实 Owner 派生审计视图。

## 替代方案
拒绝手工维护第二份中央清单。

## 后果
Owner 与 gate 必须在同一变更中保持一致。

## 验证
运行 verifier 及其负向测试。
""",
        )
        self._write_valid_workflows()

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write(self, relative: str, content: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _write_valid_workflows(self) -> None:
        self._write(
            ".github/workflows/trust.yml",
            """on:
  pull_request:
jobs:
  verify:
    steps:
      - run: python3 scripts/verify_engineering_contracts.py
      - run: python3 -m unittest scripts.test_verify_engineering_contracts
""",
        )
        self._write(
            ".github/workflows/test.yml",
            """on:
  pull_request:
    paths:
      - '.env.template'
      - 'backend/**'
      - 'scripts/init.sh'
      - 'scripts/init.ps1'
      - 'scripts/test_init_security.ps1'
      - '.github/workflows/test.yml'
jobs:
  unit:
    steps:
      - run: uv run pytest test/unit -m 'not slow' -q
  powershell:
    steps:
      - run: pwsh -NoProfile -File scripts/test_init_security.ps1
""",
        )
        self._write(
            ".github/workflows/web.yml",
            """on:
  pull_request:
    paths:
      - 'web/**'
      - '.github/workflows/web.yml'
jobs:
  web:
    steps:
      - run: pnpm run lint:check && pnpm run test:unit && pnpm run build
""",
        )
        self._write(
            ".github/workflows/system-tests.yml",
            """on:
  pull_request:
    paths:
      - 'backend/package/yuxi/**'
      - 'backend/server/**'
      - 'backend/test/integration/**'
      - '.github/workflows/system-tests.yml'
jobs:
  system:
    steps:
      - run: docker compose exec -T api uv run pytest test/integration/api/test_system_router_api.py::test_health_endpoint_is_public test/integration/api/test_system_router_api.py::test_readiness_endpoint_proves_core_runtime_dependencies test/integration/api/test_system_router_api.py::test_discovery_declares_cli_knowledge_capabilities test/integration/api/test_system_router_api.py::test_lite_startup_does_not_create_knowledge_schema -q
      - run: docker compose exec -T api uv run pytest test/integration/services/test_agent_request_queue_concurrency.py -q
      - run: docker compose exec -T api uv run pytest test/integration/services/test_agent_run_lease.py -q
      - run: docker compose exec -T api uv run pytest test/integration/api/test_agent_run_result_causality.py -q
      - run: docker compose exec -T api uv run pytest test/integration/services/test_identity_admin_service.py test/integration/services/test_api_key_schema_migration.py test/integration/services/test_api_key_user_lifecycle.py test/integration/api/test_apikey_router.py -q
""",
        )

    def _errors(self) -> list[str]:
        return verify(self.root)[0]

    def test_valid_repository_passes(self) -> None:
        self.assertEqual(self._errors(), [])

    def test_central_claim_inventory_is_rejected(self) -> None:
        self._write("docs/develop-guides/engineering-claims.json", "{}\n")

        self.assertTrue(
            any("禁止手工中央主张清单" in error for error in self._errors())
        )

    def test_decision_missing_heading_is_rejected(self) -> None:
        path = (
            self.root
            / "docs/develop-guides/decisions/implemented/2026-08-15-valid-decision.md"
        )
        path.write_text(
            path.read_text(encoding="utf-8").replace("## 问题", "## 背景"),
            encoding="utf-8",
        )

        self.assertTrue(any("缺少标题：## 问题" in error for error in self._errors()))

    def test_decision_missing_owner_is_rejected(self) -> None:
        path = (
            self.root
            / "docs/develop-guides/decisions/implemented/2026-08-15-valid-decision.md"
        )
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "Owner：owner.md", "Owner：missing.md"
            ),
            encoding="utf-8",
        )

        self.assertTrue(any("Owner 引用不存在" in error for error in self._errors()))

    def test_decision_owner_symlink_cannot_escape_repository(self) -> None:
        (self.root / "outside-owner").symlink_to("/etc/hosts")
        path = (
            self.root
            / "docs/develop-guides/decisions/implemented/2026-08-15-valid-decision.md"
        )
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "Owner：owner.md", "Owner：outside-owner"
            ),
            encoding="utf-8",
        )

        self.assertTrue(any("符号链接逃逸仓库" in error for error in self._errors()))

    def test_implemented_progress_heading_is_rejected(self) -> None:
        path = (
            self.root
            / "docs/develop-guides/decisions/implemented/2026-08-15-valid-decision.md"
        )
        path.write_text(
            path.read_text(encoding="utf-8") + "\n## 进度\n已完成。\n", encoding="utf-8"
        )

        self.assertTrue(
            any("不能保留提案或进度标题" in error for error in self._errors())
        )

    def test_heading_in_code_fence_does_not_count(self) -> None:
        path = (
            self.root
            / "docs/develop-guides/decisions/implemented/2026-08-15-valid-decision.md"
        )
        text = path.read_text(encoding="utf-8").replace(
            "## 验证\n运行 verifier 及其负向测试。",
            "```markdown\n## 验证\n伪造内容。\n```",
        )
        path.write_text(text, encoding="utf-8")

        self.assertTrue(any("缺少标题：## 验证" in error for error in self._errors()))

    def test_workflow_command_drift_is_rejected(self) -> None:
        path = self.root / ".github/workflows/trust.yml"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "python3 scripts/verify_engineering_contracts.py",
                "python3 scripts/other.py",
            ),
            encoding="utf-8",
        )

        self.assertTrue(any("缺少实际 run step" in error for error in self._errors()))

    def test_comment_cannot_impersonate_workflow_run_step(self) -> None:
        path = self.root / ".github/workflows/trust.yml"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "- run: python3 scripts/verify_engineering_contracts.py",
                "# run: python3 scripts/verify_engineering_contracts.py",
            ),
            encoding="utf-8",
        )

        self.assertTrue(any("缺少实际 run step" in error for error in self._errors()))

    def test_conditionally_skipped_step_is_rejected(self) -> None:
        path = self.root / ".github/workflows/trust.yml"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "- run: python3 scripts/verify_engineering_contracts.py",
                "- if: ${{ false }}\n        run: python3 scripts/verify_engineering_contracts.py",
            ),
            encoding="utf-8",
        )

        self.assertTrue(any("被跳过或吞错" in error for error in self._errors()))

    def test_continue_on_error_step_is_rejected(self) -> None:
        path = self.root / ".github/workflows/trust.yml"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "- run: python3 scripts/verify_engineering_contracts.py",
                "- continue-on-error: true\n        run: python3 scripts/verify_engineering_contracts.py",
            ),
            encoding="utf-8",
        )

        self.assertTrue(any("被跳过或吞错" in error for error in self._errors()))

    def test_conditionally_skipped_job_is_rejected(self) -> None:
        path = self.root / ".github/workflows/trust.yml"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "  verify:\n    steps:",
                "  verify:\n    if: github.actor == 'trusted-only'\n    steps:",
            ),
            encoding="utf-8",
        )

        self.assertTrue(any("被跳过或吞错" in error for error in self._errors()))

    def test_gate_command_cannot_swallow_failure(self) -> None:
        path = self.root / ".github/workflows/trust.yml"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "python3 scripts/verify_engineering_contracts.py",
                "python3 scripts/verify_engineering_contracts.py || true",
            ),
            encoding="utf-8",
        )

        self.assertTrue(any("吞掉失败" in error for error in self._errors()))

    def test_trust_workflow_cannot_narrow_pull_request_paths(self) -> None:
        path = self.root / ".github/workflows/trust.yml"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "pull_request:\n", "pull_request:\n    paths: ['scripts/**']\n"
            ),
            encoding="utf-8",
        )

        self.assertTrue(
            any(
                "全仓信任 workflow 不得使用 path filter" in error
                for error in self._errors()
            )
        )

    def test_backend_unit_selector_cannot_drift_to_marker(self) -> None:
        path = self.root / ".github/workflows/test.yml"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "test/unit -m 'not slow'", "test -m unit"
            ),
            encoding="utf-8",
        )

        self.assertTrue(any("缺少实际 run step" in error for error in self._errors()))

    def test_backend_workflow_cannot_ignore_initialization_contract_changes(
        self,
    ) -> None:
        path = self.root / ".github/workflows/test.yml"
        path.write_text(
            path.read_text(encoding="utf-8").replace("      - 'scripts/init.sh'\n", ""),
            encoding="utf-8",
        )

        self.assertTrue(
            any(
                "workflow PR paths 缺少 owning scope" in error
                for error in self._errors()
            )
        )

    def test_powershell_security_gate_cannot_be_removed(self) -> None:
        path = self.root / ".github/workflows/test.yml"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "pwsh -NoProfile -File scripts/test_init_security.ps1",
                "pwsh -NoProfile -File scripts/other.ps1",
            ),
            encoding="utf-8",
        )

        self.assertTrue(any("缺少实际 run step" in error for error in self._errors()))

    def test_system_workflow_cannot_narrow_owning_paths(self) -> None:
        path = self.root / ".github/workflows/system-tests.yml"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "      - 'backend/package/yuxi/**'\n", ""
            ),
            encoding="utf-8",
        )

        self.assertTrue(
            any(
                "workflow PR paths 缺少 owning scope" in error
                for error in self._errors()
            )
        )

    def test_router_sqlalchemy_query_builder_is_rejected(self) -> None:
        self._write(
            "backend/server/routers/invalid_router.py",
            "from sqlalchemy import select\n",
        )

        self.assertTrue(
            any(
                "router 不得拥有 SQLAlchemy query builder" in error
                for error in self._errors()
            )
        )

    def test_router_execute_and_delete_are_rejected(self) -> None:
        self._write(
            "backend/server/routers/invalid_router.py",
            """async def route(db, user):
    await db.execute('query')
    await db.delete(user)
""",
        )

        errors = self._errors()
        self.assertTrue(any("db.execute" in error for error in errors))
        self.assertTrue(any("db.delete" in error for error in errors))

    def test_web_api_literal_outside_api_owner_is_rejected(self) -> None:
        self._write(
            "web/src/components/InvalidComponent.vue",
            "<script>fetch('/api/users')</script>\n",
        )

        self.assertTrue(
            any(
                "web/src/apis 外不得拥有 /api 路径" in error for error in self._errors()
            )
        )

    def test_projection_is_derived_from_current_owners(self) -> None:
        errors, projection = verify(self.root)

        self.assertEqual(errors, [])
        self.assertTrue(projection["derived"])
        self.assertEqual(
            projection["decisions"],
            [
                {
                    "path": "docs/develop-guides/decisions/implemented/2026-08-15-valid-decision.md",
                    "status": "implemented",
                    "owner": "owner.md",
                }
            ],
        )
        self.assertEqual(
            {workflow["path"] for workflow in projection["workflows"]},
            {
                ".github/workflows/trust.yml",
                ".github/workflows/test.yml",
                ".github/workflows/web.yml",
                ".github/workflows/system-tests.yml",
            },
        )


if __name__ == "__main__":
    unittest.main()
