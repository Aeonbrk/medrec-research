#!/usr/bin/env bash
set -euo pipefail

: "${SNAPSHOT_ROOT:?set SNAPSHOT_ROOT to the canonical MoleRec snapshot}"
: "${TRAIN_DEV_ROOT:?set TRAIN_DEV_ROOT to the frozen MIMIC-III Train/Dev artifact root}"
: "${OUT_ROOT:?set OUT_ROOT to an output directory outside the source checkout}"
PYTHON_BIN="${PYTHON_BIN:-python}"
REVISION="$(git rev-parse HEAD)"

if [[ -n "$(git status --porcelain=v1 --untracked-files=all)" ]]; then
  echo "ERROR: source checkout is not clean" >&2
  exit 2
fi

mkdir -p "$OUT_ROOT/logs"

CUDA_VISIBLE_DEVICES=0 "$PYTHON_BIN" \
  research/prototypes/memb-mutual-binding-screen/preflight_memb.py \
  --snapshot-root "$SNAPSHOT_ROOT" \
  --train-dev-root "$TRAIN_DEV_ROOT" \
  --source-revision "$REVISION" \
  > "$OUT_ROOT/preflight.json"

echo "MEMB preflight PASS at $REVISION"

lanes=(
  mutual_code
  scale2_code
  specificity_code
  foundation_code_anchor
  mutual_local
  scale2_local
  specificity_local
  prediction_local_anchor
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
  CUDA_VISIBLE_DEVICES="$gpu" "$PYTHON_BIN" \
    research/prototypes/memb-mutual-binding-screen/run_memb.py \
    --lane "$lane" \
    --snapshot-root "$SNAPSHOT_ROOT" \
    --train-dev-root "$TRAIN_DEV_ROOT" \
    --source-revision "$REVISION" \
    --output-dir "$out" \
    > "$OUT_ROOT/logs/$lane.log" 2>&1 &
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
  echo "At least one MEMB lane failed; do not summarize partial science." >&2
  exit 4
fi

"$PYTHON_BIN" \
  research/prototypes/memb-mutual-binding-screen/summarize_memb.py \
  --root "$OUT_ROOT" \
  --output "$OUT_ROOT/comparison.json" \
  > "$OUT_ROOT/comparison.stdout.json"

echo "All eight MEMB lanes complete. Aggregate: $OUT_ROOT/comparison.json"
