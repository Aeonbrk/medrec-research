#!/bin/bash
# SafeDrug Family Baseline Runner for 319-wild
# Supports SafeDrug, RETAIN, and LEAP reproduction runs.

set -euo pipefail
umask 077

# ============================================================================
# Profile & Environment Arguments
# ============================================================================
PROFILE="${1:-}"
if [ -z "$PROFILE" ]; then
    echo "Error: Profile argument required (safedrug, retain, or leap-safedrug)" >&2
    exit 1
fi

case "$PROFILE" in
    safedrug)
        ENTRYPOINT="SafeDrug.py"
        MODEL_PREFIX="SafeDrug"
        REQUIRED_INPUTS=(
            "data/output/records_final.pkl"
            "data/output/voc_final.pkl"
            "data/output/ddi_A_final.pkl"
            "data/output/ddi_mask_H.pkl"
            "data/output/atc3toSMILES.pkl"
        )
        ;;
    retain)
        ENTRYPOINT="Retain.py"
        MODEL_PREFIX="Retain"
        REQUIRED_INPUTS=(
            "data/output/records_final.pkl"
            "data/output/voc_final.pkl"
            "data/output/ddi_A_final.pkl"
        )
        ;;
    leap-safedrug|leap)
        PROFILE="leap-safedrug"
        ENTRYPOINT="Leap.py"
        MODEL_PREFIX="Leap"
        REQUIRED_INPUTS=(
            "data/output/records_final.pkl"
            "data/output/voc_final.pkl"
            "data/output/ddi_A_final.pkl"
        )
        ;;
    *)
        echo "Error: Unknown profile '$PROFILE'. Must be safedrug, retain, or leap-safedrug." >&2
        exit 1
        ;;
esac

# Validate required environment variables
MEDREC_RUN_ID="${MEDREC_RUN_ID:-}"
if [[ ! "$MEDREC_RUN_ID" =~ ^[A-Za-z0-9._-]{1,128}$ ]]; then
    echo "Error: MEDREC_RUN_ID is missing or invalid: '$MEDREC_RUN_ID'" >&2
    exit 1
fi

MEDREC_DATA_ROOT="${MEDREC_DATA_ROOT:-}"
if [ -z "$MEDREC_DATA_ROOT" ] || [ "${MEDREC_DATA_ROOT:0:1}" != "/" ]; then
    echo "Error: MEDREC_DATA_ROOT must be an absolute path: '$MEDREC_DATA_ROOT'" >&2
    exit 1
fi

SAFEDRUG_ROOT="${SAFEDRUG_ROOT:-/root/zhb/SafeDrug}"
if [ ! -d "$SAFEDRUG_ROOT" ]; then
    echo "Error: SAFEDRUG_ROOT directory not found: '$SAFEDRUG_ROOT'" >&2
    exit 1
fi

CONDA_ENV="${CONDA_ENV:-medrec-gamenet}"
PHYSICAL_GPU="${CUDA_VISIBLE_DEVICES:-0}"
LOGICAL_CUDA="0"
# Upstream expects CUDA_VISIBLE_DEVICES to isolate the single device as logical device 0
export CUDA_VISIBLE_DEVICES="$PHYSICAL_GPU"

# Harness repository directory (where this script lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARNESS_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Output and artifact paths
OUTPUT_DIR="${MEDREC_DATA_ROOT}/baselines/${PROFILE}/${MEDREC_RUN_ID}"
CHECKPOINT_DIR="${OUTPUT_DIR}/saved"
TRAIN_LOG="${OUTPUT_DIR}/train.log"
TEST_LOG="${OUTPUT_DIR}/test.log"
STATUS_FILE="${OUTPUT_DIR}/status.json"
RESULT_FILE="${OUTPUT_DIR}/result.json"
INPUT_HASHES_FILE="${OUTPUT_DIR}/input_hashes.json"

MODEL_NAME="${MODEL_PREFIX}_${MEDREC_RUN_ID}"
SYMLINK_PATH="${SAFEDRUG_ROOT}/src/saved/${MODEL_NAME}"

mkdir -p "$OUTPUT_DIR" "$CHECKPOINT_DIR"
mkdir -p "${SAFEDRUG_ROOT}/src/saved"

START_TIME="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
TRAIN_START=""
TRAIN_END=""
FINISHED_TIME=""
CURRENT_STATE="running"
CURRENT_STAGE="prepare"
LAST_EXIT_CODE=""

# ============================================================================
# Status Writing Helper
# ============================================================================
write_status() {
    local state="$1"
    local stage="$2"
    local exit_code="$3"
    local t_start="${4:-null}"
    local t_end="${5:-null}"
    local t_finish="${6:-null}"

    CURRENT_STATE="$state"
    CURRENT_STAGE="$stage"
    LAST_EXIT_CODE="$exit_code"

    local exit_code_val="null"
    if [ -n "$exit_code" ] && [ "$exit_code" != "null" ]; then
        exit_code_val="$exit_code"
    fi

    local t_start_val="null"
    if [ -n "$t_start" ] && [ "$t_start" != "null" ]; then
        t_start_val="\"$t_start\""
    fi

    local t_end_val="null"
    if [ -n "$t_end" ] && [ "$t_end" != "null" ]; then
        t_end_val="\"$t_end\""
    fi

    local t_finish_val="null"
    if [ -n "$t_finish" ] && [ "$t_finish" != "null" ]; then
        t_finish_val="\"$t_finish\""
    fi

    local tmp_status="${STATUS_FILE}.tmp.$$"
    cat > "$tmp_status" <<EOF
{
  "schema_version": 1,
  "baseline_id": "${PROFILE}",
  "run_id": "${MEDREC_RUN_ID}",
  "attempt": 1,
  "model_name": "${MODEL_NAME}",
  "state": "${state}",
  "stage": "${stage}",
  "exit_code": ${exit_code_val},
  "started_at": "${START_TIME}",
  "training_started_at": ${t_start_val},
  "training_ended_at": ${t_end_val},
  "finished_at": ${t_finish_val},
  "physical_gpu": ${PHYSICAL_GPU},
  "logical_cuda_device": ${LOGICAL_CUDA}
}
EOF
    mv "$tmp_status" "$STATUS_FILE"
}

# Write initial status
write_status "running" "prepare" null null null null

# ============================================================================
# Cleanup Trap
# ============================================================================
cleanup() {
    local exit_code=$?
    trap - EXIT INT TERM

    # Unlink symlink only if it matches our exact target
    if [ -L "$SYMLINK_PATH" ]; then
        local real_link
        local real_target
        real_link="$(realpath "$SYMLINK_PATH" 2>/dev/null || true)"
        real_target="$(realpath "$CHECKPOINT_DIR" 2>/dev/null || true)"
        if [ "$real_link" = "$real_target" ] && [ -n "$real_target" ]; then
            rm -f "$SYMLINK_PATH"
        fi
    fi

    if [ "$CURRENT_STATE" != "completed" ]; then
        local now_iso
        now_iso="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
        if [ $exit_code -ne 0 ]; then
            write_status "failed" "$CURRENT_STAGE" "$exit_code" "$TRAIN_START" "$TRAIN_END" "$now_iso"
        else
            write_status "interrupted" "$CURRENT_STAGE" 1 "$TRAIN_START" "$TRAIN_END" "$now_iso"
        fi
    fi
}
trap cleanup EXIT INT TERM

# ============================================================================
# Phase 1: Input Preflight & Hashing
# ============================================================================
echo "=== [Phase 1/5] Input Preflight & Hashing ==="
cd "$SAFEDRUG_ROOT"

# Check and hash inputs
python3 -c '
import hashlib, json, os, sys
from pathlib import Path

safedrug_root = Path(sys.argv[1])
required_inputs = sys.argv[2:]
hashes = {}

for rel_path in required_inputs:
    full_path = safedrug_root / rel_path
    if not full_path.is_file() or full_path.is_symlink():
        print(f"Error: Required input {rel_path} is missing or is symlink", file=sys.stderr)
        sys.exit(1)
    hasher = hashlib.sha256()
    with open(full_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    hashes[rel_path] = hasher.hexdigest()

out_path = Path(sys.argv[len(sys.argv)-1])
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(hashes, f, indent=2)
' "$SAFEDRUG_ROOT" "${REQUIRED_INPUTS[@]}" "$INPUT_HASHES_FILE"

echo "Input hashes recorded in $INPUT_HASHES_FILE"

# Setup atomic symlink for checkpoints
if [ -e "$SYMLINK_PATH" ] || [ -L "$SYMLINK_PATH" ]; then
    echo "Error: Symlink collision! $SYMLINK_PATH already exists" >&2
    exit 1
fi
ln -s "$CHECKPOINT_DIR" "$SYMLINK_PATH"
echo "Created run-scoped symlink: $SYMLINK_PATH -> $CHECKPOINT_DIR"

# ============================================================================
# Phase 2: Environment Activation
# ============================================================================
echo "=== [Phase 2/5] Environment Activation ==="
source /root/anaconda3/etc/profile.d/conda.sh
conda activate "$CONDA_ENV"
echo "Activated Conda environment: $CONDA_ENV ($(which python))"

# ============================================================================
# Phase 3: Model Training (50 Epochs)
# ============================================================================
echo "=== [Phase 3/5] Model Training ($ENTRYPOINT) ==="
TRAIN_START="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
write_status "running" "training" null "$TRAIN_START" null null

cd "${SAFEDRUG_ROOT}/src"

echo "Launching training on GPU $PHYSICAL_GPU..."
set +e
python "$ENTRYPOINT" --model_name "$MODEL_NAME" --cuda 0 2>&1 | tee "$TRAIN_LOG"
TRAIN_EXIT="${PIPESTATUS[0]}"
set -eu

TRAIN_END="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

if [ "$TRAIN_EXIT" -ne 0 ]; then
    echo "Error: Training exited with code $TRAIN_EXIT" >&2
    write_status "failed" "training" "$TRAIN_EXIT" "$TRAIN_START" "$TRAIN_END" "$TRAIN_END"
    exit "$TRAIN_EXIT"
fi

# ============================================================================
# Phase 4: Checkpoint Selection & Native Test
# ============================================================================
echo "=== [Phase 4/5] Checkpoint Selection & Native Test ==="
write_status "running" "selecting" null "$TRAIN_START" "$TRAIN_END" null

# Parse training log to get best_epoch and verify 50 epochs
BEST_EPOCH="$(python3 -c '
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from parse_safedrug_family_results import parse_train_log
with open(sys.argv[2], encoding="utf-8", errors="replace") as f:
    res = parse_train_log(f.read())
print(res["best_epoch"])
' "${HARNESS_ROOT}/baselines/scripts" "$TRAIN_LOG")"

echo "Selected best_epoch: $BEST_EPOCH"

# Select unique checkpoint
CHECKPOINT_INFO="$(python3 -c '
import json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from parse_safedrug_family_results import select_checkpoint
res = select_checkpoint(Path(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5])
print(json.dumps(res))
' "${HARNESS_ROOT}/baselines/scripts" "$CHECKPOINT_DIR" "$BEST_EPOCH" "$PROFILE" "$MODEL_NAME")"

CHECKPOINT_PATH="$(python3 -c "import json, sys; print(json.loads(sys.argv[1])['path'])" "$CHECKPOINT_INFO")"
CHECKPOINT_BASENAME="$(python3 -c "import json, sys; print(json.loads(sys.argv[1])['basename'])" "$CHECKPOINT_INFO")"

echo "Selected checkpoint path: $CHECKPOINT_PATH (basename: $CHECKPOINT_BASENAME)"

write_status "running" "testing" null "$TRAIN_START" "$TRAIN_END" null

echo "Running native --Test evaluation..."
set +e
if [ "$PROFILE" = "retain" ]; then
    # Retain.py joins "saved", args.model_name, args.resume_path -> needs basename only
    python "$ENTRYPOINT" --model_name "$MODEL_NAME" --Test --resume_path "$CHECKPOINT_BASENAME" --cuda 0 2>&1 | tee "$TEST_LOG"
else
    # SafeDrug and Leap load args.resume_path directly
    python "$ENTRYPOINT" --model_name "$MODEL_NAME" --Test --resume_path "$CHECKPOINT_PATH" --cuda 0 2>&1 | tee "$TEST_LOG"
fi
TEST_EXIT="${PIPESTATUS[0]}"
set -eu

if [ "$TEST_EXIT" -ne 0 ]; then
    echo "Error: Test evaluation exited with code $TEST_EXIT" >&2
    NOW_ISO="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    write_status "failed" "testing" "$TEST_EXIT" "$TRAIN_START" "$TRAIN_END" "$NOW_ISO"
    exit "$TEST_EXIT"
fi

# ============================================================================
# Phase 5: Result Assembly & Validation
# ============================================================================
echo "=== [Phase 5/5] Result Assembly & Validation ==="
write_status "running" "parsing" null "$TRAIN_START" "$TRAIN_END" null

# Get git revisions and environment sha256
SAFEDRUG_REV="$(git -c safe.directory="$SAFEDRUG_ROOT" -C "$SAFEDRUG_ROOT" rev-parse HEAD)"

# Compute adapter revision (SHA-256 over fixed ordered byte stream of runner + parser)
ADAPTER_REV="$(python3 -c '
import hashlib, sys
from pathlib import Path
runner_path = Path(sys.argv[1]) / "baselines/scripts/run_safedrug_family_319.sh"
parser_path = Path(sys.argv[1]) / "baselines/scripts/parse_safedrug_family_results.py"

h = hashlib.sha256()
for p, rel in [(runner_path, "baselines/scripts/run_safedrug_family_319.sh"), (parser_path, "baselines/scripts/parse_safedrug_family_results.py")]:
    h.update(rel.encode("utf-8"))
    h.update(b"\0")
    h.update(p.read_bytes())
    h.update(b"\0")
print("sha256:" + h.hexdigest())
' "$HARNESS_ROOT")"

ENV_SHA256="$(conda list --explicit | sha256sum | awk '{print $1}')"

# Run strict parser
python3 "${HARNESS_ROOT}/baselines/scripts/parse_safedrug_family_results.py" \
    --baseline-id "$PROFILE" \
    --model-name "$MODEL_NAME" \
    --train-log "$TRAIN_LOG" \
    --test-log "$TEST_LOG" \
    --status-json "$STATUS_FILE" \
    --checkpoint-dir "$CHECKPOINT_DIR" \
    --output-json "$RESULT_FILE" \
    --source-revision "$SAFEDRUG_REV" \
    --adapter-revision "$ADAPTER_REV" \
    --environment-sha256 "$ENV_SHA256" \
    --input-hashes-json "$INPUT_HASHES_FILE"

FINISHED_TIME="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
write_status "completed" "terminal" 0 "$TRAIN_START" "$TRAIN_END" "$FINISHED_TIME"

echo "================================================"
echo "Reproduction Run Completed Successfully: $PROFILE"
echo "Result file: $RESULT_FILE"
echo "Status file: $STATUS_FILE"
echo "================================================"
