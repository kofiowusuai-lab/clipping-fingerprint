# Release verification — fingerprint 1.0.0

This records real execution, not invented example output. All fresh video fixtures below are explicitly synthetic test patterns/tones with test-label captions. They do not certify human editorial quality, speech alignment, source rights or virality.

## Passed

- **Native renderer:** final security-pinned dependency tree rendered creator and podcast outputs, each H.264/AAC, 360×640, 30 fps, 72 frames / 2.4 seconds. Both fully decoded. Creator hero/caption pixels and all-frame picture checks passed; podcast all-frame check and checksum-backed resume passed. See `verification/native-smoke.json`.
- **Final Linux container:** image `sha256:a97d6b951ea6f6296b5d783003e681975823b413fa1738e52cf9ce25a749d7d5` built successfully for **linux/arm64**. The final image rendered both formats successfully with runtime network disabled, user `renderer`, dropped capabilities and no-new-privileges. Container exit was 0. The same 72-frame codec/timing/full-decode, persistent creator hero/caption, picture-regression and podcast-resume checks passed. See `verification/container-smoke.json`.
- **Python unit/technical suite:** 45 tests ran, successful, with 3 explicit opt-in skips. The skipped paths cover optional local-checkpoint/full integration/extra Chrome tests; they are not counted as exercised. The separate real render smoke above was executed.
- **JavaScript:** all 54 unit tests passed; TypeScript typecheck passed. Final pnpm peer check reported no dependency issues.
- **Additional graphics:** real native full-composition smoke rendered and decoded 60 frames, checked actual lower-third pixels, white-transition peak/recovery and endcard pixels. Separate full-creator graphics smokes generated transparent RGBA frames for both clean-energy (30 fps) and aggressive (24 fps), with visible graphics and output-collision refusal checks. These optional test graphics are not the default house edit.
- **Reviewed-pause trim:** an explicit synthetic removal produced the expected 60-frame / 2.0-second result from a 72-frame source; full decode and A/V timing checks passed. This tests an instructed cut, not automatic silence recognition.
- **Hermes checkout installer:** installed SOUL/skills and scoped configuration into an isolated fresh test home using the actual Hermes CLI; read back working directory and MCP configuration. No original auth store or private `.env` was installed. Existing-home refusal and dry-run non-writing behaviour passed tests.
- **Native Hermes distribution installer:** installed the authored distribution from a clean Git-publish-set-only fixture into an isolated home; verified all three authored skills and SOUL existed, with no auth store/private `.env`. A dependency-populated working directory initially failed the installer's symlink refusal, so the correct distribution test uses the clean published source set. Remote installs likewise clone the clean repository, not local node_modules.
- **MCP bridge:** real stdio initialization, tool discovery (17 tools) and API health read returned healthy. That isolated call intentionally had `auth_mode=none` / `authenticated=false`; it does not certify task authorization or provider inference. Supply your own keys/account.
- **Compose:** standalone Docker Compose 5.1.3 parsed `compose.fingerprint.yml` successfully. This host lacked the `docker compose` plugin; use the installed `docker-compose` equivalent when necessary. The isolated render image was exercised directly, not the whole application stack.
- **Publish-set security:** the repository file audit passed, including comparison against the original installation's locally supplied secret values without logging or exporting those values. Credentials, profile runtime state, original Telegram routing, source videos, stale smoke artifacts and uncleared fonts are excluded. This is not a comprehensive penetration test.

## Dependency security gate

An initial final-image Trivy 0.76.1 scan **failed** on two fixable critical advisories in rspack's bundled tinypool 1.1.1: CVE-2026-104848 and CVE-2026-104849. They were not suppressed or hidden by deleting metadata. The exported workspace now pins `@rspack/core=2.2.9` (bundled tinypool 2.2.0) and `webpack=5.112.0` for the schema-utils peer requirement, with an updated committed pnpm lockfile. All Remotion packages remain exactly 4.0.539.

Native unit, type, peer and real creator/podcast/optional-graphics smoke tests were rerun after these pins. The final image above was rebuilt and smoke-tested.

**Final exact-image critical scan: PASSED.** Trivy produced a complete report for the exact image ID above with zero fixable CRITICAL findings. A repeat using the just-downloaded cached vulnerability database, with runtime network disabled, returned exit code 0. See `verification/image-security.json`. The initial failed scan was not suppressed; the vulnerable bundled dependency was replaced through explicit version pins and the lockfile, then the image was rebuilt and retested. The gate follows the inherited project policy (`--severity CRITICAL --ignore-unfixed`); it does not assert that HIGH/lower or unfixed findings are absent.

## Environment and limits

Native tests: macOS/arm64, Python 3.12.13, Node 22.16.0, pnpm 11.24.0, FFmpeg 8.1, installed Chrome, NumPy 2.4.4, Pillow 13.0.0, OpenCV 4.13.0. Hermes installation tested: 0.21.0.

Container base pins preserve the source project's patched Python 3.11.17 / Node 22.23.4 choices; image tools include FFmpeg 7.1.5 and Debian Chromium. Package-manager installation used the frozen committed lockfile.

Freshly tested platforms are native macOS/arm64 and Linux/arm64 container. No Windows, Linux/amd64, GPU, HDR/VFR/exotic-codec matrix, automatic gameplay-event understanding or production deployment claim is made. The full inherited web/API/worker stack and its independent provider credentials were not launched or migrated for this export. No new ASR model was downloaded, no paid service activated, and no real clips published.

Generated MP4s and private/raw logs remain local and excluded; sanitized technical reports and checksums are included. Input-bytes/tool/version/approved-plan parity matters; this is not a guarantee of identical AI editorial decisions or cross-platform encoded bytes.
