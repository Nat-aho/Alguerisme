"""Configuration model for the dictionary website."""

from pydantic import BaseModel, Field

from alguerisme.utils.alphabet import Alphabet


class WebDictionaryConfig(BaseModel):
    """Configuration describing the structure of the dictionary website."""

    base_url: str = Field(
        default="https://www.algueres.net/",
        description="Base URL of the dictionary site",
    )
    letters: str = Field(
        default=Alphabet.STANDARD_CHARS,
        description="Letters/prefixes to crawl",
    )
    index_url_template: str = Field(
        default="{base_url}/index.aspx?lletra={letter}&p={page}"
    )
    entry_link_selector: str = Field(default="a[href*='/vocabols/']")
    entry_link_prefix: str = Field(default="/vocabols/")
    entry_link_suffix: str = Field(default=".aspx")
    content_selector: str = Field(default="#cntBody_pnlNews")
    # Selectors used by the HTML parser to extract structured fields
    algueres_word_selector: str = Field(
        default="#cntBody_label_Alg",
        description="CSS selector for Alguerés word",
    )
    algueres_definition_selector: str = Field(
        default="#cntBody_txtDefinizione_Alg",
        description="CSS selector for Alguerés definition",
    )
    catalan_word_selector: str = Field(
        default="#cntBody_label_Cat",
        description="CSS selector for Catalan word",
    )
    catalan_definition_selector: str = Field(
        default="#cntBody_txtDefinizione_Cat",
        description="CSS selector for Catalan definition",
    )
    italian_word_selector: str = Field(
        default="#cntBody_label_Ita",
        description="CSS selector for Italian word",
    )
    italian_definition_selector: str = Field(
        default="#cntBody_txtDefinizione_Ita",
        description="CSS selector for Italian definition",
    )
    image_selector: str = Field(
        default="#cntBody_pnlFoto img[src]",
        description="CSS selector for images",
    )
    audio_embed_selector: str = Field(
        default="#cntBody_pnlAudio embed",
        description="CSS selector for audio embeds",
    )
    audio_tag_selector: str = Field(
        default="#cntBody_pnlAudio audio[src]",
        description="CSS selector for audio tags",
    )
