# Local Data Root Playbook

The Local Data Root on 319 is the only home for restricted EHR inputs, derived snapshots, patient split membership, real Prediction Records, checkpoints, and private run artifacts. It must be outside both the 319 repository checkout and the archived `New-Search` checkout. Do not mirror it to the MacBook harness.

## Configure

Choose a protected path or mount on 319 and expose it only to remote commands that need data.

```bash
export MEDREC_DATA_ROOT=/absolute/path/outside/git/medrec-data
test -d "$MEDREC_DATA_ROOT"
```

Do not commit this path to configuration or Run Records, and do not include it in remote logs copied to the Mac. Public-safe records identify snapshots by stable manifest identity and checksum, not remote location.

## Suggested layout

```text
$MEDREC_DATA_ROOT/
  sources/       Immutable licensed or private source deliveries
  snapshots/     Versioned processed dataset snapshots
  splits/        Patient-level split membership
  predictions/   Real per-visit Prediction Records
  checkpoints/   Model weights
  runs/          Restricted logs and intermediate artifacts
  baseline-src/  Pinned external source checkouts
  keys/          Private membership-HMAC keys with restricted permissions
```

Filesystem layout is operational, not scientific identity. Build a restricted Dataset Manifest on 319 with `DatasetManifest.from_memberships(...)` while patient and eligible-visit membership is in memory. Pass a private HMAC key of at least 32 bytes from `keys/`; never place that key, raw membership, or command-line key material in the manifest or logs. The builder rejects patient overlap, duplicate visits, and visits assigned outside their patient's split before returning public-safe digests.

## Handling rules

- Keep source deliveries immutable. Create a new snapshot instead of editing one in place.
- Generate train, validation, and test membership at patient level and store membership only under `splits/`.
- Give each snapshot an immutable content digest. Use private HMAC-derived membership digests for restricted patient and eligible-visit sets; plain SHA-256 membership digests are limited to public synthetic fixtures.
- Pass data locations through environment variables or local ignored configuration.
- Write aggregate public-safe results separately from restricted per-visit outputs.
- Review every artifact before copying it into Git. File extension alone does not establish safety.

## Failure handling

If restricted content enters Git history, stop work and treat it as an incident. Removing the working-tree file is insufficient because Git retains prior objects. Do not rewrite or publish history without explicit authorization and a verified remediation plan.
