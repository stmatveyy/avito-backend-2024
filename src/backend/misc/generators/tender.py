from sqlalchemy.orm import Session
from typing import Generator, Any
from model.models import Tender
from uuid import uuid4
from sqlalchemy import select


def gen_tender_id(session: Session) -> Generator[Any, Any, Any]:
    """
    Returns a `Generator` object to yeild a UUID4-like string for a Tender.
    Args:
        session:
            Current database session.

    Returns:
        `Generator` object.
    """

    while True:

        new_id = uuid4()
        check_query = select(Tender).where(Tender.id == str(new_id))
        result = session.execute(check_query)
        existing_tender = result.fetchone()

        if existing_tender is None:

            yield str(new_id)
