from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


ALLOWED_COMMANDS = {
    "pwd",
    "df",
    "free",
    "git",
    "cat",
}

ALLOWED_GIT_SUBCOMMANDS = {"status", "rev-parse", "log", "diff", "branch"}
ALLOWED_ABSOLUTE_READ_PATHS = {"/proc/loadavg"}

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ActionPlan:
    action: str
    command: str


class TerminalActionExecutor:
    def execute(
        self,
        action: str,
        params: Dict[str, Any] | None = None,
        *,
        timeout_seconds: int = 20,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        payload = params or {}
        plan = self._build_plan(action, payload)

        if dry_run:
            return {
                "action": plan.action,
                "command": plan.command,
                "success": True,
                "stdout": "[DRY-RUN]",
                "stderr": "",
                "return_code": 0,
                "timed_out": False,
                "root_cause": None,
            }

        result = self._run_safe(plan.command, timeout_seconds=timeout_seconds)
        return {
            "action": plan.action,
            "command": plan.command,
            "success": result["return_code"] == 0,
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "return_code": result["return_code"],
            "timed_out": result["timed_out"],
            "root_cause": self._diagnose(result),
        }

    def _build_plan(self, action: str, params: Dict[str, Any]) -> ActionPlan:
        if action == "check_disk":
            return ActionPlan(action="check_disk", command="df -h")

        if action == "check_memory":
            return ActionPlan(action="check_memory", command="free -m")

        if action == "check_cpu":
            return ActionPlan(action="check_cpu", command="cat /proc/loadavg")

        if action == "git_status":
            return ActionPlan(action="git_status", command="git status --short --branch")

        if action == "pwd":
            return ActionPlan(action="pwd", command="pwd")

        raise ValueError(f"Ação não suportada: {action}")

    def _run_safe(self, cmd: str, timeout_seconds: int) -> Dict[str, Any]:
        tokens = shlex.split(cmd)
        if not tokens:
            raise ValueError("Comando vazio")

        base = tokens[0]
        if base not in ALLOWED_COMMANDS:
            raise ValueError(f"Comando não permitido: {base}")

        if base == "git":
            if len(tokens) < 2 or tokens[1] not in ALLOWED_GIT_SUBCOMMANDS:
                raise ValueError("Subcomando git não permitido")

        if base == "cat":
            if len(tokens) != 2:
                raise ValueError("Uso de cat não permitido")
            target = Path(tokens[1])
            if target.is_absolute():
                if str(target) not in ALLOWED_ABSOLUTE_READ_PATHS:
                    raise ValueError("Path absoluto não permitido")
            else:
                resolved = (PROJECT_ROOT / target).resolve()
                try:
                    resolved.relative_to(PROJECT_ROOT.resolve())
                except ValueError as exc:
                    raise ValueError("Path fora do projeto") from exc

        try:
            proc = subprocess.run(
                tokens,
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                shell=False,
            )
            return {
                "return_code": proc.returncode,
                "stdout": proc.stdout[:20000],
                "stderr": proc.stderr[:20000],
                "timed_out": False,
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "return_code": 124,
                "stdout": (exc.stdout or "")[:20000],
                "stderr": ((exc.stderr or "") + "\n[TIMEOUT]")[:20000],
                "timed_out": True,
            }
        except FileNotFoundError as exc:
            return {
                "return_code": 127,
                "stdout": "",
                "stderr": str(exc),
                "timed_out": False,
            }

    @staticmethod
    def _diagnose(result: Dict[str, Any]) -> str | None:
        if result["return_code"] == 0:
            return None
        if result["return_code"] == 124:
            return "timeout"
        if result["return_code"] == 127:
            return "comando_nao_encontrado_no_ambiente"
        return "falha_na_execucao"
