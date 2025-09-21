# ABOUTME: Two-step DSPy module for NPC image identification and visual characteristic extraction
# ABOUTME: Step 1: Identify correct images from markdown, Step 2: Analyze image pixels for visual traits

from typing import cast

import dspy
import httpx
from pydantic import BaseModel, Field

from voiceover_mage.config import get_config
from voiceover_mage.utils.logging import get_logger


class NPCVisualCharacteristics(BaseModel):
    """Visual characteristics extracted from NPC images and descriptions."""

    # Image URLs
    chathead_image_url: str | None = Field(default=None, description="URL to the NPC's chathead/portrait image")
    image_url: str | None = Field(default=None, description="URL to the NPC's main/full body image")

    # Physical appearance traits that mirror text characteristics
    age_category: str = Field(
        default="", description="Apparent age category (e.g., 'young adult', 'middle-aged', 'elderly', 'ancient')"
    )
    build_type: str = Field(
        default="", description="Physical build (e.g., 'slender', 'stocky', 'muscular', 'frail', 'imposing')"
    )
    attire_style: str = Field(
        default="",
        description="Descriptive clothing and equipment style (e.g., 'flowing wizard robes with golden embroidery')",
    )
    distinctive_features: str = Field(
        default="",
        description="Descriptive notable visual features (e.g., 'long braided beard, battle scars across cheek')",
    )
    color_palette: str = Field(
        default="",
        description="Descriptive color palette (e.g., 'deep sapphire blue robes with golden trim')",
    )
    visual_archetype: str = Field(
        default="", description="Visual archetype (e.g., 'wizard', 'warrior', 'merchant', 'peasant', 'noble')"
    )
    confidence_score: float = Field(default=0.0, description="Confidence in the extraction accuracy (0.0-1.0)")
    reasoning: str = Field(
        default="", description="Explanation of how images were identified and visual traits determined"
    )


class ImageIdentificationSignature(dspy.Signature):
    """Step 1: Identify correct NPC images from wiki markdown content.

    Analyze markdown to find the primary NPC's chathead and main body images.
    Handle cases where multiple NPCs appear on the same page.
    """

    markdown_content: str = dspy.InputField(description="Raw markdown content from the NPC's wiki page")
    npc_name: str = dspy.InputField(description="Name of the target NPC to extract images for")
    npc_variant: str = dspy.InputField(
        description="Optional NPC variant (e.g., 'Pete', 'Peta', 'Ardougne', 'Blue shirt') or 'None' if no variant"
    )

    chathead_url: str = dspy.OutputField(description="URL to the NPC's chathead/portrait image, or 'None' if not found")
    image_url: str = dspy.OutputField(description="URL to the NPC's main/full body image, or 'None' if not found")
    confidence: float = dspy.OutputField(
        description="Confidence score from 0.0 to 1.0 for image identification accuracy"
    )
    reasoning: str = dspy.OutputField(description="Step-by-step reasoning for how images were identified and selected")


class VisualAnalysisSignature(dspy.Signature):
    """Step 2: Analyze actual image pixels to extract visual characteristics.

    Given NPC images, analyze the visual content to determine age, build, attire,
    and other physical characteristics of the NPC from Old School RuneScape.
    """

    npc_name: str = dspy.InputField(description="Name of the NPC being analyzed")
    npc_variant: str = dspy.InputField(description="NPC variant or 'None' if no variant")
    chathead_image: dspy.Image | None = dspy.InputField(description="NPC's chathead/portrait image from OSRS wiki")
    main_image: dspy.Image | None = dspy.InputField(description="NPC's main/full body image from OSRS wiki")

    age_category: str = dspy.OutputField(
        description="Apparent age category from visual analysis (young adult, middle-aged, elderly, ancient)"
    )
    build_type: str = dspy.OutputField(
        description="Physical build from visual analysis (slender, stocky, muscular, frail, imposing)"
    )
    attire_style: str = dspy.OutputField(
        description="Descriptive clothing and equipment style observed in images (e.g., 'flowing wizard robes')"
    )
    distinctive_features: str = dspy.OutputField(
        description="Descriptive notable visual features seen in images (e.g., 'weathered face with scar')"
    )
    color_palette: str = dspy.OutputField(
        description="Descriptive color palette observed in the images (e.g., 'deep blues and purples')",
    )
    visual_archetype: str = dspy.OutputField(
        description="Overall visual archetype based on appearance (wizard, warrior, merchant, etc.)"
    )
    confidence: float = dspy.OutputField(description="Confidence score from 0.0 to 1.0 for visual analysis accuracy")
    reasoning: str = dspy.OutputField(description="Step-by-step reasoning for visual characteristic determination")


class ImageDetailExtractor(dspy.Module):
    """Two-step DSPy module for intelligent NPC image extraction and visual analysis.

    Step 1: Identify correct images from markdown (smart image identification)
    Step 2: Load and analyze image pixels for visual characteristics

    This module:
    1. Uses LLM reasoning to identify the correct NPC's images from wiki markdown
    2. Downloads and analyzes actual image content using vision capabilities
    3. Handles pages with multiple NPCs by focusing on the primary target
    4. Provides confidence scores and reasoning for both steps
    """

    def __init__(self, http_client: httpx.AsyncClient | None = None):
        super().__init__()

        # Configure DSPy with Gemini for vision capabilities
        config = get_config()
        if config.gemini_api_key:
            # Configure DSPy to use Gemini Pro Vision
            lm = dspy.LM("gemini/gemini-2.5-flash", api_key=config.gemini_api_key)
            dspy.configure(lm=lm)

        self.identify_images = dspy.ChainOfThought(ImageIdentificationSignature)
        self.analyze_visuals = dspy.ChainOfThought(VisualAnalysisSignature)
        self.http_client = http_client or httpx.AsyncClient(
            headers={"User-Agent": "Gielinor-Speaks/1.0 (https://github.com/gielinor-speaks/)"}
        )
        self.logger = get_logger(__name__)

    def forward(self, markdown_content: str, npc_name: str, npc_variant: str | None = None) -> NPCVisualCharacteristics:
        """Sync wrapper around aforward() for backward compatibility.

        Args:
            markdown_content: Raw markdown content from wiki page
            npc_name: Name of the NPC to extract images for
            npc_variant: Optional variant (e.g., 'Pete', 'Ardougne', 'Blue shirt')

        Returns:
            NPCVisualCharacteristics with URLs, visual traits, and confidence
        """
        import anyio

        return anyio.run(self.aforward, markdown_content, npc_name, npc_variant)

    async def aforward(
        self, markdown_content: str, npc_name: str, npc_variant: str | None = None
    ) -> NPCVisualCharacteristics:
        """Async version of forward for native DSPy async support.

        Args:
            markdown_content: Raw markdown content from wiki page
            npc_name: Name of the NPC to extract images for
            npc_variant: Optional variant (e.g., 'Pete', 'Ardougne', 'Blue shirt')

        Returns:
            NPCVisualCharacteristics with URLs, visual traits, and confidence
        """
        # Prepare variant for DSPy (convert None to "None" string)
        variant_str = npc_variant or "None"

        # Step 1: Identify correct images from markdown using async
        image_id_result = await self.identify_images.acall(
            markdown_content=markdown_content, npc_name=npc_name, npc_variant=variant_str
        )
        # Type annotation for DSPy result (has chathead_url, image_url attributes)
        image_id_result = cast("ImageIdentificationSignature", image_id_result)

        # Parse image URLs and handle "None" strings
        chathead_url = None if image_id_result.chathead_url.lower() == "none" else image_id_result.chathead_url
        image_url = None if image_id_result.image_url.lower() == "none" else image_id_result.image_url

        # Step 2: Load images and analyze visual characteristics
        try:
            # Load images using DSPy's Image.from_url()
            chathead_image = dspy.Image.from_url(chathead_url) if chathead_url else None
            main_image = dspy.Image.from_url(image_url) if image_url else None

            # Skip visual analysis if both images are blank
            if not chathead_image and not main_image:
                raise ValueError("Both chathead and main images are unavailable for visual analysis.")

            # Use DSPy vision analysis with actual images using async
            visual_result = await self.analyze_visuals.acall(
                npc_name=npc_name, npc_variant=variant_str, chathead_image=chathead_image, main_image=main_image
            )
            # Type annotation for DSPy result (has age_category, build_type, etc. attributes)
            visual_result = cast("VisualAnalysisSignature", visual_result)

        except Exception as e:
            # Fallback if image loading fails
            self.logger.warning(f"Failed to load images for visual analysis: {e}")
            # Create minimal placeholder response
            visual_result = type(
                "obj",
                (object,),
                {
                    "age_category": "unknown",
                    "build_type": "unknown",
                    "attire_style": "unknown attire",
                    "distinctive_features": "unable to determine features",
                    "color_palette": "unknown colors",
                    "visual_archetype": "unknown",
                    "confidence": 0.0,
                    "reasoning": f"Image loading failed: {e}",
                },
            )()  # Instantiate the class
            # Type annotation for fallback result
            visual_result = cast("VisualAnalysisSignature", visual_result)

        # Combine confidence scores (weighted average)
        combined_confidence = image_id_result.confidence * 0.3 + visual_result.confidence * 0.7
        combined_reasoning = f"Image ID: {image_id_result.reasoning} | Visual Analysis: {visual_result.reasoning}"

        return NPCVisualCharacteristics(
            chathead_image_url=chathead_url,
            image_url=image_url,
            age_category=visual_result.age_category,
            build_type=visual_result.build_type,
            attire_style=visual_result.attire_style,
            distinctive_features=visual_result.distinctive_features,
            color_palette=visual_result.color_palette,
            visual_archetype=visual_result.visual_archetype,
            confidence_score=float(combined_confidence),
            reasoning=combined_reasoning,
        )
