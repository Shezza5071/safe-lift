// Safe Lift pitch as .pptx with the motion video embedded. Mirrors the Slides deck.
const pptxgen = require("pptxgenjs");
const fs = require("fs");

const VIDEO = "/home/claude/safe_lift_motion.mp4";
const POSTER = "/tmp/claude-0/-home-claude/b5cafed6-aec3-5027-92ac-37f5ad91f7df/scratchpad/deckmedia/poster.png";
const OUT = process.argv[2] || "safe_lift_pitch.pptx";

const BG = "0C1422", CARD = "152033", INK = "EEF2F7", MUTED = "A6B2C3";
const TEAL = "40C4D6", AMBER = "F6AD34", RED = "EB484D", GREEN = "34C778";
const LIGHT = "F3F5F8", LCARD = "FBFCFD", LBORDER = "D9DFE7", DTEAL = "0B6E7C", LBODY = "33404F", LMUTED = "4A5568";
const F = "Arial";
const px = (v) => v / 144;           // deck canvas 1920 px = 13.333 in
const pt = (v) => v / 2;             // 72 px on the canvas = 36 pt

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.title = "Safe Lift pitch";
pres.subject = "Hack for Humanity Adelaide 2026";
pres.theme = { headFontFace: F, bodyFontFace: F };

function frame(name, bg, eyebrowColor, titleColor) {
  pres.defineSlideMaster({
    title: name,
    background: { color: bg },
    objects: [
      { placeholder: { options: { name: "eyebrow", type: "body", x: px(128), y: px(110), w: px(1664), h: px(40), fontFace: F, fontSize: pt(24), bold: true, color: eyebrowColor, charSpacing: 2, margin: 0 }, text: "" } },
      { placeholder: { options: { name: "title", type: "title", x: px(128), y: px(160), w: px(1664), h: px(110), fontFace: F, fontSize: pt(72), bold: true, color: titleColor, margin: 0, valign: "top", align: "left" }, text: "" } },
    ],
  });
}
frame("DARK", BG, TEAL, INK);
frame("LIGHT", LIGHT, DTEAL, BG);
frame("ACCENT", TEAL, BG, BG);
pres.defineSlideMaster({ title: "DARK_BLANK", background: { color: BG }, objects: [] });

const T = (s, text, o) => s.addText(text, { isTextBox: true, fontFace: F, margin: 0, valign: "top", ...o });
function footer(s, text, color) {
  T(s, text, { x: px(128), y: px(1000), w: px(1664), h: px(36), fontSize: pt(24), color });
}
function card(s, x, y, w, h, fill, line) {
  s.addShape(pres.ShapeType.roundRect, { x: px(x), y: px(y), w: px(w), h: px(h), rectRadius: px(24),
    fill: { color: fill }, line: line ? { color: line, width: 0.75 } : { type: "none" } });
}
function head(s, eyebrow, title) {
  s.addText(eyebrow.toUpperCase(), { placeholder: "eyebrow" });
  s.addText(title, { placeholder: "title" });
}

// 1 cover
pres.addSection({ title: "The hook" });
let s = pres.addSlide({ masterName: "DARK_BLANK", sectionTitle: "The hook" });
T(s, "HACK FOR HUMANITY ADELAIDE 2026", { x: px(128), y: px(200), w: px(960), h: px(40), fontSize: pt(24), bold: true, color: TEAL, charSpacing: 2 });
T(s, "Safe Lift", { x: px(128), y: px(260), w: px(960), h: px(190), fontSize: pt(160), bold: true, color: INK });
T(s, "Plan first. Then lift.", { x: px(128), y: px(470), w: px(960), h: px(70), fontSize: pt(44), bold: true, color: TEAL });
T(s, "A Gemma-coached manual handling trainer for aged care workers.", { x: px(128), y: px(560), w: px(900), h: px(100), fontSize: pt(32), color: MUTED });
card(s, 1152, 250, 640, 480, CARD);
T(s, "17,358", { x: px(1208), y: px(300), w: px(540), h: px(140), fontSize: pt(120), bold: true, color: INK });
T(s, "South Australians live in residential aged care.", { x: px(1208), y: px(460), w: px(540), h: px(100), fontSize: pt(32), bold: true, color: INK });
T(s, "Every transfer they need is a manual handling task for a care worker.", { x: px(1208), y: px(580), w: px(540), h: px(100), fontSize: pt(28), color: MUTED });
footer(s, "[Team names]  ·  github.com/Shezza5071/safe-lift  ·  Based on: AIHW GEN Aged Care Data 2024-25 (CC BY 4.0), via H4H", MUTED);
s.addNotes("0:00 to 0:20. Hook. \"17,358 South Australians live in residential aged care. Every time one of them moves from bed to chair, a care worker is doing a manual handling task, and body stressing is nearly half of all serious injury claims in that workforce. We built Safe Lift so the plan gets followed before anyone lifts.\" Then: \"Here's Safe Lift in about a minute.\" Next slide.");

// 2 video
pres.addSection({ title: "Show it" });
s = pres.addSlide({ masterName: "DARK_BLANK", sectionTitle: "Show it" });
T(s, "Safe Lift in 68 seconds", { x: px(128), y: px(96), w: px(1664), h: px(60), fontSize: pt(44), bold: true, color: INK });
const poster = "data:image/png;base64," + fs.readFileSync(POSTER).toString("base64");
s.addMedia({ type: "video", path: VIDEO, x: px(320), y: px(200), w: px(1280), h: px(720), cover: poster, objectName: "Safe Lift motion graphic" });
s.addNotes("0:20 to 1:30. Click the video to play (no sound: talk over it or let it run). Cues: the numbers (first 20 s); training alone isn't the control (~0:25); MediaPipe is the eyes, Gemma the coach, Snowflake the memory (~0:30); the gate blocks the lift until the plan is met (~0:40); red only after two seconds, then Gemma asks why (~0:50). When it ends: \"Now let's do it live.\"");

// 3 demo
s = pres.addSlide({ masterName: "DARK", sectionTitle: "Show it" });
head(s, "Live demo", "One transfer, four moments");
const beats = [
  ["1", AMBER, "Gemma reads the plan", "Photo of a synthetic plan becomes rules: hoist, 2 staff, no manual lift."],
  ["2", RED, "The gate blocks", "“Plan says 2 staff, 1 seen.” The function call shows on screen. A second trainee walks in: unlocked."],
  ["3", TEAL, "A bad lift goes red", "Red only after 2 seconds held. Gemma looks at the skeleton and asks a specific question."],
  ["4", GREEN, "Debrief and dashboard", "A cited debrief in the trainee’s language, then the trainer’s view in Snowflake."],
];
beats.forEach(([n, col, h, b], i) => {
  const x = 128 + i * 424;
  card(s, x, 340, 392, 560, CARD);
  s.addShape(pres.ShapeType.ellipse, { x: px(x + 40), y: px(380), w: px(72), h: px(72), fill: { color: col }, line: { type: "none" } });
  T(s, n, { x: px(x + 40), y: px(380), w: px(72), h: px(72), fontSize: pt(36), bold: true, color: BG, align: "center", valign: "middle" });
  T(s, h, { x: px(x + 40), y: px(480), w: px(312), h: px(100), fontSize: pt(32), bold: true, color: INK });
  T(s, b, { x: px(x + 40), y: px(600), w: px(312), h: px(260), fontSize: pt(26), color: MUTED });
});
footer(s, "If the camera fails: play the recorded backup run and keep narrating.", MUTED);
s.addNotes("1:30 to 3:00 (90 s). Leave this slide up while you switch to the laptop. (1) ~15 s: plan photo, Gemma's rules JSON. (2) ~25 s: one trainee in frame, BLOCKED with the block_task call visible; second trainee joins, READY. (3) ~30 s: stoop lift, amber then red after 2 s, beep; Gemma's question; tap the answer (keys 1 to 4). (4) ~20 s: debrief in Nepali or Vietnamese citing the Model Code; flip to the dashboard: ML risk badge, model comparison, SA context tile (17,358). Fallback: the recorded run, same narration.");

// 4 under the hood
pres.addSection({ title: "How it works and how well" });
s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "How it works and how well" });
head(s, "Under the hood", "The camera measures. Gemma reasons. Snowflake learns.");
const cols = [
  ["Gemma 4: five jobs", ["Reads the plan photo into rules", "Runs the setup gate with function calls", "Asks why after a red alarm", "Writes a cited debrief in the trainee’s language", "Second-rates every lift to clean ML labels"]],
  ["Snowflake: the memory", ["Readings stream in every 2 seconds", "Cortex Search over official guidance", "ML classifier learns what trainers call unsafe", "Trainer dashboard, plus live research evidence from the Marketplace", "H4H open data for SA context"]],
];
cols.forEach(([h, items], i) => {
  const x = 128 + i * 856;
  card(s, x, 400, 808, 520, LCARD, LBORDER);
  T(s, h, { x: px(x + 48), y: px(440), w: px(712), h: px(50), fontSize: pt(32), bold: true, color: BG });
  T(s, items.map((t, k) => ({ text: t, options: { bullet: { type: "number" }, breakLine: k < items.length - 1 } })),
    { x: px(x + 48), y: px(510), w: px(712), h: px(390), fontSize: pt(28), color: LBODY, paraSpaceAfter: 8 });
});
footer(s, "MediaPipe pose runs on the laptop. Only angles and skeleton drawings leave it, never video.", LMUTED);
s.addNotes("3:00 to 3:40. \"The camera only measures angles. Every decision is Gemma's: it reads the plan, runs the gate with function calls, asks why, and writes the debrief grounded in the Model Code through Cortex Search. Snowflake is the memory: readings stream in, a classifier learns what our trainers label unsafe, and Gemma acts as a second rater so we drop labels where human and Gemma disagree before training.\"");

// 5 results
s = pres.addSlide({ masterName: "DARK", sectionTitle: "How it works and how well" });
head(s, "Does it work?", "Tested, with the limits stated");
const stats = [
  ["0 / 33", GREEN, "alarm errors on a labelled test set", "Synthetic staged lifts. Precision 1.00, recall 0.83: the 2 misses are a body hidden from the camera."],
  ["74%", AMBER, "accuracy when Gemma cleans the labels", "23 held-out readings: Snowflake ML v2 74%, Gemma alone 64%, ML v1 52%, REBA rule 43%."],
  ["Closed", TEAL, "the setup gate fails safe", "Any error, timeout or empty reply keeps the lift blocked."],
];
stats.forEach(([big, col, h, b], i) => {
  const x = 128 + i * 565;
  card(s, x, 340, 533, 580, CARD);
  T(s, big, { x: px(x + 48), y: px(390), w: px(437), h: px(120), fontSize: pt(96), bold: true, color: col });
  T(s, h, { x: px(x + 48), y: px(530), w: px(437), h: px(100), fontSize: pt(32), bold: true, color: INK });
  T(s, b, { x: px(x + 48), y: px(660), w: px(437), h: px(220), fontSize: pt(26), color: MUTED });
});
footer(s, "Staged lifts, small labelled sets, one 2D camera (about 5 to 10° error): evidence the pipeline works, not proof it prevents injury.", MUTED);
s.addNotes("3:40 to 4:15. \"We tested it honestly. On a labelled set of 33 staged sessions the alarm made no errors; it missed the two where a second worker blocked the camera, which is a real limit. Then the Gemma and Snowflake result: on 23 held-out readings, the REBA rule alone matched our trainers 43% of the time, Gemma alone 64%, our first Snowflake model 52%. When Gemma rated every lift as a second rater and we dropped the labels where it and the human disagreed, the retrained Snowflake model reached 74%. Small numbers, but that is Gemma teaching Snowflake. And the gate fails closed: if anything goes wrong, nobody lifts.\" Don't claim injury prevention.");

// 6 responsible
s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "How it works and how well" });
head(s, "Built for a training room", "Coaching, not surveillance");
[["Skeleton only", "No video is saved. Gemma sees a stick figure, never a person."],
 ["Consent first", "Training-room mode by default. Synthetic plans, consenting adults, no residents."],
 ["Fix the task", "Patterns by task and plan, never worker rankings or discipline."]].forEach(([h, b], i) => {
  const x = 128 + i * 565;
  card(s, x, 400, 533, 440, LCARD, LBORDER);
  T(s, h, { x: px(x + 48), y: px(450), w: px(437), h: px(60), fontSize: pt(36), bold: true, color: BG });
  T(s, b, { x: px(x + 48), y: px(540), w: px(437), h: px(260), fontSize: pt(28), color: LMUTED });
});
footer(s, "Real care settings would need recorded consent: the Surveillance Devices Act 2016 (SA) covers observing, not just recording.", LMUTED);
s.addNotes("4:15 to 4:35. \"A camera in a care setting raises real questions, so we designed for the training room. Nothing is recorded, Gemma only ever sees a skeleton, and the data points at tasks and plans that need fixing, never at individual workers. Taking it into a real facility would need recorded consent; South Australia's Surveillance Devices Act covers observing a private activity, not just recording it.\"");

// 7 next
pres.addSection({ title: "Next and close" });
s = pres.addSlide({ masterName: "ACCENT", sectionTitle: "Next and close" });
head(s, "What’s next", "From the hackathon to a pilot");
[["Pilot with SA educators", "Real trainer labels across many workers, then retrain the model."],
 ["Score the whole transfer", "A validated 16-item observation checklist (DINO), pre-filled by Gemma, confirmed by the trainer."],
 ["Keep data at home", "Gemma inside the provider’s Snowflake, or on the device, so care plans never leave."]].forEach(([h, b], i) => {
  const x = 128 + i * 565;
  card(s, x, 400, 533, 500, BG);
  T(s, h, { x: px(x + 48), y: px(450), w: px(437), h: px(110), fontSize: pt(36), bold: true, color: INK });
  T(s, b, { x: px(x + 48), y: px(590), w: px(437), h: px(280), fontSize: pt(28), color: MUTED });
});
s.addNotes("4:35 to 4:50. \"Next, we'd pilot with South Australian aged care educators to get real labels. We'd score the whole transfer, not just the back angle, using a validated observation checklist where Gemma pre-fills and the trainer confirms. And we'd run Gemma inside the provider's own Snowflake account or on the device, so care plans never leave the building.\"");

// 8 close
s = pres.addSlide({ masterName: "DARK_BLANK", sectionTitle: "Next and close" });
T(s, "Safe Lift", { x: px(128), y: px(260), w: px(1664), h: px(190), fontSize: pt(160), bold: true, color: INK, align: "center" });
T(s, "Plan first. Then lift.", { x: px(128), y: px(470), w: px(1664), h: px(100), fontSize: pt(72), bold: true, color: TEAL, align: "center" });
T(s, "MediaPipe  ·  Gemma 4  ·  Snowflake  ·  open source, MIT\ngithub.com/Shezza5071/safe-lift", { x: px(128), y: px(620), w: px(1664), h: px(110), fontSize: pt(32), color: MUTED, align: "center" });
T(s, "Training aid only, not a safety device or medical advice. Always follow the resident’s plan and your employer’s procedures.", { x: px(128), y: px(1000), w: px(1664), h: px(36), fontSize: pt(24), color: MUTED, align: "center" });
s.addNotes("4:50 to 5:00. \"Safe Lift: plan first, then lift. It's open source, so any trainer can run it. Thank you.\" Stop. Take questions with the sources slide ready.");

// 9 sources
s = pres.addSlide({ masterName: "LIGHT", sectionTitle: "Next and close" });
head(s, "For questions", "Sources and credits");
const src = [
  "17,358 in SA residential aged care at 30 June 2025: based on AIHW, GEN Aged Care Data, People using aged care by region 2024-25, CC BY 4.0 (H4H set A2, summarised to SA totals)",
  "47.6% body stressing: Safe Work Australia, WHS profile: nursing, care and support workforce (May 2025; average since 2012-13)",
  "21% of SA body-stressing claims from health care and social assistance: SafeWork SA, 21 October 2024",
  "Model comparison: Safe Lift MODEL_COMPARE, 23 held-out staged readings, 30 October 2026",
  "Training alone: Cochrane review CD005958.pub3. Hierarchy of controls: Model Code of Practice: Hazardous manual tasks",
  "Alarm bands: REBA, Hignett and McAtamney (2000), Applied Ergonomics 31(2):201-205",
  "Observation checklist: DINO, Johnsson et al. (2004), Applied Ergonomics 35(6):591-601",
  "Gemma 4 (Gemma terms) · MediaPipe (Apache 2.0) · Snowflake · Safe Lift code MIT. Test data in the repo is synthetic.",
];
T(s, src.map((t, k) => ({ text: t, options: { bullet: true, breakLine: k < src.length - 1 } })),
  { x: px(128), y: px(330), w: px(1664), h: px(680), fontSize: pt(24), color: LBODY, paraSpaceAfter: 6 });
s.addNotes("Backup slide for Q&A. Don't present it in the 5 minutes.");

pres.writeFile({ fileName: OUT }).then((f) => console.log("wrote", f));
