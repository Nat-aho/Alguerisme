"""CRUD operations for EntryURLs."""

from typing import Optional
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, select

from alguerisme.utils.alphabet import normalize_letter

from .models import (
    EntryURLs,
    EntryURLsCreate,
    EntryURLsUpdate,
    ParsedVocabols,
    ParsedVocabolsCreate,
    ParsedVocabolsLetterStats,
    ParsedVocabolsOverallStats,
    VocabolsHtmlChanges,
    VocabolsHtmlChangesCreate,
    VocabolsImages,
    VocabolsImagesCreate,
    VocabolsImagesUpdate,
    VocabolsRawHTML,
    VocabolsRawHTMLCreate,
    VocabolsRawHTMLUpdate,
)


def create_entry_url(session: Session, entry_create: EntryURLsCreate) -> EntryURLs:
    """Create a new URL entry and commit.

    Parameters
    ----------
    session : Session
        Database session
    entry_create : EntryURLsCreate
        Data for creating the entry

    Returns
    -------
    EntryURLs
        The created EntryURLs instance

    """
    entry = EntryURLs.model_validate(entry_create)
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def add_entry_url_to_session(
    session: Session, entry_create: EntryURLsCreate
) -> EntryURLs:
    """Add a new URL entry to session without committing.

    Parameters
    ----------
    session : Session
        Database session
    entry_create : EntryURLsCreate
        Data for creating the entry

    Returns
    -------
    EntryURLs
        The created EntryURLs instance (ID will be None until commit)

    """
    entry = EntryURLs.model_validate(entry_create)
    session.add(entry)
    return entry


def get_or_create_entry_url(
    session: Session, url: str, letter: Optional[str] = None
) -> tuple[EntryURLs, bool]:
    """Get existing URL entry or create and commit new one.

    Parameters
    ----------
    session : Session
        Database session
    url : str
        The URL to get or create
    letter : Optional[str]
        Optional letter (used only if creating). Will be normalized to uppercase.

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
    if not normalized_letter:
        raise ValueError("Letter is required when creating a new EntryURLs")
    entry_create = EntryURLsCreate(url=url, letter=normalized_letter)
    entry = create_entry_url(session, entry_create)
    return entry, True


def get_or_add_entry_url_to_session(
    session: Session, url: str, letter: Optional[str] = None
) -> tuple[EntryURLs, bool]:
    """Get existing URL entry or add new one to session without committing.

    Parameters
    ----------
    session : Session
        Database session
    url : str
        The URL to get or create
    letter : Optional[str]
        Optional letter (used only if creating). Will be normalized to uppercase.

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
    if not normalized_letter:
        raise ValueError("Letter is required when creating a new EntryURLs")
    entry_create = EntryURLsCreate(url=url, letter=normalized_letter)
    entry = add_entry_url_to_session(session, entry_create)
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
        Letter to count (will be normalized to uppercase)

    Returns
    -------
    int
        Number of URLs for the letter

    """
    normalized_letter = normalize_letter(letter)
    statement = (
        select(func.count())
        .select_from(EntryURLs)
        .where(EntryURLs.letter == normalized_letter)
    )
    return session.exec(statement).one()


def delete_all_entry_urls(session: Session) -> int:
    """Delete all URL entries using efficient set-based delete.

    Parameters
    ----------
    session : Session
        Database session

    Returns
    -------
    int
        Number of entries deleted

    """
    from sqlalchemy import delete as sql_delete

    statement = sql_delete(EntryURLs)
    result = session.exec(statement)
    session.commit()
    return result.rowcount


def delete_entry_urls_by_letter(session: Session, letter: str) -> int:
    """Delete all URL entries for a specific letter using efficient set-based delete.

    Parameters
    ----------
    session : Session
        Database session
    letter : str
        Letter to filter by (will be normalized to uppercase)

    Returns
    -------
    int
        Number of entries deleted

    """
    from sqlalchemy import delete as sql_delete

    normalized_letter = normalize_letter(letter)
    statement = sql_delete(EntryURLs).where(EntryURLs.letter == normalized_letter)  # type: ignore[arg-type]
    result = session.exec(statement)
    session.commit()
    return result.rowcount


def create_vocabols_raw_html(
    session: Session, html_create: VocabolsRawHTMLCreate
) -> VocabolsRawHTML:
    """Create a new VocabolsRawHTML entry and commit.

    Parameters
    ----------
    session : Session
        Database session
    html_create : VocabolsRawHTMLCreate
        Data for creating the entry

    Returns
    -------
    VocabolsRawHTML
        The created VocabolsRawHTML instance

    """
    html_entry = VocabolsRawHTML.model_validate(html_create)
    session.add(html_entry)
    session.commit()
    session.refresh(html_entry)
    return html_entry


def add_vocabols_raw_html_to_session(
    session: Session, html_create: VocabolsRawHTMLCreate
) -> VocabolsRawHTML:
    """Add a new VocabolsRawHTML entry to session without committing.

    Parameters
    ----------
    session : Session
        Database session
    html_create : VocabolsRawHTMLCreate
        Data for creating the entry

    Returns
    -------
    VocabolsRawHTML
        The created VocabolsRawHTML instance (ID will be None until commit)

    """
    html_entry = VocabolsRawHTML.model_validate(html_create)
    session.add(html_entry)
    return html_entry


def find_vocabols_raw_html_by_id(
    session: Session, html_id: UUID
) -> Optional[VocabolsRawHTML]:
    """Find a VocabolsRawHTML entry by its ID.

    Parameters
    ----------
    session : Session
        Database session
    html_id : UUID
        ID of the VocabolsRawHTML entry

    Returns
    -------
    Optional[VocabolsRawHTML]
        The VocabolsRawHTML instance if found, None otherwise

    """
    statement = select(VocabolsRawHTML).where(VocabolsRawHTML.id == html_id)
    return session.exec(statement).first()


def find_vocabols_raw_html_by_entry_url_id(
    session: Session, entry_url_id: UUID
) -> Optional[VocabolsRawHTML]:
    """Find a VocabolsRawHTML entry by entry_url_id.

    Parameters
    ----------
    session : Session
        Database session
    entry_url_id : UUID
        Foreign key to entry_urls table

    Returns
    -------
    Optional[VocabolsRawHTML]
        The VocabolsRawHTML instance if found, None otherwise

    """
    statement = select(VocabolsRawHTML).where(
        VocabolsRawHTML.entry_url_id == entry_url_id
    )
    return session.exec(statement).first()


def find_vocabols_raw_html_by_url(
    session: Session, url: str
) -> Optional[VocabolsRawHTML]:
    """Find a VocabolsRawHTML entry by URL.

    Parameters
    ----------
    session : Session
        Database session
    url : str
        URL to search for

    Returns
    -------
    Optional[VocabolsRawHTML]
        The VocabolsRawHTML instance if found, None otherwise

    """
    statement = select(VocabolsRawHTML).where(VocabolsRawHTML.url == url)
    return session.exec(statement).first()


def update_vocabols_raw_html(
    session: Session, html_id: UUID, html_update: VocabolsRawHTMLUpdate
) -> VocabolsRawHTML:
    """Update a VocabolsRawHTML entry.

    Parameters
    ----------
    session : Session
        Database session
    html_id : UUID
        ID of the entry to update
    html_update : VocabolsRawHTMLUpdate
        Update data

    Returns
    -------
    VocabolsRawHTML
        The updated VocabolsRawHTML instance

    Raises
    ------
    ValueError
        If the entry is not found

    """
    html_entry = find_vocabols_raw_html_by_id(session, html_id)
    if not html_entry:
        raise ValueError(f"VocabolsRawHTML with id {html_id} not found")

    update_data = html_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(html_entry, key, value)

    session.add(html_entry)
    session.commit()
    session.refresh(html_entry)
    return html_entry


def delete_vocabols_raw_html_by_id(session: Session, html_id: UUID) -> bool:
    """Delete a VocabolsRawHTML entry by ID.

    Parameters
    ----------
    session : Session
        Database session
    html_id : UUID
        ID of the entry to delete

    Returns
    -------
    bool
        True if entry was deleted, False if not found

    """
    html_entry = find_vocabols_raw_html_by_id(session, html_id)
    if not html_entry:
        return False

    session.delete(html_entry)
    session.commit()
    return True


def delete_vocabols_raw_html_by_letter(session: Session, letter: str) -> int:
    """Delete all VocabolsRawHTML entries for a specific letter.

    Parameters
    ----------
    session : Session
        Database session
    letter : str
        Letter to filter by (single character)

    Returns
    -------
    int
        Number of entries deleted

    """
    statement = select(VocabolsRawHTML).where(VocabolsRawHTML.letter == letter.upper())
    entries = list(session.exec(statement).all())

    count = len(entries)
    for entry in entries:
        session.delete(entry)

    session.commit()
    return count


def count_all_vocabols_raw_html(session: Session) -> int:
    """Count total number of VocabolsRawHTML entries.

    Parameters
    ----------
    session : Session
        Database session

    Returns
    -------
    int
        Total count of entries

    """
    statement = select(func.count()).select_from(VocabolsRawHTML)
    return session.exec(statement).one()


def count_vocabols_raw_html_by_letter(session: Session, letter: str) -> int:
    """Count VocabolsRawHTML entries for a specific letter.

    Parameters
    ----------
    session : Session
        Database session
    letter : str
        Letter to filter by (single character)

    Returns
    -------
    int
        Count of entries for the letter

    """
    statement = (
        select(func.count())
        .select_from(VocabolsRawHTML)
        .where(VocabolsRawHTML.letter == letter.upper())
    )
    return session.exec(statement).one()


def get_vocabols_raw_html_paginated(
    session: Session,
    limit: int = 50,
    offset: int = 0,
    letter: Optional[str] = None,
) -> list[VocabolsRawHTML]:
    """Get paginated list of VocabolsRawHTML entries, optionally filtered by letter.

    Parameters
    ----------
    session : Session
        Database session
    limit : int
        Maximum number of entries to return
    offset : int
        Number of entries to skip
    letter : Optional[str]
        Letter to filter by (single character)

    Returns
    -------
    list[VocabolsRawHTML]
        List of VocabolsRawHTML entries

    """
    statement = select(VocabolsRawHTML).order_by(VocabolsRawHTML.collected_at.desc())  # type: ignore[attr-defined]

    if letter:
        statement = statement.where(VocabolsRawHTML.letter == letter.upper())

    statement = statement.limit(limit).offset(offset)
    return list(session.exec(statement).all())


def list_unparsed_vocabols_raw_html(
    session: Session, letters: Optional[list[str]] = None
) -> list[VocabolsRawHTML]:
    """List raw HTML entries that need (re)parsing.

    Returns entries that either:
    1. Haven't been parsed yet (no entry in ParsedVocabols), OR
    2. Have been updated since last parsing (last_updated_at > parsed_at)

    This ensures HTML changes trigger re-parsing to keep parsed data in sync.

    Parameters
    ----------
    session : Session
        Database session
    letters : Optional[list[str]]
        List of letters to filter by (e.g., ["A", "B", "NY"])
        If None, returns unparsed entries for all letters

    Returns
    -------
    list[VocabolsRawHTML]
        List of raw HTML entries that need parsing

    """
    from sqlalchemy import or_

    # Strategy: LEFT JOIN to find entries that are either:
    # 1. Not parsed (ParsedVocabols is NULL), OR
    # 2. HTML updated after parsing (last_updated_at > parsed_at)
    statement = (
        select(VocabolsRawHTML)
        .outerjoin(
            ParsedVocabols,
            VocabolsRawHTML.entry_url_id == ParsedVocabols.entry_url_id,  # type: ignore[arg-type]
        )
        .where(VocabolsRawHTML.raw_html.isnot(None))  # type: ignore[attr-defined] # Must have HTML content
        .where(
            or_(
                ParsedVocabols.entry_url_id.is_(None),  # type: ignore[attr-defined] # Not yet parsed
                VocabolsRawHTML.last_updated_at > ParsedVocabols.parsed_at,  # type: ignore[arg-type] # Updated
            )
        )
    )

    # Optionally filter by letters
    if letters:
        normalized = [letter.upper() for letter in letters]
        statement = statement.where(VocabolsRawHTML.letter.in_(normalized))  # type: ignore[attr-defined]

    return list(session.exec(statement).all())


def list_pending_vocabols_urls(
    session: Session, limit: Optional[int] = None
) -> list[EntryURLs]:
    """List entry URLs that haven't been collected yet.

    Note: Assumes all URLs in entry_urls table are already filtered
    by the crawler to be vocabols URLs.

    Parameters
    ----------
    session : Session
        Database session
    limit : Optional[int]
        Maximum number of URLs to return

    Returns
    -------
    list[EntryURLs]
        List of entry URLs that need collection

    """
    subquery = select(VocabolsRawHTML.entry_url_id)
    statement = select(EntryURLs).where(EntryURLs.id.notin_(subquery))  # type: ignore[attr-defined]

    if limit:
        statement = statement.limit(limit)

    return list(session.exec(statement).all())


# ============================================================================
# VocabolsHtmlChanges CRUD Operations
# ============================================================================


def create_vocabols_html_change(
    session: Session, change_create: VocabolsHtmlChangesCreate
) -> VocabolsHtmlChanges:
    """Create a new VocabolsHtmlChanges entry and commit.

    Parameters
    ----------
    session : Session
        Database session
    change_create : VocabolsHtmlChangesCreate
        Data for creating the change record

    Returns
    -------
    VocabolsHtmlChanges
        The created VocabolsHtmlChanges instance

    """
    change = VocabolsHtmlChanges.model_validate(change_create)
    session.add(change)
    session.commit()
    session.refresh(change)
    return change


def find_pending_change_by_entry_url_id(
    session: Session, entry_url_id: UUID
) -> Optional[VocabolsHtmlChanges]:
    """Find a pending change for a specific entry_url_id.

    Parameters
    ----------
    session : Session
        Database session
    entry_url_id : UUID
        Entry URL ID to search for

    Returns
    -------
    Optional[VocabolsHtmlChanges]
        Pending change if found, None otherwise

    """
    from alguerisme.core.collector.enums import ChangeStatus

    statement = select(VocabolsHtmlChanges).where(
        VocabolsHtmlChanges.entry_url_id == entry_url_id,
        VocabolsHtmlChanges.status == ChangeStatus.PENDING,
    )
    return session.exec(statement).first()


def find_approved_change_by_entry_url_id(
    session: Session, entry_url_id: UUID
) -> Optional[VocabolsHtmlChanges]:
    """Find an approved change by entry_url_id.

    Parameters
    ----------
    session : Session
        Database session
    entry_url_id : UUID
        Entry URL ID to search for

    Returns
    -------
    Optional[VocabolsHtmlChanges]
        Approved change if found, None otherwise

    """
    from alguerisme.core.collector.enums import ChangeStatus

    statement = select(VocabolsHtmlChanges).where(
        VocabolsHtmlChanges.entry_url_id == entry_url_id,
        VocabolsHtmlChanges.status == ChangeStatus.APPROVED,
    )
    return session.exec(statement).first()


def find_rejected_change_by_entry_url_id(
    session: Session, entry_url_id: UUID
) -> Optional[VocabolsHtmlChanges]:
    """Find a rejected change by entry_url_id.

    Parameters
    ----------
    session : Session
        Database session
    entry_url_id : UUID
        Entry URL ID to search for

    Returns
    -------
    Optional[VocabolsHtmlChanges]
        Rejected change if found, None otherwise

    """
    from alguerisme.core.collector.enums import ChangeStatus

    statement = select(VocabolsHtmlChanges).where(
        VocabolsHtmlChanges.entry_url_id == entry_url_id,
        VocabolsHtmlChanges.status == ChangeStatus.REJECTED,
    )
    return session.exec(statement).first()


def list_changes_by_status(
    session: Session, status: str, limit: Optional[int] = None
) -> list[VocabolsHtmlChanges]:
    """List changes by status.

    Parameters
    ----------
    session : Session
        Database session
    status : str
        Status to filter by (ChangeStatus enum value)
    limit : Optional[int]
        Maximum number of changes to return

    Returns
    -------
    list[VocabolsHtmlChanges]
        List of changes with the specified status

    """
    statement = select(VocabolsHtmlChanges).where(VocabolsHtmlChanges.status == status)

    if limit:
        statement = statement.limit(limit)

    return list(session.exec(statement).all())


def get_change_by_id(
    session: Session, change_id: UUID
) -> Optional[VocabolsHtmlChanges]:
    """Get a change by ID.

    Parameters
    ----------
    session : Session
        Database session
    change_id : UUID
        Change ID

    Returns
    -------
    Optional[VocabolsHtmlChanges]
        Change if found, None otherwise

    """
    return session.get(VocabolsHtmlChanges, change_id)


def approve_change(
    session: Session, change_id: UUID, reviewed_by: str = "cli"
) -> Optional[VocabolsHtmlChanges]:
    """Approve a pending change.

    Parameters
    ----------
    session : Session
        Database session
    change_id : UUID
        Change ID to approve
    reviewed_by : str
        Who approved the change

    Returns
    -------
    Optional[VocabolsHtmlChanges]
        Approved change if found, None otherwise

    """
    from datetime import datetime, timezone

    from alguerisme.core.collector.enums import ChangeStatus

    change = session.get(VocabolsHtmlChanges, change_id)
    if not change:
        return None

    change.status = ChangeStatus.APPROVED
    change.reviewed_at = datetime.now(timezone.utc)
    change.reviewed_by = reviewed_by

    session.commit()
    session.refresh(change)
    return change


def reject_change(
    session: Session, change_id: UUID, reviewed_by: str = "cli"
) -> Optional[VocabolsHtmlChanges]:
    """Reject a pending change.

    Parameters
    ----------
    session : Session
        Database session
    change_id : UUID
        Change ID to reject
    reviewed_by : str
        Who rejected the change

    Returns
    -------
    Optional[VocabolsHtmlChanges]
        Rejected change if found, None otherwise

    """
    from datetime import datetime, timezone

    from alguerisme.core.collector.enums import ChangeStatus

    change = session.get(VocabolsHtmlChanges, change_id)
    if not change:
        return None

    change.status = ChangeStatus.REJECTED
    change.reviewed_at = datetime.now(timezone.utc)
    change.reviewed_by = reviewed_by

    session.commit()
    session.refresh(change)
    return change


def delete_change_by_id(session: Session, change_id: UUID) -> bool:
    """Delete a change by ID.

    Parameters
    ----------
    session : Session
        Database session
    change_id : UUID
        Change ID to delete

    Returns
    -------
    bool
        True if deleted, False if not found

    """
    change = session.get(VocabolsHtmlChanges, change_id)
    if not change:
        return False

    session.delete(change)
    session.commit()
    return True


def count_changes_by_status(session: Session, status: str) -> int:
    """Count changes by status.

    Parameters
    ----------
    session : Session
        Database session
    status : str
        Status to count

    Returns
    -------
    int
        Number of changes with the specified status

    """
    statement = (
        select(func.count())
        .select_from(VocabolsHtmlChanges)
        .where(VocabolsHtmlChanges.status == status)
    )
    return session.exec(statement).one()


def update_pending_change(
    session: Session, change: VocabolsHtmlChanges
) -> VocabolsHtmlChanges:
    """Update a pending change record (for when re-collection finds new change).

    Parameters
    ----------
    session : Session
        Database session
    change : VocabolsHtmlChanges
        Change record to update

    Returns
    -------
    VocabolsHtmlChanges
        Updated change record

    """
    from datetime import datetime, timezone

    change.detected_at = datetime.now(timezone.utc)
    session.add(change)
    session.commit()
    session.refresh(change)
    return change


# ============================================================================
# ParsedVocabols CRUD Operations
# ============================================================================


def create_parsed_vocabol(
    session: Session, parsed_create: ParsedVocabolsCreate
) -> ParsedVocabols:
    """Create a new parsed vocabol entry and commit.

    Parameters
    ----------
    session : Session
        Database session
    parsed_create : ParsedVocabolsCreate
        Data for creating the parsed entry

    Returns
    -------
    ParsedVocabols
        The created ParsedVocabols instance

    """
    parsed = ParsedVocabols.model_validate(parsed_create)
    session.add(parsed)
    session.commit()
    session.refresh(parsed)
    return parsed


def add_parsed_vocabol_to_session(
    session: Session, parsed_create: ParsedVocabolsCreate
) -> ParsedVocabols:
    """Add a new parsed vocabol to session without committing.

    Parameters
    ----------
    session : Session
        Database session
    parsed_create : ParsedVocabolsCreate
        Data for creating the parsed entry

    Returns
    -------
    ParsedVocabols
        The created ParsedVocabols instance (not yet committed)

    """
    parsed = ParsedVocabols.model_validate(parsed_create)
    session.add(parsed)
    return parsed


def upsert_parsed_vocabol_to_session(
    session: Session, parsed_create: ParsedVocabolsCreate
) -> tuple[ParsedVocabols, bool]:
    """Insert or update a parsed vocabol in session without committing.

    If an entry exists for this entry_url_id, updates it.
    Otherwise, creates a new entry.

    This enables re-parsing when HTML is updated.

    Parameters
    ----------
    session : Session
        Database session
    parsed_create : ParsedVocabolsCreate
        Data for creating/updating the parsed entry

    Returns
    -------
    tuple[ParsedVocabols, bool]
        Tuple of (ParsedVocabols instance, was_created)
        was_created is True if new entry, False if updated existing

    """
    from datetime import datetime, timezone

    # Check if entry already exists
    existing = get_parsed_vocabol_by_entry_url_id(session, parsed_create.entry_url_id)

    if existing:
        # Update existing entry
        existing.raw_html_id = parsed_create.raw_html_id
        existing.url = parsed_create.url
        existing.algueres_word = parsed_create.algueres_word
        existing.algueres_definition = parsed_create.algueres_definition
        existing.catalan_word = parsed_create.catalan_word
        existing.catalan_definition = parsed_create.catalan_definition
        existing.italian_word = parsed_create.italian_word
        existing.italian_definition = parsed_create.italian_definition
        existing.image_urls = parsed_create.image_urls
        existing.audio_urls = parsed_create.audio_urls
        existing.image_url_count = parsed_create.image_url_count
        existing.audio_url_count = parsed_create.audio_url_count
        existing.parsing_errors = parsed_create.parsing_errors
        existing.parsed_at = datetime.now(timezone.utc)  # Update timestamp

        session.add(existing)
        return existing, False
    else:
        # Create new entry
        parsed = ParsedVocabols.model_validate(parsed_create)
        session.add(parsed)
        return parsed, True


def get_parsed_vocabol_by_id(session: Session, id: UUID) -> Optional[ParsedVocabols]:
    """Get parsed vocabol by ID.

    Parameters
    ----------
    session : Session
        Database session
    id : UUID
        Parsed entry UUID

    Returns
    -------
    Optional[ParsedVocabols]
        ParsedVocabols if found, None otherwise

    """
    return session.get(ParsedVocabols, id)


def get_parsed_vocabol_by_entry_url_id(
    session: Session, entry_url_id: UUID
) -> Optional[ParsedVocabols]:
    """Get parsed vocabol by entry_url_id.

    Parameters
    ----------
    session : Session
        Database session
    entry_url_id : UUID
        Entry URL UUID

    Returns
    -------
    Optional[ParsedVocabols]
        ParsedVocabols if found, None otherwise

    """
    statement = select(ParsedVocabols).where(
        ParsedVocabols.entry_url_id == entry_url_id
    )
    return session.exec(statement).first()


def find_parsed_vocabol_by_url(session: Session, url: str) -> Optional[ParsedVocabols]:
    """Find parsed vocabol by URL.

    Parameters
    ----------
    session : Session
        Database session
    url : str
        URL to search for

    Returns
    -------
    Optional[ParsedVocabols]
        ParsedVocabols if found, None otherwise

    """
    statement = select(ParsedVocabols).where(ParsedVocabols.url == url)
    return session.exec(statement).first()


def get_unparsed_vocabols(
    session: Session, limit: Optional[int] = None
) -> list[VocabolsRawHTML]:
    """Get raw HTML entries that haven't been parsed yet.

    Parameters
    ----------
    session : Session
        Database session
    limit : Optional[int]
        Maximum number of entries to return

    Returns
    -------
    list[VocabolsRawHTML]
        List of unparsed raw HTML entries

    """
    # Subquery to get entry_url_ids that have been parsed
    parsed_ids_subquery = select(ParsedVocabols.entry_url_id)

    # Main query: get raw HTML where entry_url_id NOT IN parsed_ids
    statement = (
        select(VocabolsRawHTML)
        .where(VocabolsRawHTML.entry_url_id.notin_(parsed_ids_subquery))  # type: ignore[attr-defined]
        .where(VocabolsRawHTML.raw_html.isnot(None))  # type: ignore[attr-defined]  # Only entries with HTML
        .where(VocabolsRawHTML.http_status_code == 200)  # Only successful fetches
    )

    if limit:
        statement = statement.limit(limit)

    return list(session.exec(statement).all())


def get_unparsed_vocabols_by_letter(
    session: Session, letter: str, limit: Optional[int] = None
) -> list[VocabolsRawHTML]:
    """Get unparsed raw HTML entries for a specific letter.

    Parameters
    ----------
    session : Session
        Database session
    letter : str
        Letter to filter by
    limit : Optional[int]
        Maximum number of entries to return

    Returns
    -------
    list[VocabolsRawHTML]
        List of unparsed raw HTML entries for the letter

    """
    normalized_letter = normalize_letter(letter)

    # Subquery to get entry_url_ids that have been parsed
    parsed_ids_subquery = select(ParsedVocabols.entry_url_id)

    # Main query with letter filter
    statement = (
        select(VocabolsRawHTML)
        .where(VocabolsRawHTML.letter == normalized_letter)
        .where(VocabolsRawHTML.entry_url_id.notin_(parsed_ids_subquery))  # type: ignore[attr-defined]
        .where(VocabolsRawHTML.raw_html.isnot(None))  # type: ignore[attr-defined]
        .where(VocabolsRawHTML.http_status_code == 200)
    )

    if limit:
        statement = statement.limit(limit)

    return list(session.exec(statement).all())


def count_unparsed_vocabols(session: Session) -> int:
    """Count total unparsed vocabols.

    Parameters
    ----------
    session : Session
        Database session

    Returns
    -------
    int
        Count of unparsed entries

    """
    parsed_ids_subquery = select(ParsedVocabols.entry_url_id)

    statement = (
        select(func.count())
        .select_from(VocabolsRawHTML)
        .where(VocabolsRawHTML.entry_url_id.notin_(parsed_ids_subquery))  # type: ignore[attr-defined]
        .where(VocabolsRawHTML.raw_html.isnot(None))  # type: ignore[attr-defined]
        .where(VocabolsRawHTML.http_status_code == 200)
    )

    return session.exec(statement).one()


def count_parsed_vocabols(session: Session) -> int:
    """Count total parsed vocabols.

    Parameters
    ----------
    session : Session
        Database session

    Returns
    -------
    int
        Count of parsed entries

    """
    statement = select(func.count()).select_from(ParsedVocabols)
    return session.exec(statement).one()


def get_parsed_vocabols_list(
    session: Session,
    limit: int = 50,
    letters: Optional[list[str]] = None,
    with_images: Optional[bool] = None,
    with_audio: Optional[bool] = None,
) -> list[ParsedVocabols]:
    """Get list of parsed vocabols with optional filters.

    Parameters
    ----------
    session : Session
        Database session
    limit : int
        Maximum number of results to return
    letters : Optional[list[str]]
        Letters to filter by (e.g., ['A', 'B', 'C']). Uses all if None.
    with_images : Optional[bool]
        Filter by presence of images (True=with, False=without, None=no filter)
    with_audio : Optional[bool]
        Filter by presence of audio (True=with, False=without, None=no filter)

    Returns
    -------
    list[ParsedVocabols]
        List of parsed vocabols matching the filters

    """
    statement = select(ParsedVocabols)

    # Filter by letters if provided
    if letters:
        # Get entry_url_ids for these letters
        entry_url_ids = []
        for letter in letters:
            normalized = normalize_letter(letter)
            entry_urls = get_entry_urls_by_letter(session, normalized)
            entry_url_ids.extend([eu.id for eu in entry_urls])

        if entry_url_ids:
            statement = statement.where(
                ParsedVocabols.entry_url_id.in_(entry_url_ids)  # type: ignore[attr-defined]
            )

    # Filter by images
    if with_images is not None:
        if with_images:
            statement = statement.where(ParsedVocabols.image_url_count > 0)
        else:
            statement = statement.where(ParsedVocabols.image_url_count == 0)

    # Filter by audio
    if with_audio is not None:
        if with_audio:
            statement = statement.where(ParsedVocabols.audio_url_count > 0)
        else:
            statement = statement.where(ParsedVocabols.audio_url_count == 0)

    statement = statement.limit(limit)
    return list(session.exec(statement).all())


def get_parsed_vocabols_overall_stats(
    session: Session,
) -> ParsedVocabolsOverallStats:
    """Get overall statistics for all parsed vocabols.

    Parameters
    ----------
    session : Session
        Database session

    Returns
    -------
    ParsedVocabolsOverallStats
        Overall statistics model

    """
    total = count_parsed_vocabols(session)

    # Count entries with images
    with_images = session.exec(
        select(func.count())
        .select_from(ParsedVocabols)
        .where(ParsedVocabols.image_url_count > 0)
    ).one()

    # Count entries with audio
    with_audio = session.exec(
        select(func.count())
        .select_from(ParsedVocabols)
        .where(ParsedVocabols.audio_url_count > 0)
    ).one()

    # Sum of all images
    total_images = (
        session.exec(
            select(func.sum(ParsedVocabols.image_url_count)).select_from(ParsedVocabols)
        ).one()
        or 0
    )

    # Sum of all audio files
    total_audio = (
        session.exec(
            select(func.sum(ParsedVocabols.audio_url_count)).select_from(ParsedVocabols)
        ).one()
        or 0
    )

    # Count entries with errors
    with_errors = session.exec(
        select(func.count())
        .select_from(ParsedVocabols)
        .where(ParsedVocabols.parsing_errors.isnot(None))  # type: ignore[attr-defined]
    ).one()

    return ParsedVocabolsOverallStats(
        total=total,
        with_images=with_images,
        with_audio=with_audio,
        total_images=total_images,
        total_audio=total_audio,
        with_errors=with_errors,
    )


def get_parsed_vocabols_stats_by_letter(
    session: Session, letter: str
) -> ParsedVocabolsLetterStats:
    """Get statistics for parsed vocabols for a specific letter.

    Parameters
    ----------
    session : Session
        Database session
    letter : str
        Letter to get stats for (will be normalized)

    Returns
    -------
    ParsedVocabolsLetterStats
        Letter statistics model

    """
    normalized = normalize_letter(letter)

    # Get entry_url_ids for this letter
    entry_urls = get_entry_urls_by_letter(session, normalized)
    entry_url_ids = [eu.id for eu in entry_urls]

    if not entry_url_ids:
        return ParsedVocabolsLetterStats(
            letter=normalized,
            total=0,
            with_images=0,
            with_audio=0,
            avg_images=0.0,
            avg_audio=0.0,
        )

    # Count total parsed for this letter
    total = session.exec(
        select(func.count())
        .select_from(ParsedVocabols)
        .where(ParsedVocabols.entry_url_id.in_(entry_url_ids))  # type: ignore[attr-defined]
    ).one()

    # Count with images
    with_images = session.exec(
        select(func.count())
        .select_from(ParsedVocabols)
        .where(ParsedVocabols.entry_url_id.in_(entry_url_ids))  # type: ignore[attr-defined]
        .where(ParsedVocabols.image_url_count > 0)
    ).one()

    # Count with audio
    with_audio = session.exec(
        select(func.count())
        .select_from(ParsedVocabols)
        .where(ParsedVocabols.entry_url_id.in_(entry_url_ids))  # type: ignore[attr-defined]
        .where(ParsedVocabols.audio_url_count > 0)
    ).one()

    # Average images per entry
    avg_images = (
        session.exec(
            select(func.avg(ParsedVocabols.image_url_count))
            .select_from(ParsedVocabols)
            .where(ParsedVocabols.entry_url_id.in_(entry_url_ids))  # type: ignore[attr-defined]
        ).one()
        or 0.0
    )

    # Average audio per entry
    avg_audio = (
        session.exec(
            select(func.avg(ParsedVocabols.audio_url_count))
            .select_from(ParsedVocabols)
            .where(ParsedVocabols.entry_url_id.in_(entry_url_ids))  # type: ignore[attr-defined]
        ).one()
        or 0.0
    )

    return ParsedVocabolsLetterStats(
        letter=normalized,
        total=total,
        with_images=with_images,
        with_audio=with_audio,
        avg_images=float(avg_images),
        avg_audio=float(avg_audio),
    )


# ============================================================================
# VocabolsImages CRUD Operations
# ============================================================================


def create_vocabols_image(
    session: Session, image_create: VocabolsImagesCreate
) -> VocabolsImages:
    """Create a new vocabol image entry and commit.

    Parameters
    ----------
    session : Session
        Database session
    image_create : VocabolsImagesCreate
        Data for creating the image entry

    Returns
    -------
    VocabolsImages
        The created VocabolsImages instance

    """
    image = VocabolsImages.model_validate(image_create)
    session.add(image)
    session.commit()
    session.refresh(image)
    return image


def add_vocabols_image_to_session(
    session: Session, image_create: VocabolsImagesCreate
) -> VocabolsImages:
    """Add a new vocabol image entry to session without committing.

    Used by service layer for batch operations.

    Parameters
    ----------
    session : Session
        Database session
    image_create : VocabolsImagesCreate
        Data for creating the image entry

    Returns
    -------
    VocabolsImages
        The created VocabolsImages instance (ID will be None until commit)

    """
    image = VocabolsImages.model_validate(image_create)
    session.add(image)
    return image


def get_vocabols_image_by_parsed_id(
    session: Session, parsed_vocabol_id: UUID
) -> Optional[VocabolsImages]:
    """Get vocabol image by parsed vocabol ID.

    Parameters
    ----------
    session : Session
        Database session
    parsed_vocabol_id : UUID
        ID of the parsed vocabol

    Returns
    -------
    Optional[VocabolsImages]
        VocabolsImages instance if found, None otherwise

    """
    statement = select(VocabolsImages).where(
        VocabolsImages.parsed_vocabol_id == parsed_vocabol_id
    )
    return session.exec(statement).first()


def update_vocabols_image(
    session: Session,
    image_id: UUID,
    image_update: VocabolsImagesUpdate,
) -> Optional[VocabolsImages]:
    """Update an existing vocabol image entry.

    Parameters
    ----------
    session : Session
        Database session
    image_id : UUID
        ID of the image entry to update
    image_update : VocabolsImagesUpdate
        Data for updating the image entry

    Returns
    -------
    Optional[VocabolsImages]
        Updated VocabolsImages instance if found, None otherwise

    """
    image = session.get(VocabolsImages, image_id)
    if not image:
        return None

    update_data = image_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(image, key, value)

    session.add(image)
    session.commit()
    session.refresh(image)
    return image


def find_parsed_vocabols_without_images(session: Session) -> list[ParsedVocabols]:
    """Find all parsed vocabols that need image collection or re-collection.

    Returns parsed vocabols that:
    - Have at least one image_url in their JSONB array
    - Either don't have collected images, or their parsed_at is newer than
      the source_parsed_at of all collected images (indicating re-parsing)

    This timestamp-based approach enables automatic re-collection when
    vocabols are re-parsed due to HTML updates.

    Parameters
    ----------
    session : Session
        Database session

    Returns
    -------
    list[ParsedVocabols]
        List of parsed vocabols needing image collection

    """
    # Subquery: max source_parsed_at for each parsed_vocabol_id
    max_source_parsed_subquery = (
        select(
            VocabolsImages.parsed_vocabol_id,
            func.max(VocabolsImages.source_parsed_at).label("max_source_parsed_at"),
        )
        .group_by(VocabolsImages.parsed_vocabol_id)  # type: ignore[arg-type]
        .subquery()
    )

    statement = (
        select(ParsedVocabols)
        .outerjoin(
            max_source_parsed_subquery,
            ParsedVocabols.id == max_source_parsed_subquery.c.parsed_vocabol_id,  # type: ignore[arg-type]
        )
        .where(ParsedVocabols.image_url_count > 0)
        .where(
            (max_source_parsed_subquery.c.max_source_parsed_at.is_(None))
            | (
                ParsedVocabols.parsed_at
                > max_source_parsed_subquery.c.max_source_parsed_at
            )
        )
    )

    return list(session.exec(statement).all())


def count_vocabols_images(session: Session) -> int:
    """Count total vocabol images collected.

    Parameters
    ----------
    session : Session
        Database session

    Returns
    -------
    int
        Count of collected images

    """
    statement = select(func.count()).select_from(VocabolsImages)
    return session.exec(statement).one()


def get_vocabols_images_with_vocabol_info(
    session: Session,
    limit: int = 50,
    letter: Optional[str] = None,
    status: Optional[str] = None,
) -> list[tuple[VocabolsImages, Optional[str], str]]:
    """Get vocabols images with associated vocabol information.

    Parameters
    ----------
    session : Session
        Database session
    limit : int
        Maximum number of results to return
    letter : Optional[str]
        Filter by letter
    status : Optional[str]
        Filter by collection status

    Returns
    -------
    list[tuple[VocabolsImages, Optional[str], str]]
        List of tuples (image, algueres_word, url)

    """
    statement = select(
        VocabolsImages,
        ParsedVocabols.algueres_word,
        ParsedVocabols.url,
    ).join(
        ParsedVocabols,
        VocabolsImages.parsed_vocabol_id == ParsedVocabols.id,  # type: ignore[arg-type]
    )

    # Filter by letter if provided
    if letter:
        normalized_letter = normalize_letter(letter)
        entry_urls = get_entry_urls_by_letter(session, normalized_letter)
        entry_url_ids = [eu.id for eu in entry_urls]
        statement = statement.where(
            ParsedVocabols.entry_url_id.in_(entry_url_ids)  # type: ignore[attr-defined]
        )

    # Filter by status if provided
    if status:
        statement = statement.where(VocabolsImages.collection_status == status)

    statement = statement.limit(limit)
    return list(session.exec(statement).all())


def get_vocabols_image_with_vocabol_by_id(
    session: Session, image_id: UUID
) -> Optional[tuple[VocabolsImages, ParsedVocabols]]:
    """Get vocabols image with associated vocabol by image ID.

    Parameters
    ----------
    session : Session
        Database session
    image_id : UUID
        Image ID

    Returns
    -------
    Optional[tuple[VocabolsImages, ParsedVocabols]]
        Tuple of (image, vocabol) if found, None otherwise

    """
    statement = (
        select(VocabolsImages, ParsedVocabols)
        .join(
            ParsedVocabols,
            VocabolsImages.parsed_vocabol_id == ParsedVocabols.id,  # type: ignore[arg-type]
        )
        .where(VocabolsImages.id == image_id)
    )
    return session.exec(statement).first()
