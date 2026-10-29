# Graphics job contract (local optional prototype)

Invoke `node render.mjs /absolute/job.json`. Existing required keys unchanged: `videoPath`, `fontPath`, `outputPath`, `style: clean|bold`, `headline` (may be empty), `headlineDuration`, `width`, `height`, `fps`, `durationInFrames`, `words: [{text,start,end}]`. Optional legacy `headlineAccent`, `strikeWords` (now max100, each max40 characters), inclusive `frameRange: [first,last]` remain supported. All timing is edited-timeline seconds; no milliseconds. No extension to clip duration: endcard replaces picture during its interval and keeps original speech unless render muted. No branding, music, sound effects, stock footage, inference or automatic speaker/face selection.

All new keys optional. Unknown nested keys rejected, no user CSS accepted. Colors strictly `#RRGGBB`. Numbers finite. Ratio dimensions use composition width for font/width/x; height for y/bottom. Absolute pixel offsets only where specified. Users must place graphics to avoid faces/captions/platform UI; no automatic collision solver. Long single words are never split even when above maxChars.

## captionStyle

- `fontSizeRatio`: .02.. .2; default bold .095, clean .078.
- `position: {bottomRatio: 0.. .9, sidesRatio: 0.. .4}`; defaults .19 / .065.
- `maxWords`: integer 1..12 (default 3); `maxChars`: integer 1..100 (default 21). Existing punctuation/gap grouping retained; no accumulating list.
- `color` default white; `activeColor` default bold yellow #ffe000; clean remains white unless explicitly configured.
- `strokeColor` default black; `strokeWidth` 0..8 px (default 0); existing default shadow preserved.
- `shadow: {color, blur:0..30, offsetX:-30..30, offsetY:-30..30}`; when supplied defaults black,5,0,2. Set blur and offsets 0 to disable.
- `entrance: {scale:.5..1.5, translateY:-200..200, duration:.01..2}`; pixels/seconds, default bold .97→1 over 4 frames, clean no scale, translate 0.
- `keywords: {word: {scale:.5..2, color, offsetX:-100..100, offsetY:-100..100}}` max100 keys, each1..40 letters/digits/apostrophes/hyphens. Keys matched case-insensitive, ignoring punctuation. Color active only while word is spoken; scale/offset smoothstep ease in/out over `keywordEaseDuration` seconds (default .08, range .001.. .5), constrained to half the word duration on each edge. Defaults scale1, offsets0; no abrupt transform toggles.
- `strikeColor` default #ff4148; `strikeDuration` .01..2 seconds, default .22; `strikeWidth` .5..30 absolute pixels, default width/720*5 (7.5px at1080). Inline strike overrides keyword color and disappears with normal caption group. Existing three-target jobs remain valid; max100 is intentional expansion.

## headlineStyle

`{topRatio:0.. .9, sidesRatio:0.. .4, fontSizeRatio:.02.. .2, color, accentColor, strokeColor, strokeWidth:0..8}`. Defaults top .075 / sides .07 / font .075 / white / legacy headlineAccent / black / 0. Accent applies last newline-separated line, matching legacy behavior. Existing headlineDuration/five-frame fade retained.

## Timed graphics

Common shape: `{start,end,xRatio?,yRatio?,widthRatio?,fontSizeRatio?,color?,backgroundColor?}`. Required interval `0 <= start < end <= duration`; active start inclusive, end exclusive. x/y 0..1; width .05..1; font .01.. .2. Defaults x .065, y .84, width .87, font .045, white on #101014, internal width*.02 padding. All positioning is absolute (not center anchor).

- `lowerThirds: [{...common, name, title?, entranceDuration?}]`: name max80 chars; title max100, rendered65% size. Smoothstep opacity and subtle width*.015 upward entrance, default .15s; configurable0..2 seconds (0 disables), constrained to interval duration. Default y .84 avoids standard caption region; adjust for platform safe areas.
- `overlays: [{...common, text}]` OR `[{...common, imagePath}]`: exactly one; text max200; raster image auto height, capped half frame height. No automatic fade.
- `endcard: {...common, text, subtitle?, imagePath?}`: text required max120, subtitle max200. Full-frame background with centered text block; default y .35; optional image width40%, height capped30%. No appended video/audio.
- Max100 lower-thirds/overlays each. No assets or graphics present unless explicitly supplied.

## Prepared footage / transition

- `background: {color, fit: 'contain'|'cover', blur:0..60}`: default #101014, contain, no blur. Positive blur adds muted cover duplicate underneath foreground (not blur applied to foreground).
- `supportingVideo: {videoPath, layout:'side-by-side'|'stacked', fit?:'contain'|'cover'}`: equal halves, synchronized from time zero, supporting audio ALWAYS muted. Default supporting fit cover. Prepared local videos only; no trims, timeline offsets, duration probing or face-aware crops here. Caller must ensure supporting footage spans composition duration. Primary audio only.
- `transitions: [{time,rise?,fall?,color?,opacity?}]`: max100 entries; smoothstep solid-color luminance bloom overlay, peak at time, default white / opacity1 / rise .1s / fall 8/30s. rise/fall .01..2; opacity0..1. Entire envelope must fit clip. This replaces a *visual* post-FFmpeg flash pass, not the prepared audio mix; no riser added. Overlays transition too. Do not double-apply old flash. Distinct entries may overlap (alpha composite).

## Assets / encoding

Assets must be absolute existing readable local files. Video extensions .mp4/.mov/.webm/.mkv; fonts .ttf/.otf/.woff/.woff2; graphics .png/.jpg/.jpeg/.webp (no SVG/URLs). Each explicitly requested asset is copied into isolated temporary public directory, removed after render; repository directories are not exposed. Validation is a local CLI guard, not a hostile multi-tenant sandbox. Output path remains existing CLI string contract.

`renderOptions: {crf:0..51 integer, muted:boolean, audioBitrate:'64k'|'96k'|'128k'|'160k'|'192k'|'256k'|'320k', volume:0..2}` defaults 21,false,128k,1. Existing primary audio reencoded AAC (not stream-copied); no external audio sources. H264 yuv420p; concurrency1, PNG, disableSharedMemoryCapture true, disallowParallelEncoding true remain enforced. Width/height even <=7680; fps1..120; frames1..216000. Existing headlineDuration may exceed short composition as before.

## Verification

`pnpm run typecheck && pnpm test` (46 passing tests including legacy14; old >3 strike rejection deliberately replaced with >100 rejection). Animation tests exercise actual transpiled source, including80ms smooth edges, short words, and lower-third entrance. `node test/smoke.mjs`: ffmpeg-generated two-second240x426/30fps color footage + existing local Poppins font; raster/text overlay, caption keyword/strike, lower-third, endcard, luma. No source audio added. Full decode + exact60-frame assertion + rendered pixel checks for lower-third glyphs, cut white peak, pre/post recovery and endcard background. Files under `test/artifacts/graphics-smoke/`: job.json, prepared.mp4, mark.png, graphics.mp4, lower-third.png, luma.png, endcard.png, verification.json. Optional `SMOKE_FONT=/absolute/font.ttf` override. All-frame strip QA on real prepared podcast footage remains parent's delivery gate; tiny generated smoke is not a substitute. Supporting-video layout and audio passthrough controls validated by schema/typecheck but not exercised by this silent primary-only smoke.
