from sqlalchemy.orm import Session
from model.models import OrganizationResponsible
from uuid import UUID
from sqlalchemy import select

from .user import get_user_id
from ..checkers import user as user_checkers


def get_respondible_org_id(session: Session,
                           username: str) -> UUID:
    """
    Returns `organization_responsible.id` by responsible employee username

    Args:
        session:
            Current database session.
        username:
            Username of a responsible employee

    Returns:
        - `UUID` object if user exists and authorised.
        - `JSONResponse` (401) if if given **username** not found.
        - `JSONResponse` (403) if user is not authorised.
    """
    response = user_checkers.invalid_user_name(session=session,
                                               username=username)
    if response:
        return response

    response = user_checkers.invalid_user_rights(session=session,
                                                 username=username)
    if response:
        return response

    user_id = get_user_id(session=session, username=username)

    res = session.execute(select(OrganizationResponsible.organization_id)
                          .where(OrganizationResponsible.user_id
                                 == UUID(user_id)))
    return str(res.scalars().first())
