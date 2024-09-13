from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from model.models import Tender
from pyrfc3339 import generate
import datetime
import pytz
from ..getters.tender import get_last_version_tender
from ..checkers import tender as tender_checkers
from typing import Any


def make_tender_copy(session: Session,
                     tenderId: str) -> Tender | JSONResponse:
    """
    Creates a copy of tender with **tenderId** as a new entity.\n
    A copy has:
    - New id, formed by adding a "*" at the end
    - New version, incremented by 1
    - New createdAt value, as a current datetime in RFC3339 format

    Args:
        session:
            Current database session.
        tenderId:
            Tender id. Must be a valid UUID4-like string,
            without any * at the end.\n

    Returns:
        - `Tender` object, copy of a given tender if tender exists.
        - `JSONResponse` (400) if given tenderId not found or UUID is invalid.
    """
    response = tender_checkers.invalid_tender_id(session=session,
                                                 tenderId=tenderId)
    if response:
        return response

    fresh_tender = get_last_version_tender(session=session, tenderId=tenderId)

    new_tender = Tender(
        id=f"{fresh_tender.id}*",
        name=fresh_tender.name,
        description=fresh_tender.description,
        serviceType=fresh_tender.serviceType,
        status=fresh_tender.status,
        organizationId=fresh_tender.organizationId,
        version=fresh_tender.version + 1,
        createdAt=generate(datetime.datetime.now(datetime.UTC)
                                            .replace(tzinfo=pytz.utc))
    )

    session.add(new_tender)
    session.commit()

    return new_tender


def format_tender(tender: Tender) -> dict[str, Any]:
    """
    Formats a `Tender` object to a following JSON format:
            **{ "id": id,\n
            "name": name\n
            "description": description,\n
            "status": status\n
            "serviceType": serviceType,\n
            "verstion": version,\n
            "createdAt": createdAt }**
    Args:
        tender:
            `Tender` object to format.

    Returns:
        JSON-like object.
    """

    return {"id": tender.id,
            "name": tender.name,
            "description": tender.description,
            "status": tender.status,
            "serviceType": tender.serviceType,
            "verstion": tender.version,
            "createdAt": tender.createdAt}
