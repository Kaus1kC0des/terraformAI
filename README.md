# tfai

`tfai` is an AI-assisted command-line tool for Terraform. It does two jobs:

1. **A Terraform wrapper.** `tfai init`, `tfai plan`, `tfai apply` and the other commands run
   the real `terraform` binary. They add friendlier long options and confirmation prompts for
   commands that change state.
2. **A read-only Terraform agent.** `tfai ask "<question>"` sends your question to an OpenAI
   model. The model can read your `.tf` files and run `terraform validate` and `terraform plan`
   to find the answer. It cannot change files or infrastructure.

AWS is the main target. Development and testing use a local AWS emulator, so no real
cloud account is needed.

> **Status:** early, active development. This README describes only what works today.

---

## Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Quick start](#quick-start)
- [The agent: `tfai ask`](#the-agent-tfai-ask)
- [The Terraform wrapper](#the-terraform-wrapper)
- [Safety behavior](#safety-behavior)
- [Project layout](#project-layout)
- [How it works](#how-it-works)
- [Development](#development)
- [Work in progress](#work-in-progress)
- [License](#license)

---

## Requirements

| Tool | Version | Notes |
| --- | --- | --- |
| Python | 3.12+ | Pinned in `.python-version` |
| [uv](https://docs.astral.sh/uv/) | any recent | Manages the virtualenv and dependencies |
| [Terraform](https://developer.hashicorp.com/terraform/install) | 1.x | Must be on your `PATH` |
| OpenAI API key | | Only needed for `tfai ask` |

## Installation

```bash
git clone git@github.com:Kaus1kC0des/terraformAI.git
cd terraformAI
uv sync
```

`uv sync` creates `.venv/` and installs `tfai` in editable mode. Run it with `uv run`:

```bash
uv run tfai --help
```

Or activate the virtualenv once and call `tfai` directly:

```bash
source .venv/bin/activate
tfai --help
```

## Configuration

Copy the example env file and fill in your key:

```bash
cp .env.example .env
```

| Variable | Required | Default | Used by |
| --- | --- | --- | --- |
| `OPENAI_API_KEY` | for `ask` | none | The OpenAI client |
| `TFAI_MODEL` | no | `gpt-6-luna` | The model that `ask` uses |
| `TFAI_CHDIR` | no | `.` | The Terraform working directory (same as `-C`) |

`.env` is loaded when the agent first creates its OpenAI client. Variables already
exported in your shell take priority over `.env`. `.env` is in `.gitignore`, so never
commit it.

## Quick start

```bash
# Wrapper commands, run in the current directory
tfai init
tfai validate
tfai plan

# Point at another Terraform directory
tfai -C infra/prod plan

# Ask the agent a question
tfai ask "Is my configuration valid? If not, what should I fix?"
tfai -C infra/prod ask "What will change if I apply right now?"
```

---

## The agent: `tfai ask`

```text
Usage: tfai ask [OPTIONS] QUESTION

  Ask the agent about your Terraform code. It can read, validate and plan;
  it never changes anything.

Options:
  --verbose   Show each tool call the agent makes (stderr).
```

### What the agent can do

The agent has three tools. The model decides which tools to call and in what order.

| Tool | What it runs | Output returned to the model |
| --- | --- | --- |
| `terraform_validate` | `terraform validate -json` | Exit code, stdout, stderr |
| `terraform_plan` | `terraform plan -no-color -input=false` | Exit code, stdout, stderr |
| `read_file` | Reads one file | The file text, or an error message |

The agent has **no** tool that writes files, applies or destroys infrastructure, or changes
state. When it finds a problem, it describes the fix, and you make the change yourself.

### The working directory is set by code, not by the model

The working directory comes from `-C/--chdir` (default: the current directory). The model
never chooses it. The tool schemas sent to OpenAI have no directory parameter. The agent loop
adds `workdir` to every tool call after the model replies, so a value the model sends cannot
override it.

`read_file` has two more limits:

- The path is resolved (following `..` and symlinks) and must stay **inside** the working
  directory.
- Only files that end in **`.tf`** can be read. This blocks `.env`, `*.tfstate`,
  `~/.aws/credentials` and similar files.

### How a question is answered

```text
you ──question──▶ run_agent ──▶ OpenAI (Responses API)
                     ▲                │
                     │      function_call(s)?
                     │        │yes          │no
                     │        ▼             ▼
                     └── run tools ◀──  return the model's answer
                       (validate / plan / read_file)
```

1. Your question is the first message in the conversation.
2. The model replies. If the reply has one or more `function_call` items, the loop runs
   every call (the model can call more than one tool at a time), appends the results and
   asks the model again.
3. When a reply has no function calls, the loop returns the model's text as the answer.
4. The loop stops after **15 turns** even if the model is still calling tools.

If a tool raises an exception, the error goes back to the model as the tool result. The
model can then recover, for example by retrying with a different file name.

### `--verbose`

`--verbose` turns on INFO logging to stderr. You see the arguments the model sent, each tool
call and each tool's output. stdout still contains only the final answer, so this works:

```bash
tfai ask --verbose "Why does validate fail?" > answer.txt
```

### Errors

| Situation | What you see | Exit code |
| --- | --- | --- |
| OpenAI rejects the API key | `OpenAI rejected your API key. Check OPENAI_API_KEY in your .env or environment.` | 1 |
| No API key is set | `OpenAI request failed: Missing credentials. ...` | 1 |
| Any other OpenAI error (network, rate limit, bad model name) | `OpenAI request failed: <details>` | 1 |
| The 15-turn limit is reached | `Reached MAX_TURNS can't run anymore!` | 0 |

### What is sent to OpenAI

`tfai ask` sends this data to OpenAI:

- your question,
- the content of every `.tf` file the model reads,
- the full output of `terraform validate` and `terraform plan`.

**Plan output can contain sensitive values.** For example, a variable marked
`sensitive = true` can still appear in the text plan through computed attributes such as
`tags_all`. Do not run `tfai ask` against configurations whose secrets must not leave your
machine.

### Before you ask

- Run `tfai init` first. The agent does not run `init`, and `plan` fails in an uninitialized
  directory.
- `terraform plan` calls your cloud provider's APIs **with whatever credentials your provider
  block resolves to**. See [Local sandbox](#local-sandbox) for a safe setup.
- `plan` takes a state lock. If you kill `tfai ask` while a plan runs, the lock can stay. Use
  `terraform force-unlock` to release it.

---

## The Terraform wrapper

Every wrapper command builds an argument list and runs the real `terraform` binary.

### Global option

| Option | Env var | Default | Effect |
| --- | --- | --- | --- |
| `-C`, `--chdir DIR` | `TFAI_CHDIR` | `.` | Runs terraform as `terraform -chdir=DIR ...` |

### Commands

**Core workflow**

| Command | Options | Terraform command |
| --- | --- | --- |
| `tfai init` | `--upgrade`, `--reconfigure`, `--backend-config X` (repeatable) | `terraform init` |
| `tfai fmt` | `--check`, `--recursive`, `--diff` | `terraform fmt` |
| `tfai validate` | `--json` | `terraform validate` |
| `tfai plan` | `--target`, `--var`, `--var-file` (all repeatable), `--out FILE`, `--destroy`, `--refresh/--no-refresh`, `--lock/--no-lock` | `terraform plan` |
| `tfai apply [PLAN_FILE]` | `--target`, `--var`, `--var-file`, `--lock/--no-lock`, `--yes` | `terraform apply` |
| `tfai destroy` | `--target`, `--var`, `--var-file`, `--lock/--no-lock`, `--yes` | `terraform destroy` |

**Read-only information**

| Command | Options | Terraform command |
| --- | --- | --- |
| `tfai version` | `--json` | `terraform version` |
| `tfai show [PATH]` | `--json` | `terraform show` |
| `tfai output [NAME]` | `--json`, `--raw` | `terraform output` |
| `tfai providers` | | `terraform providers` |

**State: `tfai state ...`**

| Command | Options | Notes |
| --- | --- | --- |
| `state list [ADDRESS...]` | `--id ID` | |
| `state show ADDRESS` | | |
| `state mv SOURCE DEST` | `--dry-run`, `--yes` | Asks for confirmation |
| `state rm ADDRESS...` | `--dry-run`, `--yes` | Asks for confirmation. Removes items from state only; real infrastructure is not destroyed |
| `state pull` | | Prints the state as JSON |

**Workspaces: `tfai workspace ...`**

| Command | Options | Notes |
| --- | --- | --- |
| `workspace list` | | |
| `workspace show` | | |
| `workspace new NAME` | | |
| `workspace select NAME` | | |
| `workspace delete NAME` | `--force`, `--yes` | Asks for confirmation |

### How options become Terraform flags

tfai options are long, double-dash options. They are converted to Terraform's single-dash
flags:

| tfai | terraform |
| --- | --- |
| `--var-file prod.tfvars` | `-var-file=prod.tfvars` |
| `--target a --target b` | `-target=a -target=b` |
| `--upgrade` | `-upgrade` |
| `--no-refresh` | `-refresh=false` |
| `--yes` (apply/destroy) | `-auto-approve` |

### Passing other Terraform flags

Every command forwards flags that it does not model. Write them in Terraform's single-dash
form, or put them after `--`:

```bash
tfai plan -no-color -out=p.tfplan
tfai plan -- -parallelism=5
```

### Output and exit codes

- `init`, `fmt`, `plan`, `apply` and `destroy` **stream**. Terraform uses your terminal
  directly, so colors, progress output and approval prompts work normally.
- The other commands **capture** Terraform's output, then print stdout to stdout and stderr
  to stderr.
- Terraform's exit code is passed through. A failing `tfai validate` exits with the same
  code as `terraform validate`.
- If `terraform` is not on your `PATH`, tfai prints an install link and exits with code
  **127**.

---

## Safety behavior

| Command | Default behavior | How to skip the prompt |
| --- | --- | --- |
| `apply`, `destroy` | Terraform asks for approval | `--yes` (adds `-auto-approve`) |
| `state mv`, `state rm` | tfai asks `Move ...?` / `Remove ...?` | `--yes`, or `--dry-run` (nothing changes) |
| `workspace delete` | tfai asks `Delete workspace '<name>'?` | `--yes` |
| `ask` | Read-only. The agent has no write, apply or destroy tools | n/a |

**No short options on subcommands, on purpose.** Commands accept unknown single-dash flags
(such as `-destroy`) so that they can forward them to Terraform. Click reads `-destroy` as a
bundle of short flags (`-d -e -s -t ...`). If `--yes` had a `-y` alias, `tfai apply -destroy`
would turn on auto-approve without asking. So subcommand options are long-only, and a test
checks that `tfai apply -destroy` does not auto-approve.

---

## Project layout

```text
terraformAI/
├── src/
│   ├── tfai/                    # The CLI: Typer app and Terraform wrapper
│   │   ├── cli.py               # Composition root: global -C option, registers command groups
│   │   ├── commands/
│   │   │   ├── ask.py           # `tfai ask`: calls the agent and handles OpenAI errors
│   │   │   ├── info.py          # version, show, output, providers
│   │   │   ├── lifecycle.py     # init, fmt, validate, plan, apply, destroy
│   │   │   ├── state.py         # state list/show/mv/rm/pull
│   │   │   └── workspace.py     # workspace list/show/new/select/delete
│   │   └── core/
│   │       ├── runner.py        # The only code that starts terraform; Typer-free, returns TfResult
│   │       ├── context.py       # TfContext (chdir), invoke() for CLI echo and exit, confirm_or_abort()
│   │       ├── flags.py         # tf_flags(): Python kwargs → terraform single-dash flags
│   │       ├── options.py       # Shared Annotated option types and EXTRA_ARGS
│   │       └── passthrough.py   # Factory for commands that only forward arguments
│   └── tf_agent/                # The AI side
│       ├── agent.py             # run_agent(): the tool-calling loop
│       ├── tools.py             # Tool functions, JSON schemas and the name → function map
│       ├── models.py            # get_client() (cached, loads .env), complete() for one-shot calls
│       ├── prompts.py           # System prompts (EXPLAIN_SYSTEM: explains validate errors)
│       └── terraform.py         # Diagnostic formatting helper (in progress)
├── tests/
│   └── test_terraform.py        # flags, runner and CLI tests (17 tests)
├── .env.example
├── .pre-commit-config.yaml
└── pyproject.toml
```

## How it works

### One place runs Terraform

`tfai.core.runner.run(args, chdir=None, stream=False)` is the only function that starts
the `terraform` process. It:

- finds the binary once with `shutil.which` (cached) and raises `TerraformNotFoundError`
  if it is missing,
- adds `-chdir=DIR` **before** the subcommand, which is where Terraform requires it,
- never raises on a non-zero exit. It returns a frozen `TfResult(argv, returncode, stdout,
  stderr)` with an `.ok` property.

`runner.py` does not import Typer. Both sides use it:

```text
tfai commands ──▶ context.invoke() ──▶ runner.run() ◀── tf_agent.tools
  (echo output, exit codes,                              (convert TfResult to
   confirm prompts)                                       JSON for the model)
```

### Agent tools

Each tool is a plain Python function that takes `workdir` plus any model-supplied arguments
and returns a **string**. `tools.py` holds three things that must stay in sync:

- the functions (`terrraform_validate`, `terraform_plan`, `read_file`),
- the JSON schemas sent to OpenAI (`terraform_tools`, `general_tools`),
- the `functions` dict that maps the model's tool name to the Python function.

`TfResult` is converted to JSON for the model, and the `argv` field is removed first.

### LLM provider

The agent uses the **OpenAI Responses API** through the official `openai` Python SDK. The
loop is written by hand, with no agent framework. The model is set by `TFAI_MODEL`.

---

## Development

### Setup

```bash
uv sync                        # installs runtime and dev dependencies
uv run pre-commit install      # once per clone
```

### Checks

```bash
uv run pytest -q               # tests
uv run ruff check              # lint
uv run ruff format .           # format
uv run pre-commit run --all-files
```

The pre-commit hook runs on every `git commit`:

1. `ruff check` on staged `.py` files,
2. `ruff format --check` on staged `.py` files (reports problems, never rewrites files),
3. the full `pytest` suite (always runs).

If a hook fails, the commit is aborted. Use `git commit --no-verify` only in an emergency.

### Tests

`tests/test_terraform.py` covers the wrapper without running Terraform:

- `tf_flags` conversions,
- `runner.run`, with `subprocess.run` replaced by a fake that records argv (checks `-chdir`
  placement, capture vs stream, missing binary),
- the CLI through Typer's `CliRunner`, with `runner.run` replaced by a recorder (flag
  building, extra-arg forwarding, the `-destroy` trap, `--yes`, confirmation aborts, exit-code
  propagation, exit 127).

The agent has no automated tests yet. Check it by hand with `tfai ask --verbose`.

### Local sandbox

The agent runs `terraform plan`, and `plan` calls real provider APIs. During development,
point Terraform at a local AWS emulator with **fake credentials**. Then a wrong setting
cannot reach a real AWS account:

```hcl
provider "aws" {
  region                      = "ap-south-1"
  access_key                  = "test"   # fake: an emulator accepts anything
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  s3_use_path_style           = true

  endpoints {
    s3       = "http://localhost:4566"
    dynamodb = "http://localhost:4566"
    sts      = "http://localhost:4566"
  }
}
```

A provider block that sets only `region` uses your default AWS credentials, which can be a
**real** account. Always set the endpoints and fake keys together.

`playground/`, `experiments/` and `broken/` are in `.gitignore`. Use them for sandbox
configs, throwaway scripts and deliberately broken Terraform.

---

## Work in progress

**Plan summaries.** We are building `src/tf_agent/plan.py`, which turns a Terraform plan
into a short, readable summary. It is a **workflow** with fixed steps, not an agent loop, so
it makes one model call:

1. **`make_plan_json(workdir)`** runs `terraform plan -out=<file>` into a temporary
   directory, then `terraform show -json <file>`, and returns the parsed plan JSON.
2. **`trim_plan(plan)`** keeps only allow-listed fields: each change's address, resource type
   and actions (`create` / `update` / `delete` / replace), plus resource drift (changes made
   outside Terraform). It removes **all attribute values**. The full plan JSON is large
   (about 8 KB for two resources) and contains sensitive variables in plaintext, so it must
   never go to the model as is.
3. **`summarize_plan(...)`** counts the actions in code ("facts from code"), then makes a
   single `complete()` call to put those facts into plain English ("words from the model").

After that, we will try it from a script in `experiments/` and then add it to the CLI.

---

## License

[Apache License 2.0](LICENSE)
