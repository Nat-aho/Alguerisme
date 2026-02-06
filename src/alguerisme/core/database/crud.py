"""CRUD operations for EntryURLs."""

from typing import Optional
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, select

from alguerisme.utils.alphabet import normalize_letter

from .models import EntryURLs, EntryURLsCreate, EntryURLsUpdate


def create_entry_url(
    session: Session, entry_create: EntryURLsCreate, commit: bool = False
) -> EntryURLs:
    """Create a new URL entry.

    Parameters
    ----------
    session : Session
        Database session
    entry_create : EntryURLsCreate
        Data for creating the entry
    commit : bool
        Whether to commit the transaction immediately. Default False.
        Allows caller to control transaction boundaries.

    Returns
    -------
    EntryURLs
        The created EntryURLs instance

    """
    # Convert Create model to DB model
    entry = EntryURLs.model_validate(entry_create)
    session.add(entry)
    if commit:
        session.commit()
        session.refresh(entry)
    else:
        # Flush to get the ID without committing
        session.flush()
        session.refresh(entry)
    return entry


def get_or_create_entry_url(
    session: Session, url: str, letter: Optional[str] = None, commit: bool = False
) -> tuple[EntryURLs, bool]:
    """Get existing URL entry or create new one.

    Parameters
    ----------
    session : Session
        Database session
    url : str
        The URL to get or create
    letter : Optional[str]
        Optional letter (used only if creating). Will be normalized to uppercase.
    commit : bool
        Whether to commit the transaction immediately. Default False.
        Allows caller to control transaction boundaries.

    Returns
    -------
    tuple[EntryURLs, bool]
        A tuple containing the EntryURLs instance and a boolean indicating
        whether it was created (True) or already existed (False)

    """
    existing = find_entry_url_by_url(session, url)
    if existing:
        return existing, False

    normalized_letter = normalize_letter(letter) if letter else None

    entry_create = EntryURLsCreate(url=url, letter=normalized_letter)
    entry = create_entry_url(session, entry_create, commit=commit)
    return entry, True


def get_entry_url_by_id(session: Session, id: UUID) -> Optional[EntryURLs]:
    """Get URL entry by ID.

    Parameters
    ----------
    session : Session
        Database session
    id : UUID
        Entry UUID

    Returns
    -------
    Optional[EntryURLs]
        EntryURLs if found, None otherwise

    """
    return session.get(EntryURLs, id)


def find_entry_url_by_url(session: Session, url: str) -> Optional[EntryURLs]:
    """Find URL entry by URL string.

    Parameters
    ----------
    session : Session
        Database session
    url : str
        URL string to search for

    Returns
    -------
    Optional[EntryURLs]
        EntryURLs if found, None otherwise

    """
    statement = select(EntryURLs).where(EntryURLs.url == url)
    return session.exec(statement).first()


def get_all_entry_urls(session: Session) -> list[EntryURLs]:
    """Get all URL entries.

    Parameters
    ----------
    session : Session
        Database session

    Returns
    -------
    list[EntryURLs]
        List of all EntryURLs

    """
    return list(session.exec(select(EntryURLs)).all())


def get_entry_urls_by_letter(session: Session, letter: str) -> list[EntryURLs]:
    """Get all URLs for a specific letter.

    Parameters
    ----------
    session : Session
        Database session
    letter : str
        Letter to filter by (will be normalized to uppercase)

    Returns
    -------
    list[EntryURLs]
        List of EntryURLs for the letter

    """
    # Normalize letter to ensure uppercase and valid format
    normalized_letter = normalize_letter(letter)
    statement = select(EntryURLs).where(EntryURLs.letter == normalized_letter)
    return list(session.exec(statement).all())


def get_entry_urls_paginated(
    session: Session,
    limit: int = 50,
    offset: int = 0,
    letter: Optional[str] = None,
) -> list[EntryURLs]:
    """Get URL entries with pagination.

    Parameters
    ----------
    session : Session
        Database session
    limit : int
        Maximum number of entries to return (default: 50)
    offset : int
        Number of entries to skip (default: 0)
    letter : Optional[str]
        Optional letter to filter by (will be normalized to uppercase)

    Returns
    -------
    list[EntryURLs]
        List of EntryURLs (paginated)

    """
    statement = select(EntryURLs)
    if letter:
        normalized_letter = normalize_letter(letter)
        statement = statement.where(EntryURLs.letter == normalized_letter)
    statement = statement.offset(offset).limit(limit)
    return list(session.exec(statement).all())


def update_entry_url(
    session: Session, id: UUID, entry_update: EntryURLsUpdate
) -> Optional[EntryURLs]:
    """Update an existing URL entry.

    Parameters
    ----------
    session : Session
        Database session
    id : UUID
        ID of entry to update
    entry_update : EntryURLsUpdate
        Fields to update (only non-None fields are updated)

    Returns
    -------
    Optional[EntryURLs]
        Updated entry if found, None otherwise

    """
    entry = session.get(EntryURLs, id)
    if not entry:
        return None

    # Update only fields that are set (not None)
    update_data = entry_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(entry, field, value)

    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def delete_entry_url(session: Session, id: UUID) -> bool:
    """Delete a URL entry by ID.

    Parameters
    ----------
    session : Session
        Database session
    id : UUID
        Entry UUID to delete

    Returns
    -------
    bool
        True if deleted, False if not found

    """
    entry = session.get(EntryURLs, id)
    if entry:
        session.delete(entry)
        session.commit()
        return True
    return False


def entry_url_exists(session: Session, url: str) -> bool:
    """Check if URL exists.

    Parameters
    ----------
    session : Session
        Database session
    url : str
        URL string to check

    Returns
    -------
    bool
        True if URL exists, False otherwise

    """
    return find_entry_url_by_url(session, url) is not None


def count_entry_urls(session: Session) -> int:
    """Count total URL entries.

    Parameters
    ----------
    session : Session
        Database session

    Returns
    -------
    int
        Total number of URLs

    """
    statement = select(func.count()).select_from(EntryURLs)
    return session.exec(statement).one()


def count_entry_urls_by_letter(session: Session, letter: str) -> int:
    """Count URLs for a specific letter.

    Parameters
    ----------
    session : Session
        Database session
    letter : str
        Letter to count

    Returns
    -------
    int
        Number of URLs for the letter

    """
    statement = (
        select(func.count()).select_from(EntryURLs).where(EntryURLs.letter == letter)
    )
    return session.exec(statement).one()


def delete_all_entry_urls(session: Session) -> int:
    """Delete all URL entries.

    Parameters
    ----------
    session : Session
        Database session

    Returns
    -------
    int
        Number of entries deleted

    """
    statement = select(EntryURLs)
    entries = session.exec(statement).all()
    count = 0
    for entry in entries:
        session.delete(entry)
        count += 1
    session.commit()
    return count


def delete_entry_urls_by_letter(session: Session, letter: str) -> int:
    """Delete all URL entries for a specific letter.

    Parameters
    ----------
    session : Session
        Database session
    letter : str
        Letter to filter by

    Returns
    -------
    int
        Number of entries deleted

    """
    statement = select(EntryURLs).where(EntryURLs.letter == letter)
    entries = session.exec(statement).all()
    count = 0
    for entry in entries:
        session.delete(entry)
        count += 1
    session.commit()
    return count
