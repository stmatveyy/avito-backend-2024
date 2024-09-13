from model.models import BidReview
from typing import Any


def format_review(rev: BidReview) -> dict[str, Any]:
    """
    Formats a `BidReview` object to a following JSON format:
            **{"id": authorId,\n
            "description": description,
            "createdAt": createdAt}**
    Args:
        rev:
            `BidReview` object to format

    Returns:
        JSON-like object.
    """
    return {"id": rev.id,
            "description": rev.description,
            "createdAt": rev.createdAt}
