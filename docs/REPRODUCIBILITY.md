# What this fingerprint can reproduce

This is an authored agent distribution plus a clean SupoClip source snapshot, additional local renderers, explicit styles, tests and editorial rules. It is **not** a dump of a live Hermes profile or a model's weights.

## Reproducible layers
- Pin this repository's commit/tag, Remotion lockfile/version, Python dependencies, FFmpeg/Chrome/OS and font files.
- Retain the exact same input bytes, reviewed source ranges/crops, word timings and render job JSON. These constrain the edit; write them to manifests along with environment/probe results.
- The creator and podcast pipelines encode the approved styles. Their technical smoke tests use explicitly synthetic fixtures, not borrowed creator footage.

## Not guaranteed
- A different LLM/provider, prompt context, ASR model, source download, platform codec or font fallback can change selection, hero wording, captions and encoded pixels. Sharing rules does not guarantee identical AI editorial decisions or bit-identical H.264.
- The original system used manual source review and iterations. These are still required. Face detection is not speaker ID. Audio/visual intensity is not a verified game-event/virality predictor.
- The premium podcast multi-clip prototype had incomplete batch validation historically; do not call every archived recipe production-proven. Synthetic renders prove the tested execution path, not a universal quality claim.
- Private histories, source caches, licensed-only sounds, OAuth/API/bot keys, model caches and accounts are excluded. Supply your own authorized inputs/providers.

Record actual smoke/build results in docs/VERIFICATION.md. Unrun platforms/formats/builds must be labelled, not inferred from adjacent tests.
