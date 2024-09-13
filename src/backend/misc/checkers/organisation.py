from sqlalchemy.orm import Session
from fastapi import status as http_status
from fastapi.responses import JSONResponse
from model.models import Organization
from uuid import UUID
from sqlalchemy import select
from .universal import _invalid_uuid4


def invalid_org_id(session: Session,
                   orgId: str) -> None | JSONResponse:
    """
    Checks if **orgId** exists in a database.

    Args:
        session:
            Current database session. Must be of type `Session`
        orgId:
            Organisation id. Must be a valid UUID4-like string,
            without any * at the end

    Returns:
        - `None` if given bidId exists.
        - `JSONResponce` (400) if given **bidId** not found
            or **id** is not UUID4 valid.
    """

    response = _invalid_uuid4(id=orgId)
    if response:
        return response

    res = session.execute(select(Organization.id)
                          .where(Organization.id == UUID(orgId)))

    if not res.scalar_one_or_none():

        return JSONResponse(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            content={"reason": "No such organisation"})

    return None
