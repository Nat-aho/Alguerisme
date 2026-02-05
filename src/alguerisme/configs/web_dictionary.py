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
