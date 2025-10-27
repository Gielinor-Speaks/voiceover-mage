# ABOUTME: Beautiful character profile renderer for webui - actor portfolio style layout
# ABOUTME: Generates HTML/CSS for rich visual presentation of NPCDetails with images and styling

from __future__ import annotations

from typing import Any


def _extract_field_value(obj: Any, field_name: str, default: Any = None) -> Any:
    """
    Extract a field value from either NPCDetails or legacy NPCWikiSourcedData.

    Handles TrackedField wrappers by accessing the .value attribute.
    """
    value = getattr(obj, field_name, default)

    # If it's a TrackedField, extract the actual value
    if hasattr(value, "value"):
        return value.value if value.value is not None else default

    return value if value is not None else default


def _map_legacy_to_modern_fields(profile: Any) -> dict[str, Any]:
    """
    Map legacy NPCWikiSourcedData fields to modern NPCDetails field names.

    Returns a dict with modern field names as keys.
    """
    # Try to extract from legacy format
    personality_traits = _extract_field_value(profile, "personality_traits", "")
    occupation = _extract_field_value(profile, "occupation", "")
    social_role = _extract_field_value(profile, "social_role", "")
    dialogue_patterns = _extract_field_value(profile, "dialogue_patterns", "")
    emotional_range = _extract_field_value(profile, "emotional_range", "")
    background_lore = _extract_field_value(profile, "background_lore", "")
    visual_archetype_val = _extract_field_value(profile, "visual_archetype", "Unknown")
    age_category = _extract_field_value(profile, "age_category", "")
    build_type = _extract_field_value(profile, "build_type", "")
    attire_style = _extract_field_value(profile, "attire_style", "")

    # Combine legacy fields into modern equivalents
    personality_profile = personality_traits or "No data available"

    voice_parts = []
    if dialogue_patterns:
        voice_parts.append(dialogue_patterns)
    if emotional_range:
        voice_parts.append(f"Emotional range: {emotional_range}")
    voice_characteristics = " ".join(voice_parts) if voice_parts else "No data available"

    background_parts = []
    if background_lore:
        background_parts.append(background_lore)
    if occupation:
        background_parts.append(f"Occupation: {occupation}")
    if age_category or build_type or attire_style:
        appearance_parts = [p for p in [age_category, build_type, attire_style] if p]
        background_parts.append(f"Appearance: {', '.join(appearance_parts)}")
    background_summary = " ".join(background_parts) if background_parts else "No data available"

    social_context = social_role or "No data available"

    return {
        "personality_profile": personality_profile,
        "voice_characteristics": voice_characteristics,
        "visual_archetype": visual_archetype_val,
        "background_summary": background_summary,
        "social_context": social_context,
    }


def render_character_profile_html(
    profile: Any,  # Accept any profile-like object
    chathead_url: str | None = None,
    image_url: str | None = None,
    npc_name: str | None = None,
) -> str:
    """
    Render a beautiful character profile layout like an actor's portfolio.

    Args:
        profile: The NPCDetails profile object
        chathead_url: URL to the character's chathead image
        image_url: URL to the character's full body/primary image
        npc_name: Display name for the NPC (overrides profile.npc_name if provided)

    Returns:
        HTML string with embedded CSS for beautiful profile display
    """
    # Detect if this is legacy NPCWikiSourcedData or modern NPCDetails
    has_personality_profile = hasattr(profile, "personality_profile")
    has_personality_traits = hasattr(profile, "personality_traits")

    # Use modern format if available, otherwise map from legacy
    if has_personality_profile:
        # Modern NPCDetails format
        field_values = {
            "personality_profile": getattr(profile, "personality_profile", "No data available"),
            "voice_characteristics": getattr(profile, "voice_characteristics", "No data available"),
            "visual_archetype": getattr(profile, "visual_archetype", "Unknown"),
            "background_summary": getattr(profile, "background_summary", "No data available"),
            "social_context": getattr(profile, "social_context", "No data available"),
        }
    elif has_personality_traits:
        # Legacy NPCWikiSourcedData format - convert it
        field_values = _map_legacy_to_modern_fields(profile)
    else:
        # Very old or incomplete data - use all defaults
        field_values = {
            "personality_profile": "No data available",
            "voice_characteristics": "No data available",
            "visual_archetype": "Unknown",
            "background_summary": "No data available",
            "social_context": "No data available",
        }

    # Extract name - works for both formats
    extracted_name = _extract_field_value(profile, "npc_name", _extract_field_value(profile, "name", "Unknown NPC"))
    display_name = npc_name or extracted_name

    # Handle variant - older data might not have this field
    variant = _extract_field_value(profile, "npc_variant", _extract_field_value(profile, "variant", None))
    variant_text = f" <span class='variant'>({variant})</span>" if variant else ""

    # Build hero section with large images
    hero_images_html = ""
    if chathead_url or image_url:
        hero_images_html = "<div class='hero-images'>"

        if chathead_url:
            hero_images_html += f"""
            <div class='hero-image-card chathead'>
                <img src="{chathead_url}" alt="{display_name} chathead" loading="lazy">
                <div class='image-label'>Chathead</div>
            </div>
            """

        if image_url:
            hero_images_html += f"""
            <div class='hero-image-card character'>
                <img src="{image_url}" alt="{display_name}" loading="lazy">
                <div class='image-label'>Character Sprite</div>
            </div>
            """

        hero_images_html += "</div>"

    # Extract confidence fields (only in modern NPCDetails format)
    synthesis_confidence = getattr(profile, "synthesis_confidence", None)
    text_confidence = getattr(profile, "text_confidence", None)
    visual_confidence = getattr(profile, "visual_confidence", None)
    synthesis_reasoning = getattr(profile, "synthesis_reasoning", None)

    # Use the field values we extracted earlier
    visual_archetype = field_values["visual_archetype"]
    personality_profile = field_values["personality_profile"]
    voice_characteristics = field_values["voice_characteristics"]
    background_summary = field_values["background_summary"]
    social_context = field_values["social_context"]

    # Build confidence bars section
    confidence_bars = ""
    if synthesis_confidence is not None and text_confidence is not None and visual_confidence is not None:
        confidence_bars = _render_confidence_section(
            overall=synthesis_confidence, text=text_confidence, visual=visual_confidence
        )

    # Build reasoning section
    reasoning_section = ""
    if synthesis_reasoning:
        reasoning_section = f"""
        <div class="reasoning-section">
            <div class="reasoning-label">💡 AI Analysis Reasoning</div>
            <div>{synthesis_reasoning}</div>
        </div>
        """

    # Main profile HTML
    html = f"""
    <style>
        .character-portfolio {{
            font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(
                135deg, var(--background-fill-primary) 0%, var(--background-fill-secondary) 100%
            );
            border-radius: 16px;
            padding: 32px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            max-width: 1400px;
            margin: 0 auto;
        }}

        .portfolio-header {{
            text-align: center;
            margin-bottom: 32px;
            padding-bottom: 24px;
            border-bottom: 3px solid var(--border-color-primary);
        }}

        .portfolio-header h1 {{
            margin: 0 0 12px 0;
            font-size: 3rem;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        .variant {{
            font-size: 1.5rem;
            font-weight: 400;
            opacity: 0.7;
        }}

        .archetype-badge {{
            display: inline-block;
            padding: 10px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 24px;
            font-size: 1rem;
            font-weight: 600;
            letter-spacing: 0.5px;
            margin-top: 12px;
        }}

        .hero-images {{
            display: flex;
            gap: 32px;
            justify-content: center;
            align-items: center;
            margin: 32px 0;
            padding: 24px;
            background: var(--background-fill-secondary);
            border-radius: 16px;
            border: 2px solid var(--border-color-primary);
        }}

        .hero-image-card {{
            position: relative;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            background: var(--background-fill-primary);
        }}

        .hero-image-card:hover {{
            transform: scale(1.05);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }}

        .hero-image-card.chathead img {{
            width: 300px;
            height: 300px;
            object-fit: contain;
        }}

        .hero-image-card.character img {{
            width: 400px;
            height: auto;
            max-height: 500px;
            object-fit: contain;
        }}

        .image-label {{
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            background: linear-gradient(to top, rgba(0,0,0,0.9), transparent);
            color: white;
            padding: 16px;
            font-size: 1rem;
            font-weight: 700;
            text-align: center;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }}

        .profile-row {{
            background: var(--background-fill-secondary);
            border-radius: 12px;
            padding: 28px;
            margin: 20px 0;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            border: 1px solid var(--border-color-primary);
        }}

        .section-title {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 16px;
            font-size: 1.4rem;
            font-weight: 700;
            color: var(--body-text-color);
            padding-bottom: 12px;
            border-bottom: 2px solid var(--border-color-primary);
        }}

        .section-icon {{
            font-size: 1.8rem;
        }}

        .section-content {{
            line-height: 1.8;
            font-size: 1.05rem;
            color: var(--body-text-color);
            opacity: 0.9;
        }}

        .confidence-section {{
            margin-top: 32px;
            padding: 28px;
            background: var(--background-fill-secondary);
            border-radius: 12px;
            border: 1px solid var(--border-color-primary);
        }}

        .confidence-bar {{
            margin: 20px 0;
        }}

        .confidence-label {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            font-size: 1rem;
            font-weight: 600;
        }}

        .bar-container {{
            height: 28px;
            background: var(--background-fill-primary);
            border-radius: 14px;
            overflow: hidden;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
        }}

        .bar-fill {{
            height: 100%;
            border-radius: 14px;
            transition: width 0.6s ease;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: flex-end;
            padding-right: 14px;
            color: white;
            font-size: 0.9rem;
            font-weight: 700;
        }}

        .reasoning-section {{
            margin-top: 24px;
            padding: 24px;
            background: var(--background-fill-primary);
            border-left: 4px solid #667eea;
            border-radius: 8px;
            font-style: italic;
            opacity: 0.85;
            font-size: 1.05rem;
        }}

        .reasoning-label {{
            font-weight: 700;
            font-style: normal;
            margin-bottom: 12px;
            color: #667eea;
            font-size: 1.1rem;
        }}
    </style>

    <div class="character-portfolio">
        <div class="portfolio-header">
            <h1>{display_name}{variant_text}</h1>
            <div class="archetype-badge">🎭 {visual_archetype}</div>
        </div>

        {hero_images_html}

        <div class="profile-row">
            <div class="section-title">
                <span class="section-icon">👤</span>
                <span>Personality</span>
            </div>
            <div class="section-content">
                {personality_profile}
            </div>
        </div>

        <div class="profile-row">
            <div class="section-title">
                <span class="section-icon">🎙️</span>
                <span>Voice Profile</span>
            </div>
            <div class="section-content">
                {voice_characteristics}
            </div>
        </div>

        <div class="profile-row">
            <div class="section-title">
                <span class="section-icon">📜</span>
                <span>Background</span>
            </div>
            <div class="section-content">
                {background_summary}
            </div>
        </div>

        <div class="profile-row">
            <div class="section-title">
                <span class="section-icon">🤝</span>
                <span>Social Context</span>
            </div>
            <div class="section-content">
                {social_context}
            </div>
        </div>

        {confidence_bars}

        {reasoning_section}
    </div>
    """

    return html


def _get_confidence_color(confidence: float) -> str:
    """Return color code based on confidence level."""
    if confidence >= 0.8:
        return "#10b981"  # Green
    elif confidence >= 0.6:
        return "#f59e0b"  # Orange
    else:
        return "#ef4444"  # Red


def _render_confidence_section(overall: float, text: float, visual: float) -> str:
    """Render confidence bars section."""
    return f"""
    <div class="confidence-section">
        <div class="section-title">
            <span class="section-icon">📊</span>
            <span>Analysis Confidence</span>
        </div>

        <div class="confidence-bar">
            <div class="confidence-label">
                <span>Overall Synthesis</span>
                <span style="color: {_get_confidence_color(overall)}">{overall:.1%}</span>
            </div>
            <div class="bar-container">
                <div class="bar-fill" style="width: {overall * 100}%">
                    {overall:.0%}
                </div>
            </div>
        </div>

        <div class="confidence-bar">
            <div class="confidence-label">
                <span>Text Analysis</span>
                <span style="color: {_get_confidence_color(text)}">{text:.1%}</span>
            </div>
            <div class="bar-container">
                <div class="bar-fill" style="width: {text * 100}%">
                    {text:.0%}
                </div>
            </div>
        </div>

        <div class="confidence-bar">
            <div class="confidence-label">
                <span>Visual Analysis</span>
                <span style="color: {_get_confidence_color(visual)}">{visual:.1%}</span>
            </div>
            <div class="bar-container">
                <div class="bar-fill" style="width: {visual * 100}%">
                    {visual:.0%}
                </div>
            </div>
        </div>
    </div>
    """
