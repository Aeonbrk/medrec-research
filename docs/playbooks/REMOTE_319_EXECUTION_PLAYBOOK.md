# Remote 319 Execution Playbook

The MacBook Air is the harness terminal. The 319 remote host is the execution plane for real EHR data, training, GPU inference, and external baseline Conda environments. A local synthetic run verifies software and protocol wiring; it is not experimental evidence.

## Current snapshot (2026-08-31)

**SSH Connection**: ⚠️ Primary `319-lab` failed its preflight; approved fallback `319-lab-via-server` authenticated and was used for read-only checks and additive recovery work  
**GPU Status**: ✅ 8× NVIDIA GeForce RTX 3090 (24 GiB each); resident external GPU processes are permitted when current utilization is at most 10% and the run's free-memory threshold passes
**Disk**: ✅ `/root/zhb` filesystem had >2.5 TiB free capacity during the recovery preflight  
**Repository**: ✅ `/root/zhb/medrec-research` remains a clean checkout at `a09fcab8c3760a5caa14ec3ab475ddf4152a3665`; the additive recovery worktree did not alter it  
**Data Root**: ✅ `MEDREC_DATA_ROOT=/root/zhb/medrec-data` configured outside the checkout  
**Conda Environment**: ✅ `medrec-molerec-table1` exists with the declared Python 3.8.16 runtime and was used for program-native recovery validation  
**Reproduction Program**: ✅ SafeDrug archived and MoleRec program façades validated the seven recovery lanes without training or testing hooks

**Status Summary**: SafeDrug `main` runs are historical only. Attempt `formal-20260828-a09fcab-u8-b` completed through the authorized continuation with Reproduction verdict `completed_mismatch`; the five target baselines are Comparison-qualified under one Unified Research Protocol v1.1 scope.

## Verified snapshot

A read-only check on 2026-07-10 confirmed eight NVIDIA GeForce RTX 3090 GPUs with 24 GiB each, NVIDIA driver `535.183.01`, and reported CUDA `12.2`. GPU utilization ranged from 25% to 100%, so capacity was not generally available. The filesystem containing `/root/zhb` was 87% used. `/root/zhb/New-Search` existed, while `/root/zhb/medrec-research` did not.

On 2026-07-14, the fallback `319-lab-via-server` SSH profile authenticated through the Tailscale-backed Windows relay and reached the expected remote account. The primary `319-lab` profile must be tried first for each new preflight. The relay address, keys, account name, and target address remain local SSH configuration, not Git. This is an observation, not a permanent guarantee; rerun preflight before every experiment.

## Hard preconditions

Do not launch a real run until all conditions hold:

- The local source has an immutable Git revision and no unrecorded experiment code.
- The accepted experiment plan fixes mode, Dataset Manifest, patient-disjoint split, features, metrics, controls, Adaptation Budget, seeds, stopping rules, and artifact policy.
- A verified 319 checkout points to the exact source revision. The intended remote root is configurable and must not reuse the archived `New-Search` checkout.
- `MEDREC_DATA_ROOT` exists outside the checkout on 319.
- The declared baseline source revision, Reproduction Program, Conda environment, and requested scientific mode satisfy the run.
- Current GPU utilization is at most 10%, the run's declared free-memory threshold passes, and disk capacity is adequate.

The repository has a Git history and an `origin` remote. A 2026-08-12 read-only observation found a clean `/root/zhb/medrec-research` checkout through the fallback profile, but its revision differed from the current local accepted revision and `MEDREC_DATA_ROOT` was not configured. This supersedes the earlier missing-checkout observation without authorizing synchronization or environment changes.

## Connection preflight

Try the primary SSH target, `319-lab`, first. If it cannot establish an authenticated `root` session, retry through `319-lab-via-server`, which uses the local SSH `ProxyJump` configuration to reach 319 through the Tailscale relay. Do not use a direct address, a legacy alias, or a ControlMaster socket.

Before every remote operation, select and verify the target in the same local shell session:

```bash
REMOTE_319_HOST=319-lab
if ! remote_user="$(rtk ssh -o BatchMode=yes -o ConnectTimeout=10 "$REMOTE_319_HOST" 'id -un')" || [ "$remote_user" != root ]; then
  REMOTE_319_HOST=319-lab-via-server
  remote_user="$(rtk ssh -o BatchMode=yes -o ConnectTimeout=10 "$REMOTE_319_HOST" 'id -un')"
fi
test "$remote_user" = root
export REMOTE_319_HOST
```

Continue only when the selected target returns `root` without an SSH host-key warning. A fallback target that returns another account or exits nonzero blocks remote work. All remaining examples use the exported `REMOTE_319_HOST`.

Check capacity and repository roots without changing remote state:

```bash
rtk ssh -o BatchMode=yes -o ConnectTimeout=10 "$REMOTE_319_HOST" '
set -eu
nvidia-smi --query-gpu=index,name,memory.total,memory.free,utilization.gpu --format=csv,noheader
df -h /root/zhb
test ! -e /root/zhb/medrec-research || git -C /root/zhb/medrec-research status --short --branch
'
```

A GPU is admissible when its current utilization is at most 10% and its free memory meets the run's declared threshold. Existing external PIDs are not an admission blocker: do not query them merely to decide admission, and never kill, preempt, or attach to them. Utilization above 10% or insufficient free memory blocks launch.

## Source deployment

Use Git as the code synchronization and source-identity mechanism. Configure a remote for `medrec-research`, create its first reviewed commit, then clone it to a dedicated 319 path. Do not run new work inside `/root/zhb/New-Search`.

Before each run, verify rather than mutate:

```bash
rtk ssh -o BatchMode=yes -o ConnectTimeout=10 "$REMOTE_319_HOST" '
set -eu
cd /root/zhb/medrec-research
git status --short
git rev-parse HEAD
git branch --show-current
'
```

The reported revision must equal the accepted experiment-plan revision. A dirty checkout blocks Comparison Mode. Do not use `git reset --hard`, `git checkout --`, or automatic cleanup to force a match.

## Conda isolation

The Homebrew `uv` environment belongs only to the Mac harness and public synthetic checks. On 319, each external baseline uses its own Conda environment and process. A separate `medrec-core-evaluator` Conda environment reads restricted Prediction Records, recomputes metrics, and creates candidate Run Records. Never install the core evaluator into a Baseline Environment.

Historical SafeDrug-main environment repair details remain in Git history and the historical run summary. They do not define the archived environment. Resolve archived dependencies from the pinned archived source and verified 319 compatibility evidence; do not repair or reuse the old environment by default.

Inspect existing environments and disk before creating one:

```bash
rtk ssh -o BatchMode=yes -o ConnectTimeout=10 "$REMOTE_319_HOST" '
set -eu
source /root/anaconda3/etc/profile.d/conda.sh
conda env list
df -h /root/anaconda3 /root/zhb
'
```

Create a new environment from a registered declaration only when no verified environment matches. Resolve Conda and pip packages using China mirrors first via repository-scoped or command-scoped configuration; fall back to official HTTPS channels (e.g., PyTorch, PyG) only when exact version-specific artifacts are unavailable. TLS verification must remain strictly enabled (`ssl_verify: true`, no `--trusted-host`), and global machine/user Conda/pip configurations must never be modified. Record Python, Conda package export, CUDA, driver, GPU model, and an environment checksum in restricted run provenance. Advancing readiness requires a smoke test through the process adapter, not successful dependency resolution alone.

Create the provisional core evaluator only after the checkout revision is fixed:

```bash
rtk ssh -o BatchMode=yes -o ConnectTimeout=10 "$REMOTE_319_HOST" '
set -eu
cd /root/zhb/medrec-research
source /root/anaconda3/etc/profile.d/conda.sh
conda env create --file environments/core-evaluator.yml
conda activate medrec-core-evaluator
uv pip install --python "$CONDA_PREFIX/bin/python" --no-deps .
python -c "import medrec_research; print(medrec_research.__file__)"
'
```

`core-evaluator.yml` is a bootstrap specification, not a lock. Export an explicit 319 Linux lock, audit it, record its checksum in the run plan, and recreate the environment from that lock before accepting real evidence.

## Submission contract

Submit a frozen run specification from the Mac harness. A Reproduction Mode job records the clean harness revision, pinned baseline source, Reproduction Program, environment identity, GPU assignment, start time, and expected restricted and public-safe outputs. Comparison Mode separately records Prediction Adapter and Dataset Manifest identities.

A remote job binds declaration, contract, preflight, baseline source revision, and environment lock before submission. Never store real run logs or patient-level output in the Git checkout.

Check GPU state immediately before launch and assign devices explicitly. Do not select a device from the stale snapshot in this document.

The registry records the archived source and shared Reproduction Program declaration. Plan one lane without SSH:

```bash
rtk proxy /opt/homebrew/bin/uv run medrec-research reproduce gamenet \
  --gpu 0 \
  --dry-run
```

Dry-run validates registry identity, local Git revision, paths, and thresholds, then prints the complete command without opening SSH. Successor formal lanes additionally require an attempt-owned frozen schedule supplied with `--schedule`; the requested GPU order and CPU sets must match that artifact exactly, with GPU 7 reserved. A non-dry invocation requires a clean local worktree and 319-verified environment identity, then tries `319-lab` followed only by `319-lab-via-server`. It requires strict host-key acceptance and `root`, verifies exact clean harness and upstream revisions, external data root, archived inputs, program presence, Conda environment checksum, GPU utilization at most 10%, the declared free-memory threshold, and free disk before creating one tmux session. A failed preflight or schedule gate creates no tmux state.

The checked-in registry marks RETAIN, LEAP, GAMENet, SafeDrug, and MoleRec `comparison_ready` only for their recorded v1.1 scope; the built-in reference remains `registered`. Readiness does not waive a new run's source, environment, data, GPU-capacity, or disk preflight.

### Implementation gate and readiness

The registered SafeDrug source is `archived@8deee38cfdb2a38882377ff95cce5922d6d9e8d6` and MoleRec is `dd5afaf0a503fd3de3229f86ec7f26b345d10e3a`. Both reproduction programs (`baselines/safedrug_archived.py` and `baselines/molerec.py`) and their isolated Conda environment (`medrec-molerec-table1`, lock SHA256 `6a01d313...`) are verified.

All five scientific baselines (RETAIN, LEAP, GAMENet, SafeDrug, MoleRec) are marked `comparison_ready` under their recorded v1.1 Comparison Scope. Any new attempt or scope change requires prospective preflight and qualification.

Dry-run plan across available GPUs with:

```bash
rtk proxy /opt/homebrew/bin/uv run medrec-research reproduce all \
  --gpus 0,1,2,3 \
  --dry-run
```

Without `--dry-run`, each lane performs its own preflight and submission. A blocked lane is reported without cancelling the remaining lanes.

## Monitoring and failure

The Mac harness may poll scheduler state, process state, aggregate progress, disk, and GPU utilization. It must not stream patient rows or raw Prediction Records into local logs.

A remote process exit does not prove scientific success. Treat missing Prediction Records, partial visit coverage, schema rejection, non-finite metrics, source drift, environment drift, data-manifest mismatch, GPU failure, and disk exhaustion as failed runs. Preserve restricted diagnostics on 319 and create a public-safe Failure Record only after audit.

## Result intake

Keep raw data, split membership, checkpoints, logs, and real Prediction Records on 319. Audit there first. Transfer only gate-approved aggregate Run Records, checksums, audits, figures with no patient-level content, and concise Failure Records.

The core evaluator performs the first acceptance pass on 319:

```bash
rtk ssh -o BatchMode=yes -o ConnectTimeout=10 "$REMOTE_319_HOST" '
set -eu
cd /root/zhb/medrec-research
source /root/anaconda3/etc/profile.d/conda.sh
conda run -n medrec-core-evaluator medrec-research accept-comparison \
  --manifest "$MEDREC_RUN_ROOT/manifest.json" \
  --registry baselines/registry.toml \
  --baseline-id "$BASELINE_ID" \
  --predictions "$MEDREC_RUN_ROOT/predictions.json" \
  --medication-vocabulary "$MEDREC_RUN_ROOT/medications.txt" \
  --membership-hmac-key "$MEDREC_DATA_ROOT/keys/membership-hmac.key" \
  --run-config "$MEDREC_RUN_ROOT/run-config.json" \
  --adaptation-budget "$MEDREC_RUN_ROOT/adaptation-budget.json" \
  --artifact model="$MEDREC_RUN_ROOT/model.pt" \
  --output "$MEDREC_RUN_ROOT/run-record.json"
'
```

The command requires a `comparison_ready` registry entry, a canonical sorted medication-vocabulary file, the same private membership-HMAC key used by the restricted Dataset Manifest builder, complete test Prediction Records, a frozen run config, and a nonempty Adaptation Budget artifact. It verifies vocabulary identity and exact eligible-visit membership, recomputes metrics, and writes only aggregate identities and checksums.

Before accepting the candidate into Git, independently inspect the Readiness Evidence, verify artifact checksums, scan the record for paths and identifiers, and confirm every claim stays within the protocol's evidence boundary.

After an explicitly authorized transfer places a schema-conforming public-safe observation or aggregate evidence file on the Mac, apply it through the local ingress commands:

```bash
rtk proxy /opt/homebrew/bin/uv run medrec-research monitor-apply \
  --root /Users/oian/Codes/master/medrec-research \
  --input /path/to/public-safe-monitor.json \
  --output /path/to/public-monitor-result.json

rtk proxy /opt/homebrew/bin/uv run medrec-research evidence-intake \
  --root /Users/oian/Codes/master/medrec-research \
  --input /path/to/public-safe-evidence.json \
  --output /path/to/public-decision-packet.json
```

## Reproduction Execution Playbooks

Detailed, step-by-step reproduction preparation and execution playbooks govern remote reproduction runs on `319-wild`:

- **Historical SafeDrug Table 2 Four-Model Reproduction**: [SAFEDRUG_ARCHIVED_PREPARATION_PLAYBOOK.md](SAFEDRUG_ARCHIVED_PREPARATION_PLAYBOOK.md) (do not execute)
- **Current MoleRec Table 1 Five-Model Reproduction**: [MOLEREC_TABLE1_EXECUTION_PLAYBOOK.md](MOLEREC_TABLE1_EXECUTION_PLAYBOOK.md)

## Destructive operations

Remote deletion, environment removal, job termination, checkout reset, and data replacement require explicit user approval after showing the target, impact, and recovery path. Routine harness operation is read-only or additive.
