from fastapi import status as http_status
from fastapi.responses import JSONResponse
from uuid import UUID


def _invalid_uuid4(id: str) -> None | JSONResponse:
    """
    Checks if **id** is a valid UUID4-like string.

    Args:
        id:
            String to check.
    Returns:
        - `None` if **id** is UUID4-like.
        - `JSONResponce` (400) if **id** is not UUID4 valid.
    """

    try:
        _dummy = UUID(id)

    except ValueError:

        return JSONResponse(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            content={"reason": "UUID is invalid"})

    return None
