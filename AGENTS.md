# Clipping Fingerprint — repository rules
Read SOUL.md and skills/supoclip-operations/SKILL.md before clipping. CLIP_ROOT means this checkout's absolute path, not a literal shell directory. HERMES_HOME means the operator's selected Hermes profile. Never copy credentials or session state from someone else.

Preserve separate creator and podcast treatments, use actual source evidence, perform rendered-output QA and verified delivery, and provide copyable post captions. Read skills/supoclip-operations/references/short-form-editorial-principles.md for the full editorial checklist.

Entrypoints: see README.md and docs/FINGERPRINT-SETUP.md. scripts/fingerprint_creator.py (if present) is the portable fast creator renderer; scripts/podcast_pipeline.py is the approved-plan interview pipeline; scripts/creator_analyze.py generates review evidence only. Existing scripts with episode names are historical recipes, not automatic generic entrypoints and may require unavailable operator-owned media. Never fabricate missing files.

SupoClip is AGPL-3.0-or-later. Preserve upstream LICENSE and notices; Remotion and fonts retain separate terms. Review docs/ASSETS-AND-LICENSES.md. Do not publish source videos or unlicensed SFX.

Original project development conventions are in docs/UPSTREAM-AGENTS.md. Do not alter lockfiles casually. Never restart active workers without checking outstanding jobs. Never edit another Hermes profile or publish a campaign unless explicitly asked.
