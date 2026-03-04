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
    ParsedVocabolsUpdate,
    VocabolsHtmlChanges,
    VocabolsHtmlChangesCreate,
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


def get_parsed_vocabol_by_id(
    session: Session, id: UUID
) -> Optional[ParsedVocabols]:
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


def find_parsed_vocabol_by_url(
    session: Session, url: str
) -> Optional[ParsedVocabols]:
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
        .where(VocabolsRawHTML.entry_url_id.notin_(parsed_ids_subquery))
        .where(VocabolsRawHTML.raw_html.isnot(None))  # Only entries with HTML
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
        .where(VocabolsRawHTML.entry_url_id.notin_(parsed_ids_subquery))
        .where(VocabolsRawHTML.raw_html.isnot(None))
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
        .where(VocabolsRawHTML.entry_url_id.notin_(parsed_ids_subquery))
        .where(VocabolsRawHTML.raw_html.isnot(None))
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
