from sqlalchemy.orm import Session
from fastapi import status as http_status
from fastapi.responses import JSONResponse
from model.models import Tender
from sqlalchemy import select
from .universal import _invalid_uuid4


def invalid_tender_version(session: Session,
                           ver: int,
                           tenderId: str) -> None | JSONResponse:
    """
    Checks if **tender version** exists in a database.

    Args:
        session:
            Current database session. Must be of type `Session`
        ver:
            Tender version to check against
        tenderId:
            Tender id. Must be a valid UUID4-like string,
            without any * at the end

    Returns:
        - `None` if given tender version exists.
        - `JSONResponce` (404) if given **tenderId** not found
            or UUID is invalid.
    """

    if ver < 1:
        return JSONResponse(
            status_code=http_status.HTTP_404_NOT_FOUND,
            content={"reason": "Invalid tender version (Must be above 1)"})

    res = session.execute(select(Tender.version)
                          .filter(Tender.id.like(f"{tenderId}%"))
                          .where(Tender.version == ver))

    if not res.scalar_one_or_none():
        return JSONResponse(
            status_code=http_status.HTTP_404_NOT_FOUND,
            content={"reason": "No such tender version"})

    return None


def invalid_tender_id(session: Session,
                      tenderId: str) -> None | JSONResponse:
    """
    Checks if **tenderId** exists in a database.

    Args:
        session:
            Current database session. Must be of type `Session`
        tenderId:
            Tender id. Must be a valid UUID4-like string,
            without any * at the end

    Returns:
        - `None` if given tenderId exists.
        - `JSONResponce` (404) if given **tenderId** not found
            or **tenderId** is not UUID4 valid.
    """

    response = _invalid_uuid4(id=tenderId)
    if response:
        return JSONResponse(
            status_code=http_status.HTTP_404_NOT_FOUND,
            content={"reason": "No such tender (Invalid UUID)"})

    res = session.execute(select(Tender.id)
                          .filter(Tender.id.like(f"{tenderId}%")))

    if len(res.scalars().all()) == 0:
        return JSONResponse(
            status_code=http_status.HTTP_404_NOT_FOUND,
            content={"reason": "No such tender"})

    return None
