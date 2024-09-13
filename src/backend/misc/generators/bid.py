from sqlalchemy.orm import Session
from typing import Generator, Any
from model.models import Bid
from sqlalchemy import select
from uuid import uuid4


def gen_bid_id(session: Session) -> Generator[Any, Any, Any]:
    """
    Returns a `Generator` object to yeild a UUID4-like string for a Bid.
    Args:
        session:
            Current database session.

    Returns:
        `Generator` object.
    """
    while True:

        new_id = uuid4()
        check_query = select(Bid).where(Bid.id == str(new_id))
        result = session.execute(check_query)
        existing_bid = result.fetchone()

        if existing_bid is None:

            yield str(new_id)
