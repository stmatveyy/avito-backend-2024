from sqlalchemy.orm import Session
from model.models import Bid
from sqlalchemy import select
from fastapi.responses import JSONResponse

from ..checkers import bid as bid_checkers


def get_last_version_bid(session: Session,
                         bidId: str) -> Bid | JSONResponse:
    """
    Returns `Bid` object with the latest `Bid.version`

    Args:
        session:
            Current database session.
        bidId:
            Bid id. Must be a valid UUID4-like string,
            without any * at the end.\n

    Returns:
        - `Bid` object if bid exists.
        - `JSONResponse` (400) if given **bidId** not found
            or **id** is not UUID4 valid..
    """

    response = bid_checkers.invalid_bid_id(session=session, bidId=bidId)
    if response:
        return response

    res = session.execute(select(Bid)
                          .filter(Bid.id.match(f"{bidId}%"))
                          .order_by(Bid.version.desc()))

    return res.scalars().first()
