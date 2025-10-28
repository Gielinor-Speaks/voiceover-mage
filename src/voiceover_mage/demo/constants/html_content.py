# ABOUTME: HTML content constants for the demo UI (separated for clean code organization)

"""
Static HTML content used throughout the demo interface.
Following React patterns, this separates content from component logic.
"""

HERO_HEADER = """
<div style="text-align: center; margin-bottom: 20px;">
    <h1>Gielinor Speaks: Context-Aware Voice Generation for OSRS</h1>
    <p style="color: #666;">Demonstration of AI-powered NPC voice synthesis with emotion-aware delivery</p>
</div>
"""

PIPELINE_FLOW = """
<div style="text-align: center; margin: 30px 0 20px 0; padding: 20px;
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
            border-radius: 10px; border: 2px solid var(--border-color-primary);">
    <div style="display: flex; align-items: center; justify-content: center; gap: 20px; flex-wrap: wrap;">
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 24px;">📖</span>
            <span style="font-weight: bold;">Wiki Data</span>
        </div>
        <span style="font-size: 20px; color: #667eea;">→</span>
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 24px;">🧠</span>
            <span style="font-weight: bold;">AI Analysis</span>
        </div>
        <span style="font-size: 20px; color: #764ba2;">→</span>
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 24px;">🎭</span>
            <span style="font-weight: bold;">Voice Design</span>
        </div>
        <span style="font-size: 20px; color: #667eea;">→</span>
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 24px;">🎵</span>
            <span style="font-weight: bold;">Speech Synthesis</span>
        </div>
    </div>
</div>
"""

WIKI_SOURCE_DESCRIPTION = (
    "*This is the raw source material extracted from the OSRS Wiki. "
    "Our AI analyzes this content to understand the character's personality, background, and traits.*"
)

CHARACTER_PROFILE_HEADER = """
<div style="text-align: center; margin: 30px 0 15px 0;">
    <h2 style="font-size: 28px; margin: 0; display: flex; align-items: center;
               justify-content: center; gap: 10px;">
        <span style="font-size: 32px;">🧠</span>
        <span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                     -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                     background-clip: text;">
            AI-Generated Character Profile
        </span>
    </h2>
    <p style="color: #666; margin-top: 8px; font-size: 14px;">
        Personality traits, vocal characteristics, and speaking style inferred from wiki content
    </p>
</div>
"""

VOICE_CANDIDATES_HEADER = """
<div style="text-align: center; margin: 40px 0 15px 0;">
    <h2 style="font-size: 28px; margin: 0; display: flex; align-items: center;
               justify-content: center; gap: 10px;">
        <span style="font-size: 32px;">🎭</span>
        <span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                     -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                     background-clip: text;">
            Voice Design Candidates
        </span>
    </h2>
    <p style="color: #666; margin-top: 8px; font-size: 14px;">
        ElevenLabs Voice Design generates multiple voice options based on character traits
    </p>
</div>
"""

DIALOGUE_SAMPLES_HEADER = """
<div style="text-align: center; margin: 40px 0 15px 0;">
    <h2 style="font-size: 28px; margin: 0; display: flex; align-items: center;
               justify-content: center; gap: 10px;">
        <span style="font-size: 32px;">🎵</span>
        <span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                     -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                     background-clip: text;">
            Emotion-Aware Speech Synthesis
        </span>
    </h2>
    <p style="color: #666; margin-top: 8px; font-size: 14px;">
        Context-aware dialogue generation with dynamic emotional expression
    </p>
</div>
"""


def get_wiki_error_html(wiki_url: str, error_msg: str) -> str:
    """Generate error HTML for failed wiki fetches."""
    return f"""
    <div style="padding: 20px;">
        <p style="color: #ff6b6b; margin-bottom: 15px;">⚠️ Failed to load wiki page: {error_msg}</p>
        <a href="{wiki_url}" target="_blank" style="
            display: inline-block;
            padding: 10px 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: bold;
        ">🔗 Open on OSRS Wiki</a>
    </div>
    """


def get_wiki_no_url_html() -> str:
    """Generate placeholder HTML when no wiki URL is available."""
    return '<p style="color: #666; padding: 20px;">No wiki URL available</p>'


WIKI_PAGE_STYLES = """
<style>
    .wiki-container {
        font-family: sans-serif;
        padding: 20px;
        line-height: 1.6;
    }
    .wiki-header {
        margin-bottom: 15px;
        padding-bottom: 15px;
        border-bottom: 2px solid var(--border-color-primary);
    }
    .wiki-button {
        display: inline-block;
        padding: 10px 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        text-decoration: none;
        border-radius: 6px;
        font-weight: bold;
        font-size: 14px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        transition: transform 0.2s;
    }
    .wiki-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
    }
    .wiki-content a {
        color: var(--link-text-color) !important;
        text-decoration: underline;
    }
    .wiki-content a:hover {
        opacity: 0.8;
    }
    .wiki-content table {
        border-collapse: collapse;
        margin: 15px 0;
        border: 1px solid var(--border-color-primary);
    }
    .wiki-content th, .wiki-content td {
        border: 1px solid var(--border-color-primary);
        padding: 8px;
    }
    .wiki-content th {
        background: var(--background-fill-secondary);
        font-weight: bold;
    }
    .wiki-content img {
        max-width: 100%;
        height: auto;
    }
    .wiki-content .infobox {
        float: right;
        margin: 0 0 10px 10px;
        background: var(--background-fill-secondary);
        border: 1px solid var(--border-color-primary);
        padding: 10px;
    }
</style>
"""
