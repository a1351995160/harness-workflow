---
name: init
description: "Initialize a project with Harness Workflow structure. Use when: user wants to set up harness-workflow for a new or existing project; invokes /harness-workflow:init; mentions project initialization with harness; wants to configure quality enforcement. Detects language/framework, runs openspec init, creates .harness/ state, and optional git/hooks setup."
---

# /harness-workflow:init - Initialize Harness Workflow

Initialize a project with the Harness Workflow structure and OpenSpec integration.

## Usage

```bash
/harness-workflow:init
/harness-workflow:init /path/to/project   # Specify project directory
```

## Prerequisites

Before running init, ensure OpenSpec CLI is installed:

```bash
npm install -g @fission-ai/openspec
```

Verify installation:
```bash
openspec --version
```

If OpenSpec CLI is not installed, init will fall back to manual directory creation.

## What It Does

### Step 1: OpenSpec Initialization (Primary)

If OpenSpec CLI is available, run:

```bash
openspec init .
```

This automatically:
- Detects AI tools in the project (Claude Code, Cursor, etc.)
- Creates `openspec/` directory with `config.yaml`
- Generates OPSX skill files in `.claude/commands/opsx/` (for Claude Code)
- Generates skill files in `.claude/skills/openspec-*/` (for Claude Code)
- Supports 20+ AI tools: Claude Code, Cursor, Windsurf, Cline, Codex, Gemini CLI, etc.

Options:
```bash
openspec init . --tools claude          # Target specific AI tool
openspec init . --tools all             # Generate for all detected tools
openspec init . --force                 # Auto-cleanup legacy files
openspec init . --profile custom        # Use custom profile
```

### Step 2: Harness Workflow Setup

After OpenSpec init, create Harness-specific structure:

```bash
python ../../scripts/run.py init_harness.py .
```

This creates:
- `.harness/state.json` - Workflow state tracking (v2.0.0)
- `.harness/config.yaml` - Full configuration template
- `intent.md` - Intent capture template at project root

Options:
```bash
python ../../scripts/run.py init_harness.py . --feature <name>    # Feature name (default: "initial")
python ../../scripts/run.py init_harness.py . --git               # Git init with lefthook hooks
python ../../scripts/run.py init_harness.py . --claude-hooks      # Claude Code session hooks
python ../../scripts/run.py init_harness.py . --git --claude-hooks # Maximum enforcement
python ../../scripts/run.py init_harness.py . --force             # Overwrite existing
```

### Step 3: Configure Expanded Workflow (Recommended)

Enable all OPSX commands including verify, onboard, etc:

```bash
openspec config profile   # Switch to expanded profile
openspec update           # Apply the new profile
```

This unlocks additional commands: `/opsx:new`, `/opsx:continue`, `/opsx:ff`, `/opsx:verify`, `/opsx:sync`, `/opsx:onboard`.

## Claude Instructions

When this command is invoked:

1. **Check OpenSpec CLI availability**:
   ```bash
   openspec --version
   ```

2. **If available**, run OpenSpec init:
   ```bash
   openspec init . --tools claude
   ```

3. **If not available**, inform the user:
   > OpenSpec CLI is not installed. For the best experience, install it:
   > `npm install -g @fission-ai/openspec`
   > Then run `/harness-workflow:init` again.
   >
   > Continuing with manual setup as fallback...

   Then run the Python fallback:
   ```bash
   python ../../scripts/run.py init_harness.py .
   ```

4. **Ask about quality enforcement**:
   - `--git` for git-based hard enforcement (lefthook pre-commit hooks)
   - `--claude-hooks` for session-level enforcement (no git required)
   - Both: `--git --claude-hooks`

5. **Run harness init**:
   ```bash
   python ../../scripts/run.py init_harness.py . --git --claude-hooks
   ```

6. **Configure expanded workflow** (if OpenSpec CLI is available):
   ```bash
   openspec config profile
   openspec update
   ```

7. **Report results**:
   - OpenSpec status: initialized or fallback
   - Language and framework detected
   - Files created
   - Hooks configured
   - Available OPSX commands generated

8. **Guide to next steps**:
   - Edit `intent.md` to capture the feature goal
   - Use `/opsx:explore` to brainstorm ideas
   - Use `/opsx:propose` to create a change proposal
   - Run `/harness-workflow:start` to begin the full workflow

## Output Structure

```
project/
├── .claude/
│   ├── commands/opsx/        # OPSX slash commands (via openspec init)
│   │   ├── propose.md
│   │   ├── explore.md
│   │   ├── apply.md
│   │   └── archive.md
│   ├── skills/openspec-*/    # OpenSpec skills (via openspec init)
│   │   └── SKILL.md
│   └── settings.json         # Claude Code hooks (--claude-hooks only)
├── .harness/
│   ├── state.json            # Workflow state tracking
│   └── config.yaml           # Configuration template
├── openspec/
│   ├── config.yaml           # OpenSpec project config
│   └── schemas/              # Custom workflow schemas
├── intent.md                 # Intent capture template
└── lefthook.yml              # Git hooks config (--git only)
```

## Available OPSX Commands After Init

Once `openspec init` completes, these slash commands become available:

| Command | Purpose |
|---------|---------|
| `/opsx:explore` | Think through ideas, investigate problems |
| `/opsx:propose` | Create a change and generate planning artifacts |
| `/opsx:apply` | Implement tasks from the change |
| `/opsx:archive` | Archive when done |
| `/opsx:verify` | Validate implementation (expanded profile) |
| `/opsx:new` | Start a new change scaffold (expanded) |
| `/opsx:continue` | Create next artifact incrementally (expanded) |
| `/opsx:ff` | Fast-forward all planning artifacts (expanded) |
| `/opsx:onboard` | Guided end-to-end walkthrough (expanded) |

## Exit Codes

- `0` - Success
- `1` - Failure (validation issues, invalid directory)
