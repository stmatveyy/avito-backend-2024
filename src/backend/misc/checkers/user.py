from sqlalchemy.orm import Session
from fastapi import status as http_status
from fastapi.responses import JSONResponse
from model.models import Employee, OrganizationResponsible
from uuid import UUID
from sqlalchemy import select

from ..getters.user import get_user_id
from .universal import _invalid_uuid4


def invalid_user_name(session: Session,
                      username: str) -> None | JSONResponse:
    """
    Checks if **username** exists in a database.

    Args:
        session:
            Current database session. Must be of type `Session`
        username:
            User name.

    Returns:
        - `None` if given **user_id** exists.
        - `JSONResponse` (400) if given user not found
    """

    res = session.execute(select(Employee.username)
                          .where(Employee.username == username))

    if not res.scalar_one_or_none():
        return JSONResponse(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            content={"reason": "No such employee"})

    return None


def invalid_user_id(session: Session,
                    user_id: str) -> None | JSONResponse:
    """
    Checks if **user_id** exists in a database.

    Args:
        session:
            Current database session. Must be of type `Session`
        user_id:
            User id. Must be a valid UUID, without any * at the end

    Returns:
        - None if given user_id exists.
        - JSONResponce (404) if given user_id not found or UUID is invalid.
    """

    response = _invalid_uuid4(id=user_id)
    if response:
        return response

    res = session.execute(select(Employee.id)
                          .where(Employee.id == UUID(user_id)))

    if res.scalar_one_or_none() is None:
        return JSONResponse(
            status_code=http_status.HTTP_404_NOT_FOUND,
            content={"reason": "No such user"})

    return None


def invalid_user_rights(session: Session,
                        username: str) -> None | JSONResponse:
    """
    Checks if **username** is a responsible employee
    (`user_id` belongs to `organization_responsible.user_id`).

    Args:
        session:
            Current database session. Must be of `Session` type
        user_id:
            User id. Must be a valid UUID, without any * at the end

    Returns:
        - `None` if user is a responsible employee.
        - `JSONResponce` (403) if user is not authorised.
    """

    user_id = get_user_id(session=session, username=username)

    response = _invalid_uuid4(id=user_id)
    if response:
        return response

    res = session.execute(select(OrganizationResponsible.user_id)
                          .where(OrganizationResponsible.user_id ==
                                 UUID(user_id)))

    if res.scalar_one_or_none() is None:
        return JSONResponse(
            status_code=http_status.HTTP_403_FORBIDDEN,
            content={"reason": "Invalid user rights"})

    return None
