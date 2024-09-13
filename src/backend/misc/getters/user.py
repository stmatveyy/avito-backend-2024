from sqlalchemy.orm import Session
from model.models import Employee
from uuid import UUID
from sqlalchemy import select
from ..checkers import user as user_checkers


def get_user_id(session: Session,
                username: str) -> UUID:
    """
    Returns id of the user by username

    Args:
        session:
            Current database session.
        username:
            Username of a user.

    Returns:
        - `Bid` object if bid exists.
        - `JSONResponse` (400) if given **username** not found
    """
    response = user_checkers.invalid_user_name(session=session,
                                               username=username)
    if response:
        return response

    res = res = session.execute(select(Employee.id)
                                .where(Employee.username == username))

    return str(res.scalars().first())
