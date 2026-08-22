# Remote 319 Execution Playbook

The MacBook Air is the harness terminal. The 319 remote host is the execution plane for real EHR data, training, GPU inference, and external baseline Conda environments. A local synthetic run verifies software and protocol wiring; it is not experimental evidence.

## Current snapshot (2026-08-22)

**SSH Connection**: ✅ Fallback `319-lab-via-server` profile authenticated and verified (root access)  
**GPU Status**: ✅ 8× NVIDIA GeForce RTX 3090 (24 GiB each), all idle (0% utilization, ~24 GiB free each)  
**Disk**: ✅ `/root/zhb` filesystem has >2.6 TiB free capacity  
**Repository**: ✅ `/root/zhb/medrec-research` clean checkout on 319  
**Data Root**: ✅ `MEDREC_DATA_ROOT=/root/zhb/medrec-data` configured  
**Data Location**: ✅ MIMIC-III and MIMIC-IV datasets at `/root/zhb/Search/dataset` (symlinked)  
**Conda Environments**: 🔄 `medrec-gamenet` configured for SafeDrug family reproduction (`safedrug`, `retain`, `leap-safedrug`)  
**Baseline Adapters**: ✅ SafeDrug family runner (`baselines/scripts/run_safedrug_family_319.sh`) and strict result parser (`baselines/scripts/parse_safedrug_family_results.py`) implemented and tested  

**Status Summary**: SafeDrug family reproduction architecture is verified and ready for 3-GPU concurrent reproduction.

## Verified snapshot

A read-only check on 2026-07-10 confirmed eight NVIDIA GeForce RTX 3090 GPUs with 24 GiB each, NVIDIA driver `535.183.01`, and reported CUDA `12.2`. GPU utilization ranged from 25% to 100%, so capacity was not generally available. The filesystem containing `/root/zhb` was 87% used. `/root/zhb/New-Search` existed, while `/root/zhb/medrec-research` did not.

On 2026-07-14, the fallback `319-lab-via-server` SSH profile authenticated through the Tailscale-backed Windows relay and reached the expected remote account. The primary `319-lab` profile must be tried first for each new preflight. The relay address, keys, account name, and target address remain local SSH configuration, not Git. This is an observation, not a permanent guarantee; rerun preflight before every experiment.

## Hard preconditions

Do not launch a real run until all conditions hold:

- The local source has an immutable Git revision and no unrecorded experiment code.
- The accepted experiment plan fixes mode, Dataset Manifest, patient-disjoint split, features, metrics, controls, Adaptation Budget, seeds, stopping rules, and artifact policy.
- A verified 319 checkout points to the exact source revision. The intended remote root is configurable and must not reuse the archived `New-Search` checkout.
- `MEDREC_DATA_ROOT` exists outside the checkout on 319.
- The declared baseline source revision, Conda environment, adapter, and readiness satisfy the requested mode.
- GPU memory and disk capacity are adequate without disrupting another job.

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

A busy GPU is unavailable even when some memory remains. An empty `nvidia-smi` process table does not override observed memory use or utilization because process visibility may differ across containers or permissions. Do not kill, preempt, or attach to another user's process.

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

### Known Environment Issues

**PyTorch MKL Symbol Conflict** (2026-08-21): The `medrec-gamenet` environment exhibits `ImportError: undefined symbol: iJIT_NotifyEvent` when importing torch. This is a known Intel MKL library version conflict. Fix:

```bash
conda activate medrec-gamenet
conda install -y mkl=2021.4.0 mkl-service=2.4.0 -c conda-forge
```

Verify the fix before declaring the environment ready for production runs. This pattern may affect other baseline environments using PyTorch 1.8.0 + Conda.

Inspect existing environments and disk before creating one:

```bash
rtk ssh -o BatchMode=yes -o ConnectTimeout=10 "$REMOTE_319_HOST" '
set -eu
source /root/anaconda3/etc/profile.d/conda.sh
conda env list
df -h /root/anaconda3 /root/zhb
'
```

Create a new environment from a registered declaration only when no verified environment matches. Record Python, Conda package export, CUDA, driver, GPU model, and an environment checksum in restricted run provenance. Advancing readiness requires a smoke test through the process adapter, not successful dependency resolution alone.

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

Submit a frozen run specification from the Mac harness. The remote job records source revision, protocol version, baseline identity and source revision, adapter revision, Dataset Manifest identity, Conda environment identity, seed, GPU assignment, start time, and expected restricted and public-safe outputs.

A remote job binds declaration, contract, preflight, baseline source revision, and environment lock before submission. Never store real run logs or patient-level output in the Git checkout.

Check GPU state immediately before launch and assign devices explicitly. Do not select a device from the stale snapshot in this document.

The harness exposes a remote-only Reproduction Mode submission command for the declared GAMENet launcher. Inspect the local command without contacting 319 first:

```bash
rtk proxy /opt/homebrew/bin/uv run medrec-research run \
  --mode reproduction \
  --baseline-id gamenet \
  --gpu 0 \
  --min-free-gpu-mib 20000 \
  --min-free-disk-gib 100 \
  --dry-run
```

Dry-run validates the registry identity, local Git revision, remote paths, thresholds, and explicit launcher, then reports `preflight: not_run_dry_run`; it does not open SSH or establish readiness. A non-dry invocation first requires a clean local worktree and at least `smoke_ready`, then tries `319-lab` followed only by `319-lab-via-server`. It requires strict host-key acceptance and `root`, verifies the exact clean harness and upstream revisions, external data root, required `mimic-iii` input directory, launcher, Conda environment checksum, selected idle GPU, and free disk before creating one tmux session. The launch binds the verified upstream root and physical GPU through `SAFEDRUG_ROOT` and `CUDA_VISIBLE_DEVICES`; GAMENet addresses that single visible device as logical device `0`. A failed preflight gate creates no tmux state. An ambiguous tmux launch failure triggers best-effort cleanup of the newly generated unique session ID without touching other jobs.

The checked-in registry currently leaves every baseline at `registered`, so the command does not yet authorize a real run. GAMENet records the launcher content digest and the environment digest observed on 319, but it still lacks content-addressed environment-lock and adapter-smoke evidence. The launcher preserves upstream Reproduction Mode behavior and emits legacy aggregate output; it cannot feed `accept-comparison` until separate work produces strict Prediction Records and matching Comparison Qualification evidence. The manual checks above remain the operator-level source of truth and must agree with the automated preflight.

### Read-only observation on 2026-08-22

The primary alias did not establish a session; the approved fallback reached the expected `root` account. The observed `medrec-gamenet` explicit-package digest is `971ad2bfd7309cd3d7af4aae26187ad4e00bc806ad3714188e854c657f5b45fe`, the declared `mimic-iii` directory exists, and preprocessed GAMENet input is present.

Submission remains blocked. The remote harness revision differs from this branch. The SafeDrug checkout resolves to the registered `88ce5c377dcdc2aa01aaa88f5478dfa4373ba49a` revision only under a one-off read-only Git ownership override, and its worktree is not clean. Do not persist that override or clean the checkout through the harness; the remote operator must resolve ownership and worktree state, synchronize the harness revision, then generate and review the missing environment-lock and adapter-smoke evidence before changing readiness.

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

These commands do not run remote preflight or submit work. They accept only the existing strict monitor/evidence schemas, bind the input to the durable request and declaration, and reject patient rows, predictions, weights, paths inside the payload, credentials, raw logs, and unknown fields. The browser never supplies the input or output paths.

## Destructive operations

Remote deletion, environment removal, job termination, checkout reset, and data replacement require explicit user approval after showing the target, impact, and recovery path. Routine harness operation is read-only or additive.
