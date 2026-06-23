# Voice Pack — POV / tense / register / rhythm

> Says *how to write*. (What was *decided* lives in `input/series/style-sheet.md`.)
> Frequency tics and the banned-phrase/metaphor list live in the sibling
> `ai-tics-detection.md` (Tier A, design §8a).

## Genre contract (load-bearing)

This is a cozy mystery. The voice must make the reader want to stay in the world. Death is present but the puzzle — the social pleasure of working it out — is the frame. Warmth is not decoration; it is the engine. Nothing below overrides that contract.

## POV & tense

Third person limited, past tense, anchored to the protagonist.

## Voice blend

**70% Clive James (travel-writer mode) / 30% Peter Temple.** James supplies warmth, observational wit, and sentence architecture. Temple supplies economy, Australian register, and the tighter cadence that takes over under pressure. Temple's darkness and menace are absent entirely — only his diction and economy come in.

## Observer stance

The protagonist moves through her world the way a travel writer moves through a foreign country: noticing what locals stopped seeing, finding the particular detail that stands for the general condition. Curiosity, not detachment. The reader feels invited into the observation, not excluded from it. Warmth is generated here — when the narrator finds something remarkable in an ordinary thing, the reader shares the discovery.

## Sentence construction

Default register is James: compound sentences that build, with subordinate clauses that earn their length. The surprise is in the arrival — the sentence sets up a direction and lands somewhere slightly unexpected.

Temple enters as **punctuation**: a short declarative after a longer construction, not the other way around. One blunt sentence can end a paragraph. Never three short sentences in a row unless tension is rising.

Rule of thumb: if a paragraph has four sentences of roughly equal length, at least one is wrong. (Rhythm variety is enforced statistically by `voice_drift.py`.)

## Detail philosophy

Specific over general, always. Earn generalisations through a particular — not "the town was run-down" but the specific detail that carries run-down as a conclusion the reader draws themselves.

Simile and metaphor must illuminate, not decorate. If the comparison doesn't change how the reader sees the thing, cut it.

Never abstract emotion. The protagonist doesn't feel warmth; she notices the thing that causes it.

## Australian register

The prose sounds Australian without announcing it. Idiom at the word and phrase level — vernacular ease, local colour. The protagonist thinks in Australian; she does not translate for an overseas reader. Place names, flora, fauna, and social customs are named without apology or footnote. This is Temple's primary contribution to the base register.

## Register under pressure

As the novel moves toward its climax, Temple takes over progressively — not switched, gradual:

- **Rising tension:** subordinate clauses reduce, sentences shorten, narration becomes less ruminative
- **Peak tension:** sentences stop building. Things happen and the prose reports them. No wit until the pressure drops
- **Climax:** a revelation, not a confrontation — the tightening is cognitive and emotional urgency, not menace

The cozy contract holds through the climax: even at maximum Temple, the register stays on the right side of dark. After the revelation, the voice returns toward James.

## What not to do

- **No BBC dryness** — James's wit is warm; it does not perform cleverness at the reader's expense
- **No American crime cadence** — hard-boiled is a different genre
- **No over-explanation** — never explain what the detail already shows
- **No stated sentiment** — earned through observation, not announced
- **No noir menace** — Temple's darkness stays out entirely
- **No gush** — warmth ≠ effusiveness
