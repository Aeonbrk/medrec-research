"""Human-in-the-Loop (HITL) Decision Gate for scientific steering."""

from __future__ import annotations

import json
import os
import signal
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ._atomic_write import atomic_write


@dataclass
class Decision:
    """Audit record of a human decision at a scientific gate."""

    decision_id: str
    timestamp: datetime
    phase: str
    context: dict[str, Any]
    options: list[str]
    chosen: str
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Decision:
        ts = datetime.fromisoformat(data["timestamp"])
        return cls(
            decision_id=data["decision_id"],
            timestamp=ts,
            phase=data["phase"],
            context=data.get("context", {}),
            options=data.get("options", []),
            chosen=data.get("chosen", ""),
            notes=data.get("notes", ""),
        )


class HITLDecisionGate:
    """Interactive decision gate that halts execution at key scientific checkpoints."""

    def __init__(self, decisions_dir: Path, interactive: bool = True):
        self.decisions_dir = Path(decisions_dir)
        self.decisions_dir.mkdir(parents=True, exist_ok=True)
        self.interactive = interactive

    def wait_for_choice(
        self,
        phase: str,
        prompt: str,
        options: list[str],
        context: dict[str, Any] | None = None,
        auto_choice: str | None = None,
        timeout_seconds: int = 3600,
    ) -> str:
        """Present options to human researcher and record their binding choice."""
        ctx = context or {}
        now = datetime.now(UTC)
        decision_id = f"{now.strftime('%Y%m%d-%H%M%S')}-{phase}"

        print("\n" + "=" * 64)
        print(f"🤔 HITL Decision Point: {phase.upper()}")
        print("=" * 64)
        print(f"\n{prompt}\n")

        print("📋 可选行动 (Options):")
        for i, option in enumerate(options, 1):
            print(f"  [{i}] {option}")

        if ctx:
            print("\n📊 决策上下文 (Context):")
            self._display_context(ctx)

        chosen = ""
        notes = ""

        # Auto-choice mode check (via argument or env var for automated pipelines/tests)
        env_auto = os.environ.get("MEDREC_HITL_AUTO_CHOICE")
        if auto_choice is not None:
            chosen = self._match_or_index(auto_choice, options)
        elif env_auto:
            chosen = self._match_or_index(env_auto, options)
        elif not self.interactive or not sys.stdin.isatty():
            # Non-interactive fallback: default to first option
            chosen = options[0] if options else ""
            print(f"\n[Non-interactive] 自动选择默认项: {chosen}")
        else:
            # Interactive user prompt with timeout
            def timeout_handler(signum, frame):
                raise TimeoutError("HITL decision timeout")

            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout_seconds)

            try:
                while True:
                    user_input = input("\n👉 你的选择 (输入编号或内容): ").strip()
                    match = self._resolve_input(user_input, options)
                    if match:
                        chosen = match
                        break
                    print(f"⚠️ 无效选择，请输入 1 到 {len(options)} 之间的编号。")

                try:
                    notes = input("💬 决策备注 (可选, 直接回车跳过): ").strip()
                except EOFError:
                    notes = ""
            except TimeoutError:
                print(f"\n⏰ Decision timeout after {timeout_seconds}s.")
                print(f"Phase '{phase}' requires explicit human decision.")
                raise TimeoutError(
                    f"HITL decision gate timeout after {timeout_seconds}s. "
                    f"No automatic approval. Restart the phase manually."
                )
            finally:
                signal.alarm(0)

        decision = Decision(
            decision_id=decision_id,
            timestamp=now,
            phase=phase,
            context=ctx,
            options=options,
            chosen=chosen,
            notes=notes,
        )

        saved_path = self.record_decision(decision)
        print(f"\n✅ 决策已记录至: {saved_path}")
        print(f"🎯 选定方案: {chosen}")
        print("=" * 64 + "\n")

        return chosen

    def record_decision(self, decision: Decision) -> Path:
        """Persist decision record as a structured JSON file."""
        filepath = self.decisions_dir / f"{decision.decision_id}.json"
        atomic_write(filepath, json.dumps(decision.to_dict(), indent=2, ensure_ascii=False))
        return filepath

    def _resolve_input(self, user_input: str, options: list[str]) -> str | None:
        if not user_input:
            return None
        # Try integer index
        try:
            idx = int(user_input) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except ValueError:
            pass

        # Try exact or substring match
        for opt in options:
            if user_input.lower() == opt.lower() or user_input.lower() in opt.lower():
                return opt
        return None

    def _match_or_index(self, val: str, options: list[str]) -> str:
        resolved = self._resolve_input(val, options)
        if resolved:
            return resolved
        return options[0] if options else val

    def _display_context(self, context: dict[str, Any], indent: int = 2):
        prefix = " " * indent
        for key, val in context.items():
            if isinstance(val, dict):
                print(f"{prefix}• {key}:")
                self._display_context(val, indent=indent + 2)
            elif isinstance(val, list):
                print(f"{prefix}• {key}:")
                for item in val:
                    print(f"{prefix}  - {item}")
            else:
                print(f"{prefix}• {key}: {val}")
