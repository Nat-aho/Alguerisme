"""Parser configuration model.

Keep runtime parser options here (parsing version and concurrency).
Selectors are defined on `WebDictionaryConfig` so parser selectors live
with the dictionary configuration.
"""

from pydantic import BaseModel, Field


class ParserConfig(BaseModel):
    """Runtime options for the HTML parser.

    Note: CSS selectors live in `WebDictionaryConfig`.
    """

    parsing_version: str = Field(
        default="1.0",
        description="Parser version for tracking schema changes",
    )

    max_workers: int = Field(
        default=10,
        description="Maximum concurrent parsing operations",
    )
