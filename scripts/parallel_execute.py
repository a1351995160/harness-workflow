#!/usr/bin/env python3
"""Parallel execution planner for Harness Workflow.

Analyzes task dependencies and generates a parallel execution plan.
Outputs batch execution strategy for Claude Code to dispatch agents.

Usage:
    python run.py parallel_execute.py
    python run.py parallel_execute.py --plan-file plan.md --max-parallel 4
    python run.py parallel_execute.py --dry-run --json

Exit codes:
    0: Plan generated successfully
    1: Error generating plan
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

from harness_shared import (
    detect_language,
    load_harness_config,
)

# Agent type mapping: harness agent -> OMC/Claude Code agent type
AGENT_DISPATCH_MAP = {
    "analyst": "oh-my-claudecode:analyst",
    "planner": "oh-my-claudecode:planner",
    "architect": "oh-my-claudecode:architect",
    "executor": "oh-my-claudecode:executor",
    "deep-executor": "oh-my-claudecode:executor",
    "reviewer": "oh-my-claudecode:code-reviewer",
    "security": "oh-my-claudecode:security-reviewer",
    "tester": "oh-my-claudecode:test-engineer",
    "writer": "oh-my-claudecode:writer",
    "build-fixer": "oh-my-claudecode:build-fixer",
    "debugger": "oh-my-claudecode:debugger",
    "verifier": "oh-my-claudecode:verifier",
    "observer": "general-purpose",
    "gc-agent": "general-purpose",
}

# Agent model mapping
AGENT_MODEL_MAP = {
    "analyst": "opus",
    "planner": "opus",
    "architect": "opus",
    "executor": "sonnet",
    "deep-executor": "opus",
    "reviewer": "opus",
    "security": "sonnet",
    "tester": "sonnet",
    "writer": "haiku",
    "build-fixer": "sonnet",
    "debugger": "sonnet",
    "verifier": "sonnet",
    "observer": "sonnet",
    "gc-agent": "sonnet",
}

# Parallel groups: agents that CAN run simultaneously
PARALLEL_GROUPS = {
    "tdd_cycle": {
        "agents": ["tester", "architect"],
        "description": "Tests and interface review can run in parallel",
    },
    "review_triple": {
        "agents": ["reviewer", "security", "verifier"],
        "description": "Code quality, security, and spec compliance can run in parallel",
    },
    "docs_parallel": {
        "agents": ["writer", "gc-agent"],
        "description": "Documentation and cleanup can run in parallel",
    },
}

# Dependency rules: which agents must complete before others
AGENT_DEPENDENCIES = {
    "reviewer": ["executor"],
    "security": ["executor"],
    "verifier": ["executor", "tester"],
    "tester": ["executor"],
    "writer": ["executor"],
    "gc-agent": [],
}


# ─────────────────────────────────────────────────────────────
# Task Parsing
# ─────────────────────────────────────────────────────────────

def parse_tasks_from_md(content: str) -> List[Dict[str, Any]]:
    """Parse tasks from a tasks.md file."""
    tasks = []
    for match in re.finditer(
        r"-\s+\[([ x])\]\s+(?:\*\*)?T(\d+)(?:\*\*)?:?\s*(.+?)(?:\*\*)?$",
        content, re.MULTILINE
    ):
        completed = match.group(1) == "x"
        task_id = f"T{match.group(2)}"
        description = match.group(3).strip().strip("*")
        tasks.append({
            "id": task_id,
            "description": description,
            "completed": completed,
            "deps": [],
            "agent": _infer_agent(description),
        })

    # Simple format tasks are handled by parse_simple_tasks()

    return tasks


def parse_simple_tasks(content: str, existing: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse simple checkbox tasks that don't match T{n} format.

    Handles: - [ ] Task description, - [x] Completed task, etc.
    """
    existing_descs = {t["description"] for t in existing}
    tasks = list(existing)

    for match in re.finditer(
        r"-\s+\[([ x])\]\s+(.+)$", content, re.MULTILINE
    ):
        text = match.group(2).strip()
        completed = match.group(1) == "x"
        # Skip T{n} format (already parsed) and duplicates
        if re.match(r"T\d+\s*[:.]?\s*", text):
            continue
        if text in existing_descs:
            continue
        existing_descs.add(text)
        tasks.append({
            "id": f"task-{len(tasks) + 1}",
            "description": text,
            "completed": completed,
            "deps": [],
            "agent": _infer_agent(text),
        })

    return tasks


def parse_dependencies(content: str, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Parse dependency relationships from tasks.md content."""
    # Look for dependency patterns like "T2 → T1" or "depends on T1"
    dep_patterns = [
        re.compile(r"(T\d+)\s*(?:→|->|depends?\s+on|requires?)\s*(T\d+)", re.IGNORECASE),
        re.compile(r"(T\d+)\s*(?:←|<-)\s*(T\d+)", re.IGNORECASE),  # reverse
    ]
    task_map = {t["id"]: t for t in tasks}

    for pattern in dep_patterns:
        for match in pattern.finditer(content):
            source = match.group(1).upper()
            target = match.group(2).upper()
            if source in task_map and target not in task_map[source]["deps"]:
                task_map[source]["deps"].append(target)

    return tasks


def _infer_agent(description: str) -> str:
    """Infer the best agent for a task based on its description."""
    desc_lower = description.lower()

    # Priority-ordered routing (matches harness-config.yaml routing)
    routing = [
        (r"security|auth|vulnerability", "security"),
        (r"test|spec|coverage|assert|mock", "tester"),
        (r"review|check|audit", "reviewer"),
        (r"implement|create|build|write code|add|develop", "executor"),
        (r"design|architecture|model", "architect"),
        (r"document|readme|docs", "writer"),
        (r"debug|error|bug|fix|resolve", "debugger"),
        (r"verify|complete|done|validate", "verifier"),
        (r"complex|autonomous|multi-file|refactor", "deep-executor"),
        (r"plan|breakdown|tasks", "planner"),
        (r"analyze|requirements|clarify", "analyst"),
        (r"build error|compilation|type error|dependency", "build-fixer"),
        (r"entropy|cleanup|slop|dead code", "gc-agent"),
    ]

    for pattern, agent in routing:
        if re.search(pattern, desc_lower):
            return agent
    return "executor"


# ─────────────────────────────────────────────────────────────
# Batch Resolution (Topological Sort)
# ─────────────────────────────────────────────────────────────

def resolve_batches(
    tasks: List[Dict[str, Any]],
    max_parallel: int = 3,
) -> List[Dict[str, Any]]:
    """Topological sort with parallelism: group independent tasks into batches."""
    task_map = {t["id"]: t for t in tasks}
    remaining = [t for t in tasks if not t["completed"]]
    completed_ids: Set[str] = set(t["id"] for t in tasks if t["completed"])
    batches = []

    while remaining:
        # Find tasks whose dependencies are all completed
        ready = []
        for t in remaining:
            deps_met = all(d in completed_ids for d in t["deps"])
            if deps_met:
                ready.append(t)

        if not ready:
            # Circular dependency or all remaining blocked
            batches.append({
                "batch_id": len(batches) + 1,
                "tasks": [],
                "blocked": [t["id"] for t in remaining],
                "note": "Remaining tasks blocked by unresolvable dependencies",
            })
            break

        # Limit batch size by max_parallel
        batch_tasks = ready[:max_parallel]
        batches.append({
            "batch_id": len(batches) + 1,
            "tasks": batch_tasks,
            "parallel_safe": len(batch_tasks) > 1,
        })

        for t in batch_tasks:
            completed_ids.add(t["id"])
            remaining.remove(t)

    return batches


# ─────────────────────────────────────────────────────────────
# Dispatch Instructions
# ─────────────────────────────────────────────────────────────

def generate_dispatch_instructions(
    batches: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Generate Claude Code Agent dispatch instructions for each batch."""
    instructions = []

    for batch in batches:
        batch_instruction = {
            "batch_id": batch["batch_id"],
            "parallel": batch.get("parallel_safe", False),
            "agents": [],
        }

        for task in batch.get("tasks", []):
            agent_type = task.get("agent", "executor")
            omc_agent = AGENT_DISPATCH_MAP.get(agent_type, "oh-my-claudecode:executor")
            model = AGENT_MODEL_MAP.get(agent_type, "sonnet")

            batch_instruction["agents"].append({
                "task_id": task["id"],
                "task": task["description"],
                "agent_type": agent_type,
                "dispatch_to": omc_agent,
                "model": model,
                "description": task["description"][:80],
                "prompt": (
                    f"Execute task {task['id']}: {task['description']}. "
                    f"Follow harness-workflow conventions. "
                    f"Run build-verify after completing."
                ),
            })

        if batch.get("blocked"):
            batch_instruction["blocked"] = batch["blocked"]

        instructions.append(batch_instruction)

    return instructions


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate parallel execution plan from task dependencies",
    )
    parser.add_argument("--plan-file", help="Read tasks from a plan/markdown file")
    parser.add_argument(
        "--max-parallel", type=int, default=3,
        help="Maximum concurrent agents (default: 3)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Output plan without executing",
    )
    parser.add_argument("--project-dir", default=".", help="Project directory")
    parser.add_argument(
        "--dispatch",
        action="store_true",
        help="Output Claude Code Agent dispatch commands (for TeamCreate orchestration)",
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    if not project_dir.exists():
        print(f"Error: Project directory not found: {project_dir}")
        sys.exit(1)

    # Find tasks file
    tasks_content = ""
    if args.plan_file:
        plan_path = Path(args.plan_file)
        if not plan_path.exists():
            print(f"Error: Plan file not found: {plan_path}")
            sys.exit(1)
        tasks_content = plan_path.read_text(encoding="utf-8")
    else:
        # Auto-discover tasks.md
        for search_dir in [
            project_dir / "openspec" / "changes",
            project_dir / "openspec" / "specs",
        ]:
            if not search_dir.is_dir():
                continue
            for change_dir in search_dir.iterdir():
                if not change_dir.is_dir():
                    continue
                tasks_file = change_dir / "tasks.md"
                if tasks_file.exists():
                    tasks_content += tasks_file.read_text(encoding="utf-8") + "\n"

    if not tasks_content:
        print("Error: No tasks found. Use --plan-file or run from a project with openspec/")
        sys.exit(1)

    # Parse tasks and dependencies
    tasks = parse_tasks_from_md(tasks_content)
    tasks = parse_simple_tasks(tasks_content, tasks)
    tasks = parse_dependencies(tasks_content, tasks)

    if not tasks:
        print("Error: No tasks parsed from input")
        sys.exit(1)

    # Resolve execution batches
    batches = resolve_batches(tasks, max_parallel=args.max_parallel)

    # Generate dispatch instructions
    instructions = generate_dispatch_instructions(batches)

    output = {
        "project_dir": str(project_dir),
        "total_tasks": len(tasks),
        "completed_tasks": sum(1 for t in tasks if t["completed"]),
        "max_parallel": args.max_parallel,
        "batches": len(batches),
        "execution_plan": instructions,
    }

    if args.dispatch:
        # Output Claude Code Agent dispatch instructions
        print("# Harness Workflow Agent Dispatch Plan")
        print(f"# Tasks: {output['total_tasks']}, Batches: {len(batches)}")
        print()
        for batch in instructions:
            mode = "PARALLEL" if batch["parallel"] else "SEQUENTIAL"
            print(f"## Batch {batch['batch_id']} ({mode})")
            for agent in batch["agents"]:
                print(f"  Agent: {agent['dispatch_to']}")
                print(f"  Model: {agent['model']}")
                print(f"  Task: {agent['task_id']}: {agent['task'][:80]}")
                print(f"  Prompt: {agent['prompt']}")
                print()
            if batch.get("blocked"):
                print(f"  BLOCKED: {', '.join(batch['blocked'])}")
            print()
        print("# Execute: For PARALLEL batches, launch multiple Agent tool calls in one message.")
        print("# For SEQUENTIAL batches, run one at a time.")
        print("# Run build-verify between batches.")
        sys.exit(0)

    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print(f"Parallel Execution Plan")
        print(f"  Tasks: {output['total_tasks']} total, {output['completed_tasks']} completed")
        print(f"  Max parallel: {args.max_parallel}")
        print()

        for batch in instructions:
            parallel_str = "PARALLEL" if batch["parallel"] else "SEQUENTIAL"
            print(f"  Batch {batch['batch_id']} ({parallel_str}):")
            for agent in batch["agents"]:
                print(f"    {agent['task_id']}: {agent['task'][:60]}")
                print(f"      -> {agent['dispatch_to']} ({agent['model']})")
            if batch.get("blocked"):
                print(f"    BLOCKED: {', '.join(batch['blocked'])}")
            print()

        # Claude Code instruction
        print("Claude Code Execution Instruction:")
        print("  For each batch with PARALLEL=true, launch multiple Agent tool calls")
        print("  in a single message. For SEQUENTIAL batches, run one at a time.")
        print("  Run build-verify between batches.")

    sys.exit(0)


if __name__ == "__main__":
    main()
