from sqlalchemy.orm import Session
from model.models import Tender
from sqlalchemy import select
from ..checkers import tender as tender_checkers


def get_last_version_tender(session: Session,
                            tenderId: str) -> Tender:
    """
    Returns `Tender` object with the latest `Tender.version`

    Args:
        session:
            Current database session.
        tenderId:
            Tender id. Must be a valid UUID, without any * at the end.\n

    Returns:
        - `Tender` object if tender exists.
        - `JSONResponse` (400) if given if given **tenderId** not found
            or **tenderId** is not UUID4 valid.
    """

    response = tender_checkers.invalid_tender_id(session=session,
                                                 tenderId=tenderId)
    if response:
        return response

    res = session.execute(select(Tender)
                          .filter(Tender.id.match(f"{tenderId}%"))
                          .order_by(Tender.version.desc()))

    return res.scalars().first()
