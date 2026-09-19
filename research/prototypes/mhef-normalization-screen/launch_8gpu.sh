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
  research/prototypes/mhef-normalization-screen/preflight_mhef.py \
  --snapshot-root "$SNAPSHOT_ROOT" \
  --train-dev-root "$TRAIN_DEV_ROOT" \
  --source-revision "$REVISION" \
  > "$OUT_ROOT/preflight.json"

echo "MHEF preflight PASS at $REVISION"

lanes=(
  mhef_independent_add
  coupled_budget_add
  wide_global_add
  mhef_independent_concat
  coupled_budget_concat
  private_only_add
  hash_partition_a_add
  hash_partition_b_add
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
    research/prototypes/mhef-normalization-screen/run_mhef.py \
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
  echo "At least one MHEF lane failed; do not summarize partial science." >&2
  exit 4
fi

"$PYTHON_BIN" \
  research/prototypes/mhef-normalization-screen/summarize_mhef.py \
  --root "$OUT_ROOT" \
  --output "$OUT_ROOT/comparison.json" \
  > "$OUT_ROOT/comparison.stdout.json"

echo "All eight MHEF lanes complete. Aggregate: $OUT_ROOT/comparison.json"
