# Extraction Layer

**Purpose**: Extract data from external sources and convert to structured formats.

## Architecture

```
External Sources (Wiki) → extraction/wiki/ → extraction/analysis/ → Structured Data
```

## Components

### `wiki/`
- `base.py` - Base wiki extractor interface  
- `crawl4ai.py` - Crawl4AI implementation
- `markdown.py` - Markdown processing and parsing

### `analysis/`
- `text.py` - DSPy text analysis module
- `image.py` - DSPy image analysis module  
- `intelligent.py` - Orchestrating extractor
- `synthesizer.py` - Data synthesis module

### `models.py`
- `NPCRawExtractionData` - Raw wiki data structure
- `NPCTextCharacteristics` - Text analysis results
- `NPCImageCharacteristics` - Image analysis results

## Data Flow

1. **Raw Extraction**: Wiki URL → Raw markdown + image URLs
2. **Analysis**: Raw data → AI-powered text/image analysis  
3. **Output**: Structured Pydantic models ready for persistence