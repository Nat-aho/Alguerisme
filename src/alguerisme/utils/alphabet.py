"""Module defining the Alphabet and Letter value objects for dictionary indexing."""

from dataclasses import dataclass
from typing import Iterator, Union


@dataclass(frozen=True, order=True)
class Letter:
    """Value object representing a single dictionary letter index."""

    value: str

    def __post_init__(self):
        """Validate and normalize the letter."""
        if not isinstance(self.value, str):
            raise ValueError(f"Letter must be a string, got {type(self.value)}")

        cleaned = self.value.strip()

        if len(cleaned) != 1:
            raise ValueError(f"Letter must be a single character, got '{self.value}'")

        if not cleaned.isalpha():
            raise ValueError(f"Letter must be alphabetic, got '{self.value}'")

        object.__setattr__(self, "value", cleaned.upper())

    def __str__(self) -> str:
        """Allow str(letter) to get the raw letter value."""
        return self.value

    def __repr__(self) -> str:
        """Return the representation of the Letter."""
        return f"Letter('{self.value}')"


class Alphabet:
    """Represents the ordered collection of valid letters for the dictionary."""

    STANDARD_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    def __init__(self, chars: str = STANDARD_CHARS):
        """Initialize the Alphabet with the given characters."""
        self._letters = tuple(Letter(c) for c in chars)
        self._set = frozenset(self._letters)

    def __iter__(self) -> Iterator[Letter]:
        """Allow iteration over the letters in the Alphabet."""
        return iter(self._letters)

    def __contains__(self, item: Union[str, Letter]) -> bool:
        """Allow membership check over the Alphabet."""
        try:
            letter = item if isinstance(item, Letter) else Letter(item)
            return letter in self._set
        except ValueError:
            return False

    def __len__(self) -> int:
        """Return the number of letters in the Alphabet."""
        return len(self._letters)

    def validate_subset(self, candidates: list[str]) -> list[Letter]:
        """Validate that the given candidates are all in the Alphabet."""
        validated = []
        for raw in candidates:
            letter = Letter(raw)
            if letter not in self:
                raise ValueError(
                    f"Letter '{letter}' is not in the allowed dictionary alphabet."
                )
            validated.append(letter)
        return validated

    @classmethod
    def standard(cls) -> "Alphabet":
        """Create a standard Alphabet instance with A-Z."""
        return cls()


def normalize_letter(letter: str) -> str:
    """Validate and normalize a single letter to uppercase.

    This is the single source of truth for letter validation and normalization.
    Use this function everywhere you need to process letter input.

    Parameters
    ----------
    letter : str
        A single alphabetic character (any case)

    Returns
    -------
    str
        The validated letter in uppercase

    Raises
    ------
    ValueError
        If the input is not a single alphabetic character

    """
    validated = Letter(letter)  # This validates it
    return str(validated)  # This returns uppercase


def normalize_letters(letters: list[str], unique: bool = True) -> list[str]:
    """Validate and normalize multiple letters to uppercase.

    This is the single source of truth for validating letter lists.
    Use this function at entry points (CLI, API, etc.) to validate user input.

    Parameters
    ----------
    letters : list[str]
        A list of strings, each should be a single alphabetic character
    unique : bool
        If True, removes duplicate letters while preserving order (default: True)

    Returns
    -------
    list[str]
        Validated and normalized uppercase letters

    Raises
    ------
    ValueError
        If any letter is invalid or not in the alphabet
    """
    alphabet = Alphabet.standard()
    validated = alphabet.validate_subset(letters)
    result = [str(letter) for letter in validated]

    if unique:
        # Deduplicate while preserving order of first appearance
        seen = set()
        deduped = []
        for letter in result:
            if letter not in seen:
                deduped.append(letter)
                seen.add(letter)
        return deduped

    return result
