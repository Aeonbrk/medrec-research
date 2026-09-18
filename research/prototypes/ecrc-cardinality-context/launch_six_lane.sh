#!/usr/bin/env bash
set -euo pipefail

: "${SNAPSHOT_ROOT:?set SNAPSHOT_ROOT}"
: "${TRAIN_DEV_ROOT:?set TRAIN_DEV_ROOT}"
: "${OUTPUT_ROOT:?set OUTPUT_ROOT}"
: "${RUN_REVISION:?set RUN_REVISION}"

PYTHON_BIN="${PYTHON_BIN:-python}"
GPU_IDS="${GPU_IDS:-0,1,2,3,4,5}"
IFS=',' read -r -a GPUS <<< "${GPU_IDS}"
if [[ "${#GPUS[@]}" -ne 6 ]]; then
  echo "GPU_IDS must contain exactly six comma-separated physical GPU IDs" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "${OUTPUT_ROOT}" "${OUTPUT_ROOT}/_launcher"

CUDA_VISIBLE_DEVICES="${GPUS[0]}" "${PYTHON_BIN}"   "${SCRIPT_DIR}/preflight_ecrc.py"   > "${OUTPUT_ROOT}/preflight.json"

launch() {
  local gpu="$1"
  local variant="$2"
  local seed="$3"
  local name="$4"
  local out="${OUTPUT_ROOT}/${name}"
  if [[ -e "${out}" ]]; then
    echo "refusing to reuse existing output: ${out}" >&2
    exit 3
  fi
  mkdir -p "${out}"
  nohup env CUDA_VISIBLE_DEVICES="${gpu}" "${PYTHON_BIN}"     "${SCRIPT_DIR}/run_ecrc.py"     --variant "${variant}"     --seed "${seed}"     --snapshot-root "${SNAPSHOT_ROOT}"     --train-dev-root "${TRAIN_DEV_ROOT}"     --source-revision "${RUN_REVISION}"     --output-dir "${out}"     > "${out}/stdout.log" 2>&1 &
  echo "$!" > "${out}/pid"
  echo "launched ${name} on GPU ${gpu}, pid $(cat "${out}/pid")"
}

launch "${GPUS[0]}" kind_bce   20260923 kind_bce_a
launch "${GPUS[1]}" kcond_bce  20260923 kcond_bce_a
launch "${GPUS[2]}" kind_exact 20260923 kind_exact_a
launch "${GPUS[3]}" kcond_exact 20260923 kcond_exact_a
launch "${GPUS[4]}" kind_exact 20260924 kind_exact_b
launch "${GPUS[5]}" kcond_exact 20260924 kcond_exact_b

cat <<EOF
All six lanes launched.

Monitor:
  for d in "${OUTPUT_ROOT}"/*; do
    [[ -f "$d/progress.json" ]] && echo "==== $d ====" && tail -n 20 "$d/progress.json"
  done

After all six results.json files exist:
  "${PYTHON_BIN}" "${SCRIPT_DIR}/summarize_ecrc.py" \
    --kind-bce-a "${OUTPUT_ROOT}/kind_bce_a/results.json" \
    --kcond-bce-a "${OUTPUT_ROOT}/kcond_bce_a/results.json" \
    --kind-exact-a "${OUTPUT_ROOT}/kind_exact_a/results.json" \
    --kcond-exact-a "${OUTPUT_ROOT}/kcond_exact_a/results.json" \
    --kind-exact-b "${OUTPUT_ROOT}/kind_exact_b/results.json" \
    --kcond-exact-b "${OUTPUT_ROOT}/kcond_exact_b/results.json" \
    --output "${OUTPUT_ROOT}/ecrc-comparison.json"
EOF
