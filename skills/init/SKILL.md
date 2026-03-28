---
name: init
description: "Initialize a project with Harness Workflow structure. Use when: user wants to set up harness-workflow for a new or existing project; invokes /harness-workflow:init; mentions project initialization with harness; wants to configure quality enforcement (git hooks, Claude Code hooks). Detects language/framework, creates .harness/ state, OpenSpec structure, and optional git/hooks setup."
---

# /harness-workflow:init - Initialize Harness Workflow

Initialize a project with the Harness Workflow structure.

## Usage

```bash
/harness-workflow:init
/harness-workflow:init /path/to/project   # Specify project directory
```

## What It Does

Runs `python ../../scripts/run.py init_harness.py [project-dir]` which:

1. **Detects project environment** - language, framework, package manager
2. **Creates `.harness/` directory** - state.json (workflow tracking), config.yaml (configuration)
3. **Creates `openspec/` directory** - config.yaml + per-feature change directories
4. **Copies templates** - intent.md to project root, proposal/design/tasks to feature change dir
5. **Generates hook config** - lefthook.yml based on detected language
6. **Git init** (optional, `--git`) - initializes git repo with .gitignore and lefthook
7. **Claude Code hooks** (optional, `--claude-hooks`) - generates session-level quality enforcement
8. **Validates setup** - confirms all files created correctly

## Options

| Option | Description |
|--------|-------------|
| `--feature <name>` | Feature name for the change directory (default: "initial") |
| `--force` | Overwrite existing files |
| `--git` | Initialize git repository with lefthook hooks |
| `--claude-hooks` | Generate Claude Code hooks for quality enforcement |

## Claude Instructions

When this command is invoked:

1. Ask the user which quality enforcement options they want:
   - `--git` for git-based hard enforcement (lefthook pre-commit hooks)
   - `--claude-hooks` for session-level enforcement (no git required)
   - Both can be combined: `--git --claude-hooks`

2. Run the initialization script:
   ```
   python ../../scripts/run.py init_harness.py . --feature <feature-name> --git --claude-hooks
   ```

3. If the project is already initialized, ask the user if they want to reinitialize with `--force`:
   ```
   python ../../scripts/run.py init_harness.py . --feature <feature-name> --git --claude-hooks --force
   ```

4. After initialization, report the detected environment:
   - Language and framework detected
   - Files created
   - Hooks configured (git lefthook, Claude Code hooks, or neither)
   - Any issues found

5. Guide the user to next steps:
   - Edit `intent.md` to capture the feature goal
   - Run `/harness-workflow:start` to begin the workflow

## Quality Enforcement Options

### Option A: Git + Lefthook (Recommended)

```bash
python ../../scripts/run.py init_harness.py . --git
```

Provides **hard enforcement** via git hooks:
- **pre-commit**: lint + format + typecheck (blocks bad commits)
- **pre-push**: build-verify loop + test coverage (blocks bad pushes)
- **commit-msg**: conventional commit format validation

Requires: `git init` + `npm install -D lefthook`

### Option B: Claude Code Hooks (No Git)

```bash
python ../../scripts/run.py init_harness.py . --claude-hooks
```

Provides **session-level enforcement** via Claude Code hooks:
- **PostToolUse (Edit|Write)**: runs lint after every file edit, injects results as context
- **Stop**: runs lint + typecheck + test before session ends, prevents stopping with failing checks

Creates: `.claude/settings.json` with hooks configuration

### Option C: Both (Maximum Enforcement)

```bash
python ../../scripts/run.py init_harness.py . --git --claude-hooks
```

### Option D: Neither (Soft Enforcement Only)

```bash
python ../../scripts/run.py init_harness.py .
```

Quality checks rely entirely on Claude reading exit codes and acting on them.

## Detected Languages

The script detects: TypeScript, JavaScript, Python, Go, Java, Rust, C# (.NET), Ruby, PHP.

Frameworks detected: Next.js, React, Vue, Express, Django, FastAPI, Flask, Spring, ASP.NET.

## Framework-Specific Behavior

- **Next.js**: `lint` command uses `npx next lint` instead of generic ESLint
- **React/Next.js**: Auto-detects Playwright or Cypress for `package.json` for add `test_e2e` command for loose loop
- **.NET/C#**: `lint` uses `dotnet format`, `typecheck` uses `dotnet build`, `test` uses `dotnet test`

## Output Structure

```
project/
├── .claude/
│   └── settings.json      # Claude Code hooks (--claude-hooks only)
├── .git/                   # Git repository (--git only)
├── .gitignore              # Git ignore rules (--git only)
├── .harness/
│   ├── state.json          # Workflow state tracking (v2.0.0)
│   └── config.yaml         # Full configuration template
├── openspec/
│   ├── config.yaml         # OpenSpec configuration
│   └── changes/
│       └── <feature>/
│           ├── .openspec.yaml   # Change metadata
│           ├── proposal.md      # Template
│           ├── design.md        # Template
│           └── tasks.md         # Template
├── intent.md               # Intent capture template
└── lefthook.yml            # Git hooks config (always generated)
```

## Claude Code Hooks Details

When `--claude-hooks` is used, the generated `.claude/settings.json` contains:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [{
          "type": "command",
          "command": "<lint-command> 2>&1 || echo '[HARNESS] Lint check failed'"
        }]
      }
    ],
    "Stop": [
      {
        "hooks": [{
          "type": "command",
          "command": "<lint> && <typecheck> && <test> 2>&1"
        }]
      }
    ]
  }
}
```

The actual commands are auto-detected from the project's language and tooling.

## OpenSpec CLI Integration

If the OpenSpec CLI is installed (`npm install -g @fission-ai/openspec`), the script
will delegate initialization to `openspec init` automatically. If the CLI is not available,
it falls back to creating the manual structure shown above.

## Exit Codes

- `0` - Success
- `1` - Failure (validation issues, invalid directory)
