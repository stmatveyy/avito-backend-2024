from sqlalchemy.orm import Session
from fastapi import status as http_status
from fastapi.responses import JSONResponse
from model.models import Bid
from sqlalchemy import select
from .universal import _invalid_uuid4


def invalid_bid_version(session: Session,
                        ver: int,
                        bidId: str) -> None | JSONResponse:
    """
    Checks if **bid version** exists in a database.

    Args:
        session:
            Current database session. Must be of type `Session`.
        ver:
            Bid version to check against. Must be > 1.
        bidId:
            Bid id. Must be a valid UUID4-like string,
            without any * at the end.

    Returns:
        - `None` if given bid version exists.
        - `JSONResponce` (400) if given **bidId** not found
            or **id** is not UUID4 valid..
    """

    if ver < 1:
        return JSONResponse(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            content={"reason": "Invalid bid version (Must be above 1)"})

    response = invalid_bid_id(bidId=bidId,session=session)
    if response:
        response

    res = session.execute(select(Bid.version)
                          .filter(Bid.id.like(f"{bidId}"))
                          .where(Bid.version == ver))

    if not res.scalar_one_or_none():

        return JSONResponse(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            content={"reason": "No such bid version"})

    return None


def invalid_bid_id(session: Session,
                   bidId: str) -> None | JSONResponse:

    """
    Checks if **bidId** exists in a database and is a valid UUID4-like string.

    Args:
        session:
            Current database session. Must be of Session type
        bidId:
            Bid id. Must be a valid UUID4-like string, without any * at the end

    Returns:
        - `None` if given bidId exists.
        - `JSONResponce` (400) if given **bidId** not found
            or **id** is not UUID4 valid.
    """

    response = _invalid_uuid4(id=bidId)
    if response:

        return JSONResponse(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            content={"reason": "No such bid (Invalid UUID)"})

    res = session.execute(select(Bid.id)
                          .filter(Bid.id
                                  .like(f"{bidId}%"))
                                  .limit(1))

    if not res.scalars().all():

        return JSONResponse(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            content={"reason": "No such bid"})

    return None
