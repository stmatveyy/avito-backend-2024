from sqlalchemy.orm import Session
from ..getters import bid as bid_getters, user as user_getters
from ..checkers import bid as bid_checkers
from fastapi.responses import JSONResponse
from model.models import Bid, OrganizationResponsible
from sqlalchemy import select, func
from pyrfc3339 import generate
import datetime
import pytz
from ..getters import bid as get_bid
from typing import Any, List, Dict, Optional


def make_bid_copy(session: Session,
                  bidId: str) -> Bid | JSONResponse:
    """
    Creates a copy of bid with **bidId** as a new entity.\n
    A copy has:
    - New id, formed by adding a "*" at the end
    - New version, incremented by 1
    - New createdAt value, as a current datetime in RFC3339 format

    Args:
        session:
            Current database session.
        bidId:
            Bid id. Must be a valid UUID4-like string,
            without any * at the end.\n

    Returns:
        - `Bid` object, copy of a given bid if bid exists.
        - `JSONResponse` (400) if given **bidId** not found
            or **id** is not UUID4 valid..
    """

    response = bid_checkers.invalid_bid_id(session=session, bidId=bidId)
    if response:
        return response

    fresh_bid = bid_getters.get_last_version_bid(session=session, bidId=bidId)

    new_bid = Bid(
        id=f"{fresh_bid.id}*",
        name=fresh_bid.name,
        description=fresh_bid.description,
        status=fresh_bid.status,
        tenderId=fresh_bid.tenderId,
        authorType=fresh_bid.authorType,
        authorId=fresh_bid.authorId,
        version=fresh_bid.version + 1,
        createdAt=generate(datetime.datetime.now(datetime.UTC)
                                            .replace(tzinfo=pytz.utc))
    )

    session.add(new_bid)
    session.commit()
    session.refresh(new_bid)

    return new_bid


def format_bid(bid: Bid) -> dict[str, Any]:
    """
    Formats a `Bid` object to a following JSON format:
            **{ "id": authorId,\n
            "name": name,\n
            "status": status,\n
            "authorType": authorType,\n
            "authorId": authorId,\n
            "verstion": version,\n
            "createdAt": createdAt }**
    Args:
        bid:
            `Bid` object to format

    Returns:
        JSON-like object.
    """

    return {"id": bid.id,
            "name": bid.name,
            "status": bid.status,
            "authorType": bid.authorType,
            "authorId": bid.authorId,
            "verstion": bid.version,
            "createdAt": bid.createdAt}


def only_fresh(limit: int,
               offset: int,
               session: Session,
               where_statement=Optional[bool]) -> List[Dict[str, Any]]:
    """Returns a list of last version JSON-like formatted Bids,
    that follow **where_statement**.

    Args:
        where_statement (Optional): Where-statement of type `bool`
        session: Database session.
        limit: Limit.
        offset: Offset.
    Returns:
        List of JSON-like bids.
    """
    query = select(Bid.id)

    query = (query
             .where(where_statement)
             .limit(limit)
             .offset(offset)
             .order_by(Bid.name))

    res = session.execute(query)
    bid_ids = res.scalars().all()

    stripped_bid_ids = [id[:36] for id in bid_ids]
    unique_bid_ids = set(stripped_bid_ids)

    return [format_bid(
            get_bid.get_last_version_bid(bidId=id,
                                         session=session))
            for id in unique_bid_ids]


def count_quorum(username: str,
                 session: Session) -> int:
    user_id = user_getters.get_user_id(username=username, session=session)

    res = session.execute(select(func.count(OrganizationResponsible.id))
                          .where(OrganizationResponsible.user_id == user_id)
                          .limit(3))
    return res.scalar()
