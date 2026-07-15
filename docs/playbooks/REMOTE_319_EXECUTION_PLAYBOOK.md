# Remote 319 Execution Playbook

The MacBook Air is the harness terminal. The 319 remote host is the execution plane for real EHR data, training, GPU inference, and external baseline Conda environments. A local synthetic run verifies software and protocol wiring; it is not experimental evidence.

## Verified snapshot

A read-only check on 2026-07-10 confirmed eight NVIDIA GeForce RTX 3090 GPUs with 24 GiB each, NVIDIA driver `535.183.01`, and reported CUDA `12.2`. GPU utilization ranged from 25% to 100%, so capacity was not generally available. The filesystem containing `/root/zhb` was 87% used. `/root/zhb/New-Search` existed, while `/root/zhb/medrec-research` did not.

On 2026-07-14, the local `319-lab-via-server` SSH profile authenticated through the Tailscale-backed Windows relay and reached the expected remote account. The relay address, keys, account name, and target address remain local SSH configuration, not Git. This is an observation, not a permanent guarantee; rerun preflight before every experiment.

## Hard preconditions

Do not launch a real run until all conditions hold:

- The local source has an immutable Git revision and no unrecorded experiment code.
- The accepted experiment plan fixes mode, Dataset Manifest, patient-disjoint split, features, metrics, controls, Adaptation Budget, seeds, stopping rules, and artifact policy.
- A verified 319 checkout points to the exact source revision. The intended remote root is configurable and must not reuse the archived `New-Search` checkout.
- `MEDREC_DATA_ROOT` exists outside the checkout on 319.
- The declared baseline source revision, Conda environment, adapter, and readiness satisfy the requested mode.
- GPU memory and disk capacity are adequate without disrupting another job.

The repository has a Git history and an `origin` remote, but its 319 checkout is absent. That blocks real execution but does not block local harness development.

## Connection preflight

`319-lab-via-server` is the only approved SSH target. It uses the local SSH `ProxyJump` configuration to reach 319 through the Tailscale relay. Do not use a direct address, a legacy alias, or a ControlMaster socket as a fallback. Stop and report a connection failure instead.

Verify the transport and remote identity before every remote operation:

```bash
rtk ssh -o BatchMode=yes -o ConnectTimeout=10 319-lab-via-server 'id -un'
```

The command must return `root`. Any other account, SSH host-key warning, or nonzero exit status blocks remote work.

Check capacity and repository roots without changing remote state:

```bash
rtk ssh -o BatchMode=yes -o ConnectTimeout=10 319-lab-via-server '
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
rtk ssh -o BatchMode=yes -o ConnectTimeout=10 319-lab-via-server '
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

Inspect existing environments and disk before creating one:

```bash
rtk ssh -o BatchMode=yes -o ConnectTimeout=10 319-lab-via-server '
set -eu
source /root/anaconda3/etc/profile.d/conda.sh
conda env list
df -h /root/anaconda3 /root/zhb
'
```

Create a new environment from a registered declaration only when no verified environment matches. Record Python, Conda package export, CUDA, driver, GPU model, and an environment checksum in restricted run provenance. Advancing readiness requires a smoke test through the process adapter, not successful dependency resolution alone.

Create the provisional core evaluator only after the checkout revision is fixed:

```bash
rtk ssh -o BatchMode=yes -o ConnectTimeout=10 319-lab-via-server '
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

ARIS submits a frozen run specification from the Mac harness. The remote job records source revision, protocol version, baseline identity and source revision, adapter revision, Dataset Manifest identity, Conda environment identity, seed, GPU assignment, start time, and expected restricted and public-safe outputs.

Use the project-local ARIS `experiment-queue` workflow when it supports the run. A manually launched fallback must use a named `tmux` session and a restricted log under the 319 Local Data Root. Never store real run logs or patient-level output in the Git checkout.

Check GPU state immediately before launch and assign devices explicitly. Do not select a device from the stale snapshot in this document.

## Monitoring and failure

The Mac harness may poll scheduler state, process state, aggregate progress, disk, and GPU utilization. It must not stream patient rows or raw Prediction Records into local logs.

A remote process exit does not prove scientific success. Treat missing Prediction Records, partial visit coverage, schema rejection, non-finite metrics, source drift, environment drift, data-manifest mismatch, GPU failure, and disk exhaustion as failed runs. Preserve restricted diagnostics on 319 and create a public-safe Failure Record only after audit.

## Result intake

Keep raw data, split membership, checkpoints, logs, and real Prediction Records on 319. Audit there first. Transfer only gate-approved aggregate Run Records, checksums, audits, figures with no patient-level content, and concise Failure Records.

The core evaluator performs the first acceptance pass on 319:

```bash
rtk ssh -o BatchMode=yes -o ConnectTimeout=10 319-lab-via-server '
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

## Destructive operations

Remote deletion, environment removal, job termination, checkout reset, and data replacement require explicit user approval after showing the target, impact, and recovery path. Routine harness operation is read-only or additive.
