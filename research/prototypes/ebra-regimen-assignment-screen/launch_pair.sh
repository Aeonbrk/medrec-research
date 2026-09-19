#!/usr/bin/env bash
set -euo pipefail

SNAPSHOT_ROOT="${SNAPSHOT_ROOT:-/root/zhb/medrec-data/snapshots/molerec-table1-c721-www23}"
TRAIN_DEV_ROOT="${TRAIN_DEV_ROOT:-/root/zhb/medrec-data/idea008/gate01-train-dev-5752596a-20260913a}"
OUT_ROOT="${OUT_ROOT:-/root/zhb/medrec-data/prototypes/ebra-regimen-assignment-screen}"
PYTHON_BIN="${PYTHON_BIN:-/root/anaconda3/envs/medrec-molerec-table1/bin/python}"
EPOCHS="${EPOCHS:-15}"
GPU_FIXED="${GPU_FIXED:-0}"
GPU_EBRA="${GPU_EBRA:-1}"

REVISION="$(git rev-parse HEAD)"
if [[ -n "$(git status --porcelain=v1 --untracked-files=all)" ]]; then
  echo "ERROR: source checkout is not clean" >&2
  exit 2
fi

mkdir -p "$OUT_ROOT/logs"
"$PYTHON_BIN" research/prototypes/ebra-regimen-assignment-screen/preflight_ebra.py \
  --snapshot-root "$SNAPSHOT_ROOT" \
  --train-dev-root "$TRAIN_DEV_ROOT" \
  --source-revision "$REVISION" \
  > "$OUT_ROOT/preflight.json"
echo "EBRA preflight PASS at $REVISION"

for arm in fixed_multilabel ebra_assignment; do
  out="$OUT_ROOT/$arm"
  if [[ -d "$out" && -n "$(ls -A "$out" 2>/dev/null || true)" ]]; then
    echo "ERROR: output is not empty: $out" >&2
    exit 3
  fi
  mkdir -p "$out"
done

CUDA_VISIBLE_DEVICES="$GPU_FIXED" "$PYTHON_BIN" \
  research/prototypes/ebra-regimen-assignment-screen/run_ebra.py \
  --arm fixed_multilabel --epochs "$EPOCHS" \
  --snapshot-root "$SNAPSHOT_ROOT" --train-dev-root "$TRAIN_DEV_ROOT" \
  --source-revision "$REVISION" --output-dir "$OUT_ROOT/fixed_multilabel" \
  > "$OUT_ROOT/logs/fixed_multilabel.log" 2>&1 &
fixed_pid=$!

CUDA_VISIBLE_DEVICES="$GPU_EBRA" "$PYTHON_BIN" \
  research/prototypes/ebra-regimen-assignment-screen/run_ebra.py \
  --arm ebra_assignment --epochs "$EPOCHS" \
  --snapshot-root "$SNAPSHOT_ROOT" --train-dev-root "$TRAIN_DEV_ROOT" \
  --source-revision "$REVISION" --output-dir "$OUT_ROOT/ebra_assignment" \
  > "$OUT_ROOT/logs/ebra_assignment.log" 2>&1 &
ebra_pid=$!

failed=0
if ! wait "$fixed_pid"; then
  echo "FAILED: fixed_multilabel" >&2
  failed=1
else
  echo "COMPLETE: fixed_multilabel"
fi
if ! wait "$ebra_pid"; then
  echo "FAILED: ebra_assignment" >&2
  failed=1
else
  echo "COMPLETE: ebra_assignment"
fi
if [[ "$failed" -ne 0 ]]; then
  echo "At least one EBRA lane failed; do not summarize partial science." >&2
  exit 4
fi

"$PYTHON_BIN" research/prototypes/ebra-regimen-assignment-screen/summarize_ebra.py \
  --fixed "$OUT_ROOT/fixed_multilabel/results.json" \
  --ebra "$OUT_ROOT/ebra_assignment/results.json" \
  --output "$OUT_ROOT/result.json" \
  > "$OUT_ROOT/comparison.stdout.json"
echo "EBRA aggregate: $OUT_ROOT/result.json"
