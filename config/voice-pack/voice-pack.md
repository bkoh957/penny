# Voice Pack — POV / tense / register / rhythm

> Says *how to write*. (What was *decided* lives in `input/series/style-sheet.md`.)
> Frequency tics and the banned-phrase/metaphor list live in the sibling
> `ai-tics-detection.md` (Tier A, design §8a).

## Genre contract (load-bearing)

This is a cozy mystery. The voice must make the reader want to stay in the world. Death is present but the puzzle — the social pleasure of working it out — is the frame. Warmth is not decoration; it is the engine. Nothing below overrides that contract.

## POV & tense

Third person limited, past tense, anchored to the protagonist.

## Voice blend

**60% Clive James (travel-writer mode) / 40% Liane Moriarty (cozy-social mode).** James supplies warmth, observational wit, sentence architecture, and the pleasure of noticing. Moriarty supplies social readability, domestic intimacy, emotional accessibility, and the comic precision of people revealing themselves while trying not to. The hybrid should feel intelligent, generous, sensuous, and commercially readable: elegant without becoming dry; warm without becoming sentimental; funny without sneering.

## Observer stance

The protagonist moves through her world the way a travel writer moves through a foreign country: noticing what locals stopped seeing, finding the particular detail that stands for the general condition. Curiosity, not detachment. The reader feels invited into the observation, not excluded from it. Warmth is generated here — when the narrator finds something remarkable in an ordinary thing, the reader shares the discovery.

## Sentence construction

Default register is James: compound sentences that build, with subordinate clauses that earn their length. The surprise is in the arrival — the sentence sets up a direction and lands somewhere slightly unexpected.

Moriarty enters through **social immediacy**: a clean, readable sentence that lets a gesture, domestic object, or tiny social lie land with comic-emotional force. One short sentence can end a paragraph, especially when it exposes a feeling the character would rather not name. Never three short sentences in a row unless tension is rising or the comedy needs a quick beat.

Rule of thumb: if a paragraph has four sentences of roughly equal length, at least one is wrong. (Rhythm variety is enforced statistically by `voice_drift.py`.)

## Detail philosophy

Specific over general, always. Earn generalisations through a particular — not "the town was run-down" but the specific detail that carries run-down as a conclusion the reader draws themselves.

Simile and metaphor must illuminate, not decorate. If the comparison doesn't change how the reader sees the thing, cut it.

Never abstract emotion. The protagonist doesn't feel warmth; she notices the thing that causes it.

## Cozy sensuality

In cozy mystery, concrete pleasure is not garnish — it is part of the genre engine. The reader should want to return to the town even while the puzzle darkens. Build warmth through embodied particulars: bread torn by hand, kettle steam, kiln heat, clay slip drying on wrists, lemon oil on fingers, rain on salt-hazed glass, wet wool in the bakery, a cat's weight on canvas, the hush after someone says the wrong thing.

Every chapter should offer the reader a few lived-in sensory rewards. Favour food, weather, craft, rooms, tools, animals, clothing, light, and small domestic rituals over abstract mood. Description should usually be attached to action: someone breaking bread, trimming a pot, folding a tea towel, wiping rain from a counter, lifting a cup by its chipped handle. Let texture carry character.

Sensual does not mean purple. Cozy warmth comes from precise, touchable details arranged with affection and wit. A paragraph may linger when the lingering gives the reader comfort, place, humour, or emotional access.

## Australian register

The prose sounds Australian without announcing it. Idiom at the word and phrase level — vernacular ease, local colour. The protagonist thinks in Australian; she does not translate for an overseas reader. Place names, flora, fauna, and social customs are named without apology or footnote. The register is contemporary, coastal, socially observant, and lightly comic.

## Register under pressure

As the novel moves toward its climax, the prose tightens progressively — not switched, gradual:

- **Rising tension:** subordinate clauses reduce, sentences shorten, narration becomes less ruminative
- **Peak tension:** sentences stop building. Things happen and the prose reports them. No wit until the pressure drops
- **Climax:** a revelation, not a confrontation — the tightening is cognitive and emotional urgency, not menace

The cozy contract holds through the climax: even at maximum pressure, the register stays on the right side of dark. After the revelation, the voice returns toward warmth, social observation, and place-pleasure.

## What not to do

- **No BBC dryness** — James's wit is warm; it does not perform cleverness at the reader's expense
- **No American crime cadence** — hard-boiled is a different genre
- **No over-explanation** — never explain what the detail already shows
- **No stated sentiment** — earned through observation, not announced
- **No noir menace** — pressure may tighten, but the world never becomes bleak, cynical, or hard-boiled
- **No sterile cleverness** — a brilliant observation that gives the reader no sensory or emotional pleasure is not enough
- **No generic domestic wallpaper** — food, rooms, weather, and objects must be specific to this town, this character, this moment
- **No gush** — warmth ≠ effusiveness; feeling is carried by concrete action and precise detail
