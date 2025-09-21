# Voiceover Mage - AI Voice Generation for OSRS NPCs

## Product Context
Voiceover Mage generates character voices for Old School RuneScape NPCs by processing wiki data and creating ElevenLabs Voice Design API-compatible prompts.

**Data Flow**: Wiki NPC Data → Character Analysis → Voice Profile → ElevenLabs Voice Design → Audio Sample

## Implementation Guidelines

### Character Analysis Requirements
- Extract personality traits from NPC dialogue, quest interactions, and lore descriptions
- Map character archetypes to voice characteristics (age, accent, tone, speech patterns)
- Preserve RuneScape's medieval fantasy setting in voice descriptions
- Handle NPCs with minimal lore by inferring from role/location context

### Voice Profile Generation
- Generate descriptive prompts focusing on: vocal tone, accent, age, personality traits, speech pace
- Include specific RuneScape context (e.g., "gruff dwarf merchant", "mystical wizard elder")
- Avoid modern references or anachronistic language
- Keep prompts concise but descriptive (50-150 words optimal for ElevenLabs)

### Code Architecture Patterns
- Use Pydantic models for NPC character profiles
- Implement template-based prompt generation with character trait mapping
- Structure code for batch processing multiple NPCs
- Include validation for ElevenLabs API prompt format requirements

### API Integration Standards
- Use ElevenLabs existing Python SDK where possible
- Follow ElevenLabs Voice Design API specifications exactly
- Implement proper error handling for API rate limits and failures
- Cache generated profiles to avoid regeneration
- Log all API interactions for debugging and optimization

### Quality Assurance
- Validate generated voices match character expectations through automated grading
- Maintain character authenticity over technical convenience
- Save final selected voice sample