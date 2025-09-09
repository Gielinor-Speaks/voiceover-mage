import dspy

from voiceover_mage.core.models import NPCProfile

# Summarized from https://elevenlabs.io/docs/product-guides/voices/voice-design
ELEVENLABS_INSTRUCTIONS = """
Construct a detailed voice description and its accompanying parameters for the ElevenLabs API, tailored to
Old School RuneScape (OSRS). Keep descriptions lore-aware, medieval-fantasy appropriate, and free of modern slang.

1. Generate a Core Voice Description (OSRS)

Begin with the NPC's place in Gielinor: region (e.g., Misthalin, Fremennik, Karamja), role (guard, merchant,
scholar, noble), race or culture when clear (human, dwarf, elf, gnome, Fremennik, etc.), and personality.

* Principle: Layer region → accent, role → delivery, personality → emotion.
* Example (guard): "A precise Varrock guard with light RP British delivery, measured pace, and restrained authority."
* Example (merchant): "A warm Lumbridge shopkeeper with a soft rural British lilt and quick but clear speech."
* Example (scholar): "An Arceuus researcher with a quiet, breathy cadence and reflective, arcane undertone."

2. Layer with OSRS-specific Attributes

Add concrete descriptors from the categories below. Keep phrasing suitable for in-game dialogue.

##### 2.1. Define the Audio Quality (clean in-world)
Prefer clean, close-mic delivery suitable for game dialogue.
* Use: "studio-quality recording", "crystal-clear voice", "no reverb", "natural room tone".
* Avoid: phone/radio effects or heavy stylization.

##### 2.2. Specify the Age (as OSRS archetypes)
Tie age to common roles.
* Youthful: "adolescent squire", "young adult apprentice", "fresh-faced recruit".
* Mid-Life: "seasoned adventurer", "middle-aged merchant", "journeyman artisan".
* Senior: "elderly sage", "aged duke", "old master craftsman".

##### 2.3. Tone, Timbre, and Pitch (fantasy-appropriate)
Choose descriptors that fit OSRS archetypes and locales.
* Pitch: "deep", "low-pitched", "mid-pitched", "high-pitched".
* Texture: "smooth", "rich", "buttery", "gravelly", "raspy", "weathered", "work-worn".
* Delivery archetypes: "courtly and precise", "boisterous tavern warmth", "stoic guard cadence",
  "scholarly and careful", "world-weary traveler", "brisk maritime pragmatism".

##### 2.4. Gender (simple and respectful)
Keep descriptors compact and performance-oriented.
* Direct: "male", "female", "gender-neutral".
* Descriptive: "husky female voice, lower-pitched", "androgynous, soft mid-range".

##### 2.5. Add a Specific Accent (RuneScape-aware)
Define the voice's regional and cultural identity with precision, preferring accents that fit Gielinor (RuneScape) lore.
This is very important!!!
* Be Specific: Instead of "European," use precise terms like "light Midlands British" or "soft Welsh lilt".
* Indicate Prominence: Use "thick", "heavy", "slight", or "soft" to define the accent's strength.
* Avoid Vague Terms: Do not use "foreign" or "exotic". Avoid caricature and stereotypes.
* World Guidance (use respectfully, never exaggerated):
  - Misthalin/Asgarnia/Kandarin (Lumbridge, Varrock, Falador, Ardougne):
    British Isles accents. Nobility/officials → Received Pronunciation; commoners → light rural British or West Country
    hints.
  - Karamja (Brimhaven, Shilo Village, Tai Bwo Wannai):
    island/coastal cadence with relaxed rhythm; neutral international English with occasional local idioms.
    Avoid caricature.
  - Kharidian Desert (Al Kharid, Pollnivneach, Sophanem, Menaphos):
    measured, formal tone with warm vowels; prefer neutral international English. Avoid stereotyped "Arabian"
    caricature; reflect setting via calm delivery and precise diction.
  - Zeah / Great Kourend (Shayzien, Arceuus, Hosidius, Piscarilius, Lovakengj):
    Shayzien → clipped, disciplined military delivery; Arceuus → scholarly, breathy, arcane undertone;
    Hosidius → friendly rural/coastal warmth; Piscarilius → brisk maritime pragmatism; Lovakengj → industrial,
    soot-worn rasp with practical focus.
  - Fremennik Province (Rellekka): Nordic or Northern UK flavor (subtle), sturdy cadence.
  - Morytania (Canifis, Meiyerditch): somber tone with faint Eastern-European-tinged cadence.
  - Dwarves (Keldagrim): stout Northern British/Scottish hints; lower pitch, work-worn timbre.
  - Elves (Tirannwn): soft, musical Welsh-like lilt; clear articulation.
  - TzHaar (Mor Ul Rek): deep, resonant, volcanic timbre; deliberate pacing.
  - Gnomes (Tree Gnome areas): light, nimble, curious; quick but clear articulation.
  - Trolls/Ogres: heavy, blunt diction with simplified syntax; keep respectful, avoid demeaning portrayals.
  - Pirates/Seafarers: classic West Country register kept light, not comedic.
* When unsure: prefer neutral British English for most Misthalin/Asgarnia towns. Avoid modern American slang.

##### 2.6. Pacing and Rhythm (match OSRS dialogue)
Mirror short NPC interactions.
* Guards/officials: clipped, efficient phrasing with steady pauses.
* Scholars/sages: measured, reflective cadence with careful emphasis.
* Vendors/commoners: lively but clear; friendly intonation.
* Seafarers/Fremennik: rolling cadence with firm beats; keep subtle and non-caricatured.
Use concise sentences with natural pauses.

##### 2.7. Emotion and Character (OSRS archetypes)
Anchor emotion to role and region.
* Emotions: "dry wit", "stoic duty", "warm hospitality", "somber resolve", "curious awe".
* Professions: city guard, duke/official, scholar/mage, monk/priest, dwarven engineer, Fremennik warrior,
  elf ranger, desert envoy, pirate quartermaster, shady Varrock merchant.

3. Write a Matching Preview Text (in-world lines)

Write 1-3 sentences that could appear in OSRS. Match region and role; prefer medieval-fantasy vocabulary;
avoid modern slang and anachronisms. Include proper nouns sparingly (e.g., Lumbridge, Varrock, Karamja,
Morytania, Kourend) when natural. Keep the line actionable (a greeting, a hint, a task, or a lore note).
Aim for 100-160 characters for stable preview quality.

* Non-matching example: "Hey! That app totally crashed my vibe!!!"
* Matching (guard): "Move along, please. Orders from the keep—no loitering by the east gate after dusk."
* Matching (merchant): "Fresh stock today—mind the crates, they're bound for Ardougne by morning tide."
""".strip()


class ElevenLabsPromptSignature(dspy.Signature):
    """Generates an ElevenLabs-optimized voice prompt from a character profile."""

    npc_profile: NPCProfile = dspy.InputField(desc="The character profile optimized for voice generation.")
    voice_description: str = dspy.OutputField(
        desc="A 50-150 word descriptive voice prompt for ElevenLabs. (>=20 characters and <=1000 characters)"
    )
    sample_text: str = dspy.OutputField(
        desc="A short sample text matching the voice description. (>=100 characters and <=1000 characters)"
    )


class ElevenLabsVoicePromptGenerator(dspy.Module):
    """DSPy module for generating ElevenLabs-specific voice prompts."""

    def __init__(self):
        super().__init__()
        # Note: Passing instructions positionally can conflict with dspy's signature.
        # Keep constructor minimal; prompt instructions can be managed via settings if needed.
        self.generator = dspy.ChainOfThought(ElevenLabsPromptSignature.with_instructions(ELEVENLABS_INSTRUCTIONS))

    async def aforward(self, npc_profile: NPCProfile) -> dict[str, str]:
        """Asynchronously generates the voice description and sample text."""
        result = await self.generator.acall(npc_profile=npc_profile)
        return {
            "voice_description": result.voice_description,
            "sample_text": result.sample_text,
            "reasoning": result.reasoning,
        }
