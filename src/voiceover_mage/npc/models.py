# ABOUTME: Data models for raw NPC information extracted from wiki sources
# ABOUTME: Contains base Pydantic models for NPC data before character analysis

from typing import Literal

from pydantic import BaseModel, Field


class RawNPCData(BaseModel):
    """Raw NPC data extracted from wiki sources."""

    name: str = Field(..., description="The name of the NPC")
    chathead_image_url: str | None = Field(None, description="The URL of the NPC's chathead image")
    image_url: str | None = Field(None, description="The URL of the NPC's image")
    gender: Literal["male", "female", "unknown"] = Field(..., description="The gender of the NPC")
    race: str = Field(..., description="The race of the NPC")
    location: str = Field(..., description="The location of the NPC")
    examine_text: str = Field(..., description="The examine text of the NPC")
    description: str = Field(..., description="A description of the NPC based on the wiki page.")
    personality: str = Field(..., description="The personality of the NPC")
