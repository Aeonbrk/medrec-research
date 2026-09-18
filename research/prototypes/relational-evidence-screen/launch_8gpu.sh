#!/usr/bin/env bash
set -euo pipefail

SNAPSHOT_ROOT="${SNAPSHOT_ROOT:-/root/zhb/medrec-data/snapshots/molerec-table1-c721-www23}"
TRAIN_DEV_ROOT="${TRAIN_DEV_ROOT:-/root/zhb/medrec-data/idea008/gate01-train-dev-5752596a-20260913a}"
OUT_ROOT="${OUT_ROOT:-/root/zhb/medrec-data/prototypes/relational-evidence-screen}"
PYTHON_BIN="${PYTHON_BIN:-/root/anaconda3/envs/medrec-molerec-table1/bin/python}"

REVISION="$(git rev-parse HEAD)"

if [[ -n "$(git status --porcelain=v1 --untracked-files=all)" ]]; then
  echo "ERROR: source checkout is not clean" >&2
  exit 2
fi

mkdir -p "$OUT_ROOT/logs"

CUDA_VISIBLE_DEVICES=0 "$PYTHON_BIN"   research/prototypes/relational-evidence-screen/preflight_screen.py   --snapshot-root "$SNAPSHOT_ROOT"   --train-dev-root "$TRAIN_DEV_ROOT"   --source-revision "$REVISION"   > "$OUT_ROOT/preflight.json"

echo "Relational evidence preflight PASS at $REVISION"

lanes=(
  resolution_visit_s1
  resolution_code_s1
  resolution_visit_s2
  resolution_code_s2
  resolution_visit_s3
  resolution_code_s3
  unary_code_canonical
  relational_code_canonical
)

pids=()
for gpu in 0 1 2 3 4 5 6 7; do
  lane="${lanes[$gpu]}"
  out="$OUT_ROOT/$lane"

  if [[ -d "$out" && -n "$(ls -A "$out" 2>/dev/null || true)" ]]; then
    echo "ERROR: output is not empty: $out" >&2
    exit 3
  fi

  mkdir -p "$out"
  echo "Launching GPU $gpu -> $lane"

  CUDA_VISIBLE_DEVICES="$gpu" "$PYTHON_BIN"     research/prototypes/relational-evidence-screen/run_screen.py     --lane "$lane"     --snapshot-root "$SNAPSHOT_ROOT"     --train-dev-root "$TRAIN_DEV_ROOT"     --source-revision "$REVISION"     --output-dir "$out"     > "$OUT_ROOT/logs/$lane.log" 2>&1 &

  pids+=("$!")
done

failed=0
for i in "${!pids[@]}"; do
  if ! wait "${pids[$i]}"; then
    echo "FAILED: ${lanes[$i]}" >&2
    failed=1
  else
    echo "COMPLETE: ${lanes[$i]}"
  fi
done

if [[ "$failed" -ne 0 ]]; then
  echo "At least one lane failed; do not summarize partial science." >&2
  exit 4
fi

"$PYTHON_BIN"   research/prototypes/relational-evidence-screen/summarize_screen.py   --root "$OUT_ROOT"   --output "$OUT_ROOT/comparison.json"   > "$OUT_ROOT/comparison.stdout.json"

echo "All eight lanes complete. Aggregate: $OUT_ROOT/comparison.json"
