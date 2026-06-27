# Book 01 Suspect-Arc Restructure (Cal False Lead) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-time Book 01's suspect resolutions into a three-stage collapse-and-converge (dead-end Saffron+Beryl → Cal emerges → Cal clears = Mary converges) by editing the outline and the whodunit ledger, then re-minting the mystery lock.

**Architecture:** This is a **content/data change, not engine code.** Two artifacts change — `input/book-01/outline.md` (drafting source of truth) and `series/whodunit/book-01.yaml` (the fairplay-gated ledger) — then the out-of-band mystery lock is re-validated. No `scripts/` change; the full pytest suite must stay green as a regression guard.

**Tech Stack:** Markdown outline, PyYAML ledger, `scripts/fairplay_check.py` + `scripts/preflight.py lock-mystery` (deterministic gates), grep audits.

## Global Constraints

- **Verification is deterministic gates, not new unit tests** (project precedent for content changes): `fairplay_check.py` clean, `preflight lock-mystery 01` re-mints, targeted grep audits, and `python3 -m pytest` stays green.
- **Do not touch finalized work:** chapters 1–2 are finalized; all edits are ch 10+. Do not edit `output/book-01/`.
- **Unchanged invariants (copy verbatim into the ledger):** `total_chapters: 29`, `reveal_chapter: 25`, `culprit: mary-burrell`, `culprit_first_appearance_chapter: 2`, `victim: neil-hartigan`. The investigative *click* (Maggie identifies Mary) stays ch 20; the formal confession/`reveal_chapter` stays 25.
- **Mary keeps her auditable gap:** her `alibi_grid` entry must remain `holds: false` (fairplay blocks if every culprit alibi holds).
- **Every `alibi_grid` suspect must resolve** to `series/continuity/characters/<id>.md`. Confirmed present: `mary-burrell`, `saffron`, `beryl-foss`, `faye`, `vincent-calloway`, `cobber`, `cal-burrell`, `neil-hartigan`.
- **Mary stays passive** (never points at Cal); **Cal is cleared on proof** (Cobber's car = Mary's; Cal's gap independently accounted), never on Maggie's feeling.
- **Lock is out-of-band:** never add a "locked/validated" field to the ledger; re-validation = delete the lock file, then run `lock-mystery`.
- Run all commands from repo root (`/Users/beeko/myTools/penny`); `pytest.ini` sets `pythonpath=.`.

---

### Task 1: Ledger restructure (`series/whodunit/book-01.yaml`)

Re-time the red herrings and alibi grid for the new arc and add Cal as a formal red herring + cleared suspect. Fairplay must stay clean. **Do not re-lock in this task** (re-lock is Task 5, after the outline is consistent).

**Files:**
- Modify: `series/whodunit/book-01.yaml` (the `clue_schedule`, `red_herrings`, `alibi_grid` blocks, lines 14–29)
- Verify with: `scripts/fairplay_check.py`

**Interfaces:**
- Consumes: nothing.
- Produces: a ledger whose `alibi_grid` includes `cal-burrell` (chapter 20, `holds: true`) and `beryl-foss` (chapter 17), and `red_herrings` includes `rh-cal`. Later tasks/the outline reference these chapter numbers (Beryl clears 17, Cal clears 20).

- [ ] **Step 1: Capture the clean fairplay baseline**

Run:
```bash
python3 scripts/fairplay_check.py series/whodunit/book-01.yaml --out /tmp/fp-before
grep -c '^BLOCKING:' /tmp/fp-before/fairplay.md || true
```
Expected: `0` (no blocking lines today).

- [ ] **Step 2: Edit the `clue_schedule` block**

In `series/whodunit/book-01.yaml`, change the `clue-erasure` line so its true payoff (Mary) is ch 20 — at ch 19 it only misleads toward Cal. Replace:
```yaml
  - { id: clue-erasure, plant_chapter: 7, pays_off_chapter: 19, necessary: true }
```
with:
```yaml
  - { id: clue-erasure, plant_chapter: 7, pays_off_chapter: 20, necessary: true }
```
Leave the other three `clue_schedule` lines unchanged.

- [ ] **Step 3: Add `rh-cal` to `red_herrings`**

Append one line to the `red_herrings` block (keep the existing three lines as-is):
```yaml
  - { id: rh-cal, plant_chapter: 11, misleads_toward: "cal-burrell", must_not_cheat: true }
```
(Cal's misleading material — precision habit readable as his, plus the workshop motive — is planted by ch 11.)

- [ ] **Step 4: Re-time Beryl and add Cal in `alibi_grid`**

Replace the existing `beryl-foss` alibi line:
```yaml
  - { suspect: beryl-foss, chapter: 14, alibi: "running CWA community event in front of fifty witnesses", holds: true }
```
with (clearing now lands at the dead-end, ch 17, via the private medical reason the outline actually uses):
```yaml
  - { suspect: beryl-foss, chapter: 17, alibi: "changed clothes the murder night after a frightening private medical appointment, not from guilt; resolves at the dead-end alongside Saffron", holds: true }
```
Then add a `cal-burrell` line immediately after the `vincent-calloway` line:
```yaml
  - { suspect: cal-burrell, chapter: 20, alibi: "the blue-green car in the timeline gap is Mary's, not his; his own movements that evening are independently accounted", holds: true }
```
Leave `mary-burrell` (`holds: false`), `saffron` (chapter 17), `faye`, `vincent-calloway`, and `cobber` unchanged.

- [ ] **Step 5: Verify fairplay stays clean and the YAML parses**

Run:
```bash
python3 scripts/fairplay_check.py series/whodunit/book-01.yaml --out /tmp/fp-after
grep -c '^BLOCKING:' /tmp/fp-after/fairplay.md || true
python3 -c "import yaml; d=yaml.safe_load(open('series/whodunit/book-01.yaml')); print(sorted(a['suspect'] for a in d['alibi_grid'])); print([r['id'] for r in d['red_herrings']])"
```
Expected: blocking count `0`; the suspect list includes `cal-burrell` and `beryl-foss`; the red-herring ids include `rh-cal`.

- [ ] **Step 6: Commit**

```bash
git add series/whodunit/book-01.yaml
git commit -m "plan(book-01): ledger — Cal red herring + Beryl/Saffron dead-end re-timing"
```

---

### Task 2: Outline Act IIa — the dead-end setup (ch 10, 16, 17)

Hold Beryl live past ch 10 and resolve her *and* Saffron together at ch 17, producing the two-possibles dead-end. Edit only the named chapter sections of `input/book-01/outline.md`.

**Files:**
- Modify: `input/book-01/outline.md` (the `## Chapter 10`, `## Chapter 16`, `## Chapter 17` sections)

**Interfaces:**
- Consumes: the ledger chapter numbers from Task 1 (Beryl clears 17).
- Produces: an outline where, by end of ch 17, both Saffron and Beryl are cleared and Maggie is at a true wall (consumed by Task 3's ch 18).

- [ ] **Step 1: Ch 10 — withhold Beryl's innocent explanation**

In `## Chapter 10 — Beryl's Changed Clothes`, **keep** the cruel blurt, the room freezing, and Pruitt's warning, but **remove the on-page reveal of the innocent cause**. Specifically:
- In the Chapter Summary, delete the sentence that explains the cause — currently: *"The truth is private and devastating rather than criminal: Beryl changed after a frightening medical appointment and did not want the town's pity."* Replace with a line that keeps the cause unknown and Beryl live, e.g.: *"Beryl will not say why she changed — only that it is private — and the refusal, layered over her public argument with Neil, leaves her a suspect Maggie cannot dismiss even as the town turns on Maggie's cruelty."*
- In **Track Movement → M**, change *"Beryl is not cleared by proof, but Maggie loses trust…"* style note to make explicit Beryl stays a **live suspect**: e.g. *"Beryl's motive (the public health humiliation) and her unexplained clothes-change keep her live; Maggie's method is discredited, but Beryl is not cleared — her innocent reason is withheld until ch 17."*
- Leave the Hook (Pruitt: "bring me facts—not a performance") unchanged.

- [ ] **Step 2: Ch 16 — two parallel live cases**

In `## Chapter 16 — The Case Against Saffron`, widen the chapter so Maggie is running **two** live suspects, not one:
- In the Chapter Summary, after the Saffron case is described, add that Beryl remains unresolved and pressing: e.g. *"And Beryl still has not said what the changed clothes were about — Maggie is now holding two open suspects at once, Saffron's convenient guilt and Beryl's unexplained night, and cannot close either."*
- In **Track Movement → M**, note both cases are live going into the dead-end: e.g. *"Builds the Saffron case while keeping Beryl unresolved — two parallel possibles entering ch 17."*
- Keep the Cal-emotional-bias material (Cal warning Maggie she "sounds like Mary") intact.

- [ ] **Step 3: Ch 17 — the double dead-end**

In `## Chapter 17 — The Wrong Woman`, make **both** suspects collapse near-together so the chapter ends on a true wall:
- Keep Saffron's public collapse (the debt-recovery alibi).
- Add Beryl's resolution here: the withheld cause from ch 10 finally surfaces innocently — e.g. *"In the same stretch, Beryl's secret comes out the only way it could: she changed that night after a frightening private medical appointment, not from guilt. The two best answers fail within a day of each other."*
- Rewrite the **Hook** so it names the wall rather than only the glaze breakthrough. Keep the repaired-glaze beat (it feeds the business arc) but end on the dead-end, e.g.: *"Two suspects gone in a day; the case has no one left in it — and Maggie, hollowed out, has only the wheel to go back to."*
- In **Track Movement → M**, change *"Act II low point; false solution collapses"* to *"Act II low point: the two live possibles (Saffron, Beryl) both collapse — a true dead-end with no suspect left."*

- [ ] **Step 4: Audit the Act IIa edits**

Run:
```bash
# Beryl's innocent cause must no longer sit in ch 10; it now lands in ch 17.
awk '/^## Chapter 10 /{f=1} /^## Chapter 11 /{f=0} f' input/book-01/outline.md | grep -i "frightening" && echo "FAIL: cause still in ch10" || echo "ok: ch10 withholds cause"
awk '/^## Chapter 17 /{f=1} /^## Chapter 18 /{f=0} f' input/book-01/outline.md | grep -iq "medical appointment\|frightening" && echo "ok: cause resolves in ch17" || echo "FAIL: cause missing from ch17"
awk '/^## Chapter 16 /{f=1} /^## Chapter 17 /{f=0} f' input/book-01/outline.md | grep -iq "two" && echo "ok: ch16 two possibles" || echo "check ch16 wording"
```
Expected: `ok: ch10 withholds cause`, `ok: cause resolves in ch17`, `ok: ch16 two possibles`.

- [ ] **Step 5: Commit**

```bash
git add input/book-01/outline.md
git commit -m "plan(book-01): outline IIa — hold Beryl live, double dead-end at ch17"
```

---

### Task 3: Outline Act IIb — Cal emerges, then clears = Mary converges (ch 18, 19, 20)

Turn the existing brief Cal-suspicion into a full stage, and split the ch-19 click so Cal is the suspect at 19 and the Cal→Mary resolution lands at 20.

**Files:**
- Modify: `input/book-01/outline.md` (the `## Chapter 18`, `## Chapter 19`, `## Chapter 20` sections)

**Interfaces:**
- Consumes: the dead-end from Task 2 (ch 17).
- Produces: ch 19 ends with Cal as the suspect; ch 20 clears Cal on proof and lands Mary as the investigative click. Consumed by Task 4 (ch 24 references the suspicion).

- [ ] **Step 1: Ch 18 — the Ordeal surfaces the precision *pattern***

In `## Chapter 18 — The Only Quiet`, keep the gift-turns-disciplined Ordeal, but make the surfaced question point at *a precise person*, setting the Cal trap. In the Chapter Summary, where the clay "hands her not an answer but a question," change the question from "whose habit reset the room" to the precision pattern that will read as Cal: e.g. *"someone with exact, trained habits reset that room — the kind of precision she has only ever seen in one person."* In **Track Movement → M**, update to: *"Recombines the staged-scene details into a precise-habits question that points, next chapter, at the most organised person Maggie knows."* Keep the Hook ("bring Pruitt a habit, not a hunch").

- [ ] **Step 2: Ch 19 — Cal emerges and stays (no Mary yet)**

Rewrite `## Chapter 19 — The Cup Returns Home` so the precision pattern + Cal's workshop motive converge on **Cal**, and the chapter ends there — **move the watch-Mary-reset-the-room beat out** (it goes to ch 20):
- Chapter Summary: Maggie's disciplined gift (from ch 18) matches the staged-scene precision to Cal's known habits; his motive (Neil planting doubt about the workshop sale, threatening Cal's future) fits. She is sick with it. Crucially she applies the discipline she failed with Beryl and Saffron: she does **not** accuse, does not go to Pruitt with a hunch — she resolves to get proof. Optionally, Pruitt independently raises Cal here on the same physical evidence (or keep that for ch 23 — keep one instance, do not duplicate).
- Retitle if helpful (the cup-return motif now belongs to ch 20). A fitting new title: `## Chapter 19 — The Most Organised Man She Knows`.
- **Hook:** end on the dread + the discipline, e.g. *"The habits are Cal's. She will not do to him what she did to Beryl — she will find the proof it wasn't him."*
- **Track Movement → M:** *"The precision clue converges on Cal (motive: the workshop; habits: his). No Mary yet. Maggie chooses proof over accusation."* **→ R:** the romance stakes spike (she is investigating the man she loves).

- [ ] **Step 3: Ch 20 — Cal clears = Mary converges**

Edit `## Chapter 20 — The Evening Accounted For` so the two proofs land together and the Cal→Mary resolution (the watch-Mary-reset beat + upbringing pivot) happens **here**:
- Keep the reconstructed-evening timeline placing Beryl, Faye, Calloway and the gap.
- Keep Cobber placing the blue-green car in the gap as **Mary's, not Cal's**, and add that **Cal's own movements in the gap are independently accounted** (so he clears on proof, not feeling).
- Bring in the watch-Mary-reset-a-room beat (moved from ch 19): Maggie sees Mary restore a room by muscle memory — the exact precision that read as Cal's — and the upbringing pivot ("Mary raised him; she made him who he is") reveals the habit was **Mary's**, taught to Cal.
- **Hook** stays Mary's tea invitation.
- **Track Movement → M:** *"Cal clears on proof (car = Mary's; his gap accounted); the precision habit's true origin is Mary, who raised him. Investigative click lands on Mary — confession still ch 25."* **→ R:** the relief of clearing Cal reframes Maggie's feelings (as in the current outline).

- [ ] **Step 4: Audit the Act IIb edits**

Run:
```bash
awk '/^## Chapter 19 /{f=1} /^## Chapter 20 /{f=0} f' input/book-01/outline.md | grep -iq "cal" && echo "ok: ch19 centres Cal" || echo "FAIL: ch19 missing Cal"
awk '/^## Chapter 19 /{f=1} /^## Chapter 20 /{f=0} f' input/book-01/outline.md | grep -iq "mary" && echo "WARN: ch19 still names Mary (should defer to ch20)" || echo "ok: ch19 defers Mary"
awk '/^## Chapter 20 /{f=1} /^## Chapter 21 /{f=0} f' input/book-01/outline.md | grep -iq "raised him\|made him who he is" && echo "ok: ch20 upbringing pivot" || echo "FAIL: ch20 missing pivot"
awk '/^## Chapter 20 /{f=1} /^## Chapter 21 /{f=0} f' input/book-01/outline.md | grep -iq "not Cal's\|Mary's, not" && echo "ok: ch20 clears Cal on proof" || echo "check ch20 car proof wording"
```
Expected: `ok: ch19 centres Cal`, `ok: ch19 defers Mary` (the WARN line is acceptable only if Mary appears merely as background, not as the identified killer — reviewer confirms), `ok: ch20 upbringing pivot`, `ok: ch20 clears Cal on proof`.

- [ ] **Step 5: Commit**

```bash
git add input/book-01/outline.md
git commit -m "plan(book-01): outline IIb — Cal emerges (ch19), clears = Mary converges (ch20)"
```

---

### Task 4: Outline ch 24 admission + summary-section consistency

Add Maggie's admission to Cal that she suspected him, and update the outline's roll-up sections (Track Map, Drafting Checks) so they describe the new cadence rather than the old serial fade-out.

**Files:**
- Modify: `input/book-01/outline.md` (`## Chapter 24`, `# Track Map at a Glance` Mystery + Romance sub-sections, `# Drafting Checks by Act` Midpoint + End-of-Act-II)

**Interfaces:**
- Consumes: the ch 19–20 suspicion from Task 3.
- Produces: a self-consistent outline whose summaries match the body.

- [ ] **Step 1: Ch 24 — Maggie tells Cal she suspected him**

In `## Chapter 24 — The Worst Conversation`, add the admission as a beat in the Chapter Summary: e.g. *"Maggie tells him the hardest part: for a day she believed it might be him — she had the habit and the motive — and instead of going to Pruitt she went looking for proof he didn't do it, because she had already burned Beryl and Saffron and would not do that to him. The admission deepens the rupture and is the most honest thing she has said to him."* Add a matching line to **Track Movement → R** (e.g. *"Maggie's admission that she suspected him makes the rupture cut deeper and sets up an earned ch 28 repair."*). Keep the existing rupture beats and the invoice/professional-self-respect beat.

- [ ] **Step 2: Track Map — Mystery + Romance**

In `# Track Map at a Glance`:
- **Mystery Track**, rewrite the `Ch. 14–17` and `Ch. 19–23` lines to the new cadence, e.g.:
  `- **Ch. 14–17:** old death, post-mortem confirmation; Saffron AND Beryl run as parallel possibles and both collapse — the double dead-end.`
  `- **Ch. 18–20:** the disciplined gift surfaces a precise-habits question (18); it converges on Cal (19); Cal clears on proof while the habit's origin resolves to Mary, who raised him (20).`
  Keep the `Ch. 21–23` and `Ch. 24–27` lines (adjust only if they now contradict).
- **Romance Track**, update the `Ch. 19–25` line to name the Cal suspicion + admission: e.g. `- **Ch. 19–25:** Maggie suspects Cal and chooses proof over accusation (19–20); Mary's deception (21); Cal unknowingly hands her the evidence (22); rupture — she admits she suspected him (24); arrest (25).`

- [ ] **Step 3: Drafting Checks — Midpoint + End of Act II**

In `# Drafting Checks by Act`:
- **Midpoint Pressure — Chapters 14–17:** add that by ch 17 the reader should feel *both* Saffron and Beryl fail, leaving a true dead-end (not a single Saffron collapse).
- **End of Act II — Chapter 23:** keep the fair-play reconstruction requirement; add that the reader should understand Cal was a fair suspect cleared on proof, and that the precision habit pointed at him because Mary raised him.

- [ ] **Step 4: Audit + full coherence pass**

Run:
```bash
awk '/^## Chapter 24 /{f=1} /^## Chapter 25 /{f=0} f' input/book-01/outline.md | grep -iq "suspect" && echo "ok: ch24 admission" || echo "FAIL: ch24 admission missing"
grep -iq "double dead-end\|both collapse\|parallel possibles" input/book-01/outline.md && echo "ok: track map names dead-end" || echo "FAIL: track map not updated"
```
Expected: `ok: ch24 admission`, `ok: track map names dead-end`.

- [ ] **Step 5: Commit**

```bash
git add input/book-01/outline.md
git commit -m "plan(book-01): outline — ch24 suspicion admission + track-map/drafting-check consistency"
```

---

### Task 5: Re-validate the mystery lock + full regression

Delete the stale lock, re-mint it against the edited ledger, and confirm the deterministic suite is green.

**Files:**
- Modify: `.penny/locks/book-01.mystery.lock` (deleted then re-minted by `lock-mystery`)
- Verify with: `scripts/preflight.py`, `scripts/fairplay_check.py`, `pytest`

**Interfaces:**
- Consumes: the edited ledger (Task 1) and outline (Tasks 2–4).
- Produces: a freshly minted lock certifying the re-planned mystery.

- [ ] **Step 1: Delete the stale lock**

```bash
rm -f .penny/locks/book-01.mystery.lock
```

- [ ] **Step 2: Re-run the lock gate (validates fairplay + lexicon, re-mints)**

Run:
```bash
python3 scripts/preflight.py lock-mystery 01; echo "exit=$?"
ls -l .penny/locks/book-01.mystery.lock
```
Expected: `exit=0` and the lock file exists (re-minted). A non-zero exit prints `preflight: <predicate>` — if it reports a fairplay failure, the ledger edit in Task 1 regressed; fix and re-run. Do not hand-create the lock.

- [ ] **Step 3: Confirm fairplay is clean and pytest is green**

Run:
```bash
python3 scripts/fairplay_check.py series/whodunit/book-01.yaml --out /tmp/fp-final
grep -c '^BLOCKING:' /tmp/fp-final/fairplay.md || true
python3 -m pytest -q 2>&1 | tail -1
```
Expected: blocking count `0`; pytest `273 passed` (unchanged — no engine code touched).

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "plan(book-01): re-mint mystery lock for the Cal-false-lead restructure"
```

---

## Self-Review

**Spec coverage:**
- Decision 1 (evidence converges; discipline) → Task 3 Step 2 (ch 19). Decision 2 (Saffron+Beryl dead-end) → Task 2 (ch 16/17) + Task 1 (ledger). Decision 3 (Mary passive; Cal cleared on proof) → Task 3 Step 3 (ch 20, car=Mary's + Cal's gap accounted). Decision 4 (Cal learns, ch 24) → Task 4 Step 1.
- Three-stage spine → Tasks 2 (dead-end), 3 (emerge + converge). Chapter delta table → Tasks 2–4 cover every changed chapter (10,16,17,18,19,20,24) and the summary sections. Fairplay/ledger ripples → Task 1. Lock re-validation sequence → Task 5. Verification (deterministic gates) → every task's audit/gate steps.
- Unchanged invariants (total 29, reveal 25, culprit ch 2, Mary `holds:false`) → Global Constraints + Task 1 leaves them untouched.

**Placeholder scan:** no TBD/TODO; ledger edits give exact YAML; outline edits give concrete add/remove/replace text and new hook lines; every verification step is a runnable command with expected output.

**Type/identifier consistency:** ledger ids used consistently — `cal-burrell` (entity confirmed present), `beryl-foss`, `rh-cal`, `rh-beryl`; chapter numbers consistent across tasks (Beryl clears 17, Cal clears 20, click 20, reveal 25). The ch-19 retitle is optional and flagged as such.

**Note on outline greps:** the `awk`-by-chapter audits are coarse coherence checks, not proof of prose quality — the task reviewer reads the diff for narrative coherence and voice match against the surrounding outline.
