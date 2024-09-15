from typing import List, Dict, Any
import datetime
import sys
import logging
from os import getenv
import os
from pyrfc3339 import generate
import pytz

import uvicorn
from fastapi import FastAPI, status as http_status, Depends, Query, Request
from fastapi.exceptions import RequestValidationError, ValidationException
from fastapi.responses import JSONResponse
from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from model.models import Tender, Bid, BidReview
from model.create import get_db

from src.backend.misc.validators import (tender as tender_model,
                              bid as bid_model)

from src.backend.misc.checkers import (bid as validate_bid,
                            organisation as validate_org,
                            tender as validate_tender,
                            user as validate_user)

from src.backend.misc.generators import (bid as generate_bid,
                              tender as generate_tender)

from src.backend.misc.getters import (bid as get_bid,
                           organisation as get_org,
                           tender as get_tender,
                           user as get_user)

from src.backend.misc.funcs import (bid as bid_funcs,
                         tender as tender_funcs,
                         review as review_funcs)


app = FastAPI(debug=True)

log = logging.getLogger(__name__)

ADDRESS = getenv("SERVER_ADDRESS")

if not ADDRESS:
    log.fatal(msg="Connection parameters not provided. Need SERVER_ADDRESS env variable")
    sys.exit(1)

APP_HOST = ADDRESS.split(sep=":")[0]
APP_PORT = int(ADDRESS.split(sep=":")[1])

@app.get("/api/ping")
def ping():
    return "ok"


@app.get("/api/tenders")
def get_tenders(service_type: List[str] = Query(...),
                limit: int = Query(5, ge=1),
                offset: int = Query(0, ge=0),
                only_new: bool = Query(default=False),
                session: Session = Depends(get_db)
                ):
    """
    Param **only_new**=True returns a list of only latest-vertion tenders 
    """

    valid_types: bool = set(service_type).issubset({"Construction", "Delivery", "Manufacture"})
    empty_types: bool = set(service_type).issubset({""})

    if not valid_types and not empty_types:
        return JSONResponse(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                content={"reason": "Invalid service type"})

    if only_new:
        query = select(Tender.id)
        if service_type != [""]:
            query = query.where(Tender.serviceType.in_(service_type))

        query = query.limit(limit).offset(offset).order_by(Tender.name)

        res = session.execute(query)
        tender_ids = res.scalars().all()

        stripped_tender_ids = [id[:36] for id in tender_ids]
        unique_tender_ids = set(stripped_tender_ids)

        return [tender_funcs.format_tender(
                get_tender.get_last_version_tender(tenderId=id,
                                                   session=session))
                for id in unique_tender_ids]

    query = select(Tender)
    if service_type != [""]:
        query = query.where(Tender.serviceType.in_(service_type))

    query = query.limit(limit).offset(offset).order_by(Tender.name)

    res = session.execute(query)
    tenders = res.scalars().all()

    return [tender_funcs.format_tender(tender) for tender in tenders]


@app.post("/api/tenders/new")
def post_tender(new_tender: tender_model.NewTender,
                session: Session = Depends(get_db)):

    response = validate_user.invalid_user_name(username=new_tender.creatorUsername,
                                                                    session=session)

    if response:
        return JSONResponse(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            content={"reason": "No such user"})

    response = validate_user.invalid_user_rights(username=new_tender.creatorUsername,
                                                 session=session)
    if response:
        return response

    response = validate_org.invalid_org_id(orgId=new_tender.organizationId,
                                           session=session)
    if response:
        return response

    if new_tender.serviceType not in {"Construction", "Delivery", "Manufacture"}:
        return JSONResponse(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            content={"reason": "Indalid service type"})

    if new_tender.status not in {"Created", "Published", "Canceled", "Approved", "Rejected"}:
        return JSONResponse(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            content={"reason": "Indalid status"})

    try:

        tender = Tender(
                id=next(generate_tender.gen_tender_id(session=session)),
                name=new_tender.name,
                description=new_tender.description,
                serviceType=new_tender.serviceType,
                status=new_tender.status,
                organizationId=new_tender.organizationId,
                version=1,
                createdAt=generate(datetime.datetime.now(datetime.UTC)
                                   .replace(tzinfo=pytz.utc))
            )

        session.add(tender)
        session.commit()
        session.refresh(tender)

    except ValidationException:
        session.rollback()

        return JSONResponse(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            content={"reason": "Invalid request body or parameters"})

    except IntegrityError as ie:
        session.rollback()
        log.fatal(msg=f"Integrity error while creating tender. Reason:{ie}")

        return JSONResponse(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"reason": "IntegrityError. See logs for info."}
        )

    return tender_funcs.format_tender(tender=tender)


@app.get("/api/tenders/my")
def get_my_tenders(
                   username: str = Query(...),
                   limit: int = Query(5, ge=1),
                   offset: int = Query(0, ge=0),
                   session: Session = Depends(get_db)):

    response = validate_user.invalid_user_name(username=username,
                                               session=session)

    if response:
        return JSONResponse(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            content={"reason": "No such user"})

    response = validate_user.invalid_user_rights(username=username,
                                                 session=session)
    if response:
        return JSONResponse(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            content={"reason": "No organisation found for user"})

    org_id = get_org.get_respondible_org_id(session=session, username=username)

    res = session.execute(select(Tender).where(Tender.organizationId == org_id)
                                        .limit(limit)
                                        .offset(offset)
                                        .order_by(Tender.name))

    tenders_list = res.scalars().all()

    return [tender_funcs.format_tender(tender) for tender in tenders_list]


@app.get("/api/tenders/{tenderId}/status")
def get_tender_status(
                    tenderId: str,
                    username: str = Query(...),
                    session: Session = Depends(get_db)):

    response = validate_user.invalid_user_name(username=username,
                                               session=session)
    if response:
        return JSONResponse(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            content={"reason": "No such user"})

    response = validate_user.invalid_user_rights(username=username,
                                                 session=session)
    if response:
        return response

    response = validate_tender.invalid_tender_id(tenderId=tenderId,
                                                 session=session)
    if response:
        return JSONResponse(
            status_code=http_status.HTTP_404_NOT_FOUND,
            content={"reason": "No such tender"})

    org_id = get_org.get_respondible_org_id(username=username,
                                            session=session)
    res = session.execute(select(Tender.status)
                          .filter(Tender.id.match(f"{tenderId}%"))
                          .where(Tender.organizationId == org_id))

    return res.scalars().first()


@app.put("/api/tenders/{tenderId}/status")
def change_status(
                tenderId: str,
                username: str = Query(...),
                status: str = Query(...),
                session: Session = Depends(get_db)):

    if status not in {"Created", "Published", "Closed"}:
        return JSONResponse(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            content={"reason": "Invalid status"})

    response = validate_user.invalid_user_name(username=username,
                                               session=session)
    if response:
        return JSONResponse(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            content={"reason": "No such user"})

    response = validate_user.invalid_user_rights(username=username,
                                                 session=session)
    if response:
        return response

    response = validate_tender.invalid_tender_id(tenderId=tenderId,
                                                 session=session)
    if response:
        return JSONResponse(
            status_code=http_status.HTTP_404_NOT_FOUND,
            content={"reason": "No such tender"})

    try:
        last_tender_id = get_tender.get_last_version_tender(tenderId=tenderId,
                                                            session=session).id
        session.execute(update(Tender)
                        .where(Tender.id == last_tender_id)
                        .values(status=status))
        session.commit()

        res = session.execute(select(Tender)
                              .where(Tender.id == last_tender_id))
        curr_tender = res.scalars().first()
        return tender_funcs.format_tender(curr_tender)

    except IntegrityError as ie:
        session.rollback()
        log.fatal(msg=f"Integrity error while creating tender. Reason:{ie}")

        return JSONResponse(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"reason": "IntegrityError. See logs for info"}
        )


@app.patch("/api/tenders/{tenderId}/edit")
def edit_tender(fields: Dict[str, Any],
                tenderId: str,
                username: str = Query(...),
                session: Session = Depends(get_db)):

    response = validate_user.invalid_user_name(username=username,
                                               session=session)
    if response:
        return response

    response = validate_user.invalid_user_rights(username=username,
                                                 session=session)
    if response:
        return response

    response = validate_tender.invalid_tender_id(tenderId=tenderId,
                                                 session=session)
    if response:
        return JSONResponse(
                status_code=http_status.HTTP_404_NOT_FOUND,
                content={"reason": "No such tender"})

    for key in fields.keys():

        if key not in {"name", "description", "serviceType"}:
            return JSONResponse(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                content={"reason": "Invalid fields"})

        if key == "serviceType" and fields[key] not in {"Construction", "Delivery", "Manufacture"}:
            return JSONResponse(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                content={"reason": "Invalid serviceType"})

        elif key == "name" and len(fields[key]) > 100:
            return JSONResponse(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                content={"reason": "Invalid name"})

        elif key == "description" and len(fields[key]) > 500:
            return JSONResponse(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                content={"reason": "Invalid description"})

    tender_to_change = tender_funcs.make_tender_copy(session=session,
                                                     tenderId=tenderId)

    for key, value in fields.items():
        setattr(tender_to_change, key, value)

    try:
        session.execute(update(Tender)
                        .where(Tender.id == tender_to_change.id
                               and Tender.version == tender_to_change.version)
                        .values(
                                name=tender_to_change.name,
                                description=tender_to_change.description,
                                serviceType=tender_to_change.serviceType))

        session.commit()
        session.refresh(tender_to_change)

        return tender_funcs.format_tender(tender_to_change)

    except ValidationException as ve:
        session.rollback()
        log.fatal(msg=f"Validation exception while creating tender. Reason:{ve}")

        return JSONResponse(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            content={"reason": "Invalid request body or parameters"})

    except IntegrityError as ie:
        session.rollback()
        log.fatal(msg=f"Integrity error while editing tender. Reason:{ie}")

        return JSONResponse(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"reason": "IntegrityError. See logs for info."}
        )


@app.put("/api/tenders/{tenderId}/rollback/{version}")
def tender_rollback(tenderId: str,
                    version: int,
                    username: str = Query(...),
                    session: Session = Depends(get_db)):

    response = validate_tender.invalid_tender_id(tenderId=tenderId,
                                                 session=session)
    if response:
        return JSONResponse(
                status_code=http_status.HTTP_404_NOT_FOUND,
                content={"reason": "No such tender"})

    response = validate_user.invalid_user_name(username=username,
                                               session=session)
    if response:
        return JSONResponse(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                content={"reason": "No such user"})

    response = validate_user.invalid_user_rights(username=username,
                                                 session=session)
    if response:
        return response

    response = validate_tender.invalid_tender_version(ver=version,
                                                      tenderId=tenderId,
                                                      session=session)
    if response:
        return response

    res = session.execute(select(Tender)
                          .filter(Tender.id.match(f"{tenderId}%"))
                          .where(Tender.version == version))
    copy_from = res.scalars().first()

    last_version = get_tender.get_last_version_tender(tenderId=tenderId,
                                                      session=session).version

    backed_up = Tender(
        id=f"{copy_from.id}" + "*" * (last_version - copy_from.version + 1),
        name=copy_from.name,
        description=copy_from.description,
        serviceType=copy_from.serviceType,
        status=copy_from.status,
        organizationId=copy_from.organizationId,
        version=last_version + 1,
        createdAt=generate(datetime.datetime.now(datetime.UTC)
                                            .replace(tzinfo=pytz.utc))
    )

    try:
        session.add(backed_up)
        session.commit()
        session.refresh(backed_up)

        return tender_funcs.format_tender(backed_up)

    except IntegrityError as ie:
        session.rollback()
        log.fatal(msg=f"Integrity error while rollbacking. Reason:{ie}")

        return JSONResponse(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"reason": "IntegrityError. See logs for info."}
        )


@app.post("/api/bids/new")
def new_bid(bid: bid_model.NewBid,
            session: Session = Depends(get_db)):

    response = validate_tender.invalid_tender_id(tenderId=bid.tenderId,
                                                 session=session)
    if response:
        return response

    response = validate_user.invalid_user_name(username=bid.creatorUsername,
                                               session=session)
    if response:
        return JSONResponse(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                content={"reason": "No such user"})

    invalid_status: bool = bid.status not in {"Created",
                                              "Published",
                                              "Canceled",
                                              "Approved",
                                              "Rejected"}

    if invalid_status:
        return JSONResponse(
                            status_code=http_status.HTTP_400_BAD_REQUEST,
                            content={"reason": "Invalid status"})

    response = validate_user.invalid_user_rights(session=session,
                                                 username=bid.creatorUsername)
    if response:
        return response

    response = validate_org.invalid_org_id(orgId=bid.organizationId,
                                           session=session)
    if response:
        return response

    latest_tender_id = get_tender.get_last_version_tender(tenderId=bid.tenderId,
                                                          session=session).id

    bid_to_write = Bid(
                        id=next(generate_bid.gen_bid_id(session=session)),
                        name=bid.name,
                        description=bid.description,
                        status=bid.status,
                        tenderId=latest_tender_id,
                        authorType="Organization",
                        authorId=bid.organizationId,
                        version=1,
                        createdAt=generate(datetime.datetime.now(datetime.UTC)
                                                            .replace(tzinfo=pytz.utc)))
    try:
        session.add(bid_to_write)
        session.commit()
        session.refresh(bid_to_write)

        return bid_funcs.format_bid(bid_to_write)

    except IntegrityError as ie:
        session.rollback()
        log.fatal(msg=f"Integrity error while creating bid. Reason:{ie}")

        return JSONResponse(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"reason": "IntegrityError. See logs for info."}
        )


@app.get("/api/bids/my")
def get_my_bids(username: str = Query(...),
                only_new: bool = Query(default=False),
                limit: int = Query(5, ge=1),
                offset: int = Query(0, ge=0),
                session: Session = Depends(get_db)):

    response1 = validate_user.invalid_user_name(username=username,
                                                session=session)
    response2 = validate_user.invalid_user_rights(username=username,
                                                  session=session)
    if response1 or response2:
        return JSONResponse(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                content={"reason": "No such user"})

    author_id = get_org.get_respondible_org_id(session=session,
                                               username=username)

    if only_new:
        where_statement: bool = Bid.authorId == author_id
        return bid_funcs.only_fresh(limit=limit,
                                    offset=offset,
                                    session=session,
                                    where_statement=where_statement)

    query = (select(Bid)
             .where(Bid.authorId == author_id)
             .limit(limit)
             .offset(offset)
             .order_by(Bid.name))

    res = session.execute(query)

    complete_bids = res.scalars().all()

    return [bid_funcs.format_bid(bid) for bid in complete_bids]


@app.get("/api/bids/{tenderId}/list")
def get_bids_for_tender(tenderId: str,
                        username: str = Query(...),
                        limit: int = Query(5, ge=1),
                        offset: int = Query(0, ge=0),
                        session: Session = Depends(get_db)):

    response = validate_user.invalid_user_name(username=username,
                                               session=session)
    if response:
        return JSONResponse(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                content={"reason": "No such user"})

    response = validate_user.invalid_user_rights(username=username,
                                                 session=session)
    if response:
        return response

    response = validate_tender.invalid_tender_id(tenderId=tenderId,
                                                 session=session)
    if response:
        return response

    res = session.execute(select(Bid)
                          .filter(Bid.tenderId.match(f"{tenderId}%"))
                          .order_by(Bid.name)
                          .limit(limit)
                          .offset(offset))

    bid_list = res.scalars().all()
    if len(bid_list) == 0:
        return JSONResponse(
                status_code=http_status.HTTP_404_NOT_FOUND,
                content={"reason": "No bids for this tender"})

    return [bid_funcs.format_bid(bid) for bid in bid_list]


@app.get("/api/bids/{bidId}/status")
def get_bid_status(bidId: str,
                   username: str = Query(...),
                   session: Session = Depends(get_db)):

    response = validate_user.invalid_user_name(username=username,
                                               session=session)
    if response:
        return JSONResponse(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                content={"reason": "No such employee"})

    response = validate_user.invalid_user_rights(username=username,
                                                 session=session)
    if response:
        return response

    response = validate_bid.invalid_bid_id(bidId=bidId, session=session)
    if response:
        return JSONResponse(
                status_code=http_status.HTTP_404_NOT_FOUND,
                content={"reason": "No such bid"})

    res = session.execute(select(Bid.status).filter(Bid.id.match(f"{bidId}%")))
    return res.scalars().one()


@app.put("/api/bids/{bidId}/status")
def change_bid_status(bidId: str,
                      status: str,
                      username: str,
                      session: Session = Depends(get_db)):

    valid_status: bool = status in {"Created", "Published", "Canceled", "Approved", "Rejected"}

    if not valid_status:

        return JSONResponse(
                            status_code=http_status.HTTP_400_BAD_REQUEST,
                            content={"reason": "Invalid status"})

    response = validate_user.invalid_user_name(username=username,
                                               session=session)
    if response:
        return JSONResponse(
                status_code=http_status.HTTP_401_UNAUTHORIZED,
                content={"reason": "No such employee"})

    response = validate_bid.invalid_bid_id(bidId=bidId,
                                           session=session)
    if response:
        return JSONResponse(
                status_code=http_status.HTTP_404_NOT_FOUND,
                content={"reason": "No such bid"})

    response = validate_user.invalid_user_rights(username=username,
                                                 session=session)
    if response:
        return response

    try:
        latest_version_id = get_bid.get_last_version_bid(session=session, bidId=bidId).id

        session.execute(update(Bid)
                        .where(Bid.id == latest_version_id)
                        .values(status=status))
        session.commit()

        res = session.execute(select(Bid).where(Bid.id == latest_version_id))
        updated_bid = res.scalars().one()

        return bid_funcs.format_bid(updated_bid)

    except IntegrityError as ie:
        session.rollback()
        log.fatal(msg=f"Integrity error while changing bid status. Reason:{ie}")

        return JSONResponse(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"reason": "IntegrityError. See logs for info."}
        )


@app.patch("/api/bids/{bidId}/edit")
def edit_bid(fields: Dict[str, Any],
             bidId: str,
             username: str = Query(...),
             session: Session = Depends(get_db)):

    response = validate_user.invalid_user_name(username=username,
                                               session=session)
    if response:
        return response

    response = validate_user.invalid_user_rights(username=username,
                                                 session=session)
    if response:
        return response

    response = validate_bid.invalid_bid_id(bidId=bidId,
                                           session=session)
    if response:
        return JSONResponse(
                status_code=http_status.HTTP_404_NOT_FOUND,
                content={"reason": "Bid not found"})

    for key in fields.keys():
        if key not in {"name", "description"}:
            return JSONResponse(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                content={"reason": "Invalid fields"})

        if key == "name" and len(fields[key]) > 100:
            return JSONResponse(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                content={"reason": "Invalid name"})

        if key == "description" and len(fields[key]) > 500:
            return JSONResponse(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                content={"reason": "Invalid description"})

    bid_to_change = bid_funcs.make_bid_copy(session=session, bidId=bidId)

    for key, value in fields.items():
        setattr(bid_to_change, key, value)

    try:
        session.execute(update(Bid)
                        .where(Bid.id == bid_to_change.id
                               and Bid.version == bid_to_change.version)
                        .values(
                                name=bid_to_change.name,
                                description=bid_to_change.description))

        session.commit()
        session.refresh(bid_to_change)

        return bid_funcs.format_bid(bid_to_change)

    except IntegrityError as ie:
        session.rollback()
        log.fatal(msg=f"Integrity error while editing bid. Reason:{ie}")

        return JSONResponse(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"reason": "IntegrityError. See logs for info."}
        )


@app.put("/api/bids/{bidId}/submit_decision")
def submit_decision(bidId: str,
                    decision: str = Query(...),
                    username: str = Query(...),
                    session: Session = Depends(get_db)):

    if decision not in {"Approved", "Rejected"}:
        return JSONResponse(
                            status_code=http_status.HTTP_400_BAD_REQUEST,
                            content={"reason": "Invalid decision"})

    response = validate_bid.invalid_bid_id(bidId=bidId, session=session)
    if response:
        return JSONResponse(
                            status_code=http_status.HTTP_404_NOT_FOUND,
                            content={"reason": "No such bid"})

    last_version_bid = get_bid.get_last_version_bid(bidId=bidId,
                                                    session=session)
    last_version_id = last_version_bid.id
    if last_version_bid.status == "Rejected":
        return JSONResponse(
                            status_code=http_status.HTTP_400_BAD_REQUEST,
                            content={"reason": "Invalid bid status (Already rejected)"})

    response = validate_user.invalid_user_name(session=session,
                                               username=username)
    if response:
        return JSONResponse(
                            status_code=http_status.HTTP_401_UNAUTHORIZED,
                            content={"reason": "No such user"})

    response = validate_user.invalid_user_rights(username=username,
                                                 session=session)
    if response:
        return response

    if decision == "Rejected":
        session.execute(update(Bid)
                        .where(Bid.id == last_version_bid.id)
                        .values(status="Rejected"))
        session.commit()

    else:
        session.execute(update(Bid)
                        .where(Bid.id == last_version_bid.id)
                        .values(status="Approved"))
        session.commit()

        res = session.execute(select(Bid.tenderId)
                              .where(Bid.id == last_version_id))
        tenderId = res.scalars().one()

        session.execute(delete(Tender).where(Tender.id == tenderId))
        session.commit()

    res = session.execute(select(Bid).where(Bid.id == last_version_bid.id))
    bid = res.scalars().one()

    return bid_funcs.format_bid(bid)


@app.put("/api/bids/{bidId}/feedback")
def post_feedback(bidId: str,
                  bidFeedback: str = Query(...),
                  username: str = Query(...),
                  session: Session = Depends(get_db)):

    response = validate_bid.invalid_bid_id(bidId=bidId, session=session)
    if response:
        return JSONResponse(
                            status_code=http_status.HTTP_404_NOT_FOUND,
                            content={"reason": "No such bid"})

    if len(bidFeedback) > 1000:
        return JSONResponse(
                            status_code=http_status.HTTP_400_BAD_REQUEST,
                            content={"reason": "Invalid feedback"})

    response = validate_user.invalid_user_name(username=username,
                                               session=session)
    if response:
        return JSONResponse(
                            status_code=http_status.HTTP_401_UNAUTHORIZED,
                            content={"reason": "No such user"})

    response = validate_user.invalid_user_rights(username=username,
                                                 session=session)
    if response:
        return response

    latest_bid: Bid = get_bid.get_last_version_bid(bidId=bidId,
                                                   session=session)

    review = BidReview(
        id=latest_bid.id,
        description=bidFeedback,
        createdAt=generate(datetime.datetime.now(datetime.UTC)
                                   .replace(tzinfo=pytz.utc)))

    existing_review = session.execute(select(BidReview)
                                      .where(BidReview.id == latest_bid.id)).scalar_one_or_none()

    if existing_review:
        session.execute(delete(BidReview)
                        .where(BidReview.id == latest_bid.id))

    session.commit()
    session.add(review)
    session.commit()
    session.refresh(review)

    latest_bid: Bid = get_bid.get_last_version_bid(bidId=bidId,
                                                   session=session)
    return bid_funcs.format_bid(latest_bid)

@app.get("/api/{tenderId}/reviews")
def get_bid_reviews(tenderId: str,
                    authorUsername: str = Query(...),
                    limit: int = Query(5, ge=1),
                    offset: int = Query(0, ge=0),
                    requesterUsername: str = Query(...),
                    session: Session = Depends(get_db)):

    response = validate_user.invalid_user_name(username=requesterUsername,
                                               session=session)
    if response:
        return response

    response = validate_user.invalid_user_name(username=authorUsername,
                                               session=session)
    if response:
        return response

    response = validate_user.invalid_user_rights(username=requesterUsername,
                                                 session=session)
    if response:
        return response

    response = validate_user.invalid_user_rights(username=authorUsername,
                                                 session=session)
    if response:
        return response

    response = validate_tender.invalid_tender_id(tenderId=tenderId,
                                                 session=session)
    if response:
        return response

    autor_id = get_org.get_respondible_org_id(username=authorUsername,
                                              session=session)

    res = session.execute(select(Bid.id)
                          .where(Bid.authorId == autor_id))

    creator_bids_ids = res.scalars().all()

    res = session.execute(select(BidReview)
                          .where(BidReview.id.in_(creator_bids_ids))
                          .limit(limit)
                          .offset(offset))

    reviews_list = res.scalars().all()
    if reviews_list == [""]:
        return JSONResponse(status_code=http_status.HTTP_404_NOT_FOUND,
                            content={"reason": "Reviews not found."})

    return [review_funcs.format_review(review) for review in reviews_list]


@app.put("/api/bids/{bidId}/rollback/{version}")
def bid_rollback(bidId: str,
                 version: int,
                 username: str = Query(...),
                 session: Session = Depends(get_db)):

    response = validate_bid.invalid_bid_id(bidId=bidId, session=session)
    if response:
        return JSONResponse(
                            status_code=http_status.HTTP_400_BAD_REQUEST,
                            content={"reason": "No such bid"})

    response = validate_bid.invalid_bid_version(ver=version,
                                                bidId=bidId,
                                                session=session)
    if response:
        return response

    response = validate_user.invalid_user_name(username=username,
                                               session=session)
    if response:
        return JSONResponse(
                            status_code=http_status.HTTP_401_UNAUTHORIZED,
                            content={"reason": "No such user"})

    response = validate_user.invalid_user_rights(username=username,
                                                 session=session)
    if response:
        return response

    res = session.execute(select(Bid)
                          .filter(Bid.id.match(f"{bidId}%"))
                          .where(Bid.version == version))
    copy_from = res.scalars().first()

    last_version = get_bid.get_last_version_bid(bidId=bidId, session=session).version

    backed_up = Bid(
                    id=f"{copy_from.id}" + "*" * (last_version - copy_from.version + 1),
                    name=copy_from.name,
                    description=copy_from.description,
                    status=copy_from.status,
                    tenderId=copy_from.tenderId,
                    authorType=copy_from.authorType,
                    authorId=copy_from.authorId,
                    version=last_version + 1,
                    createdAt=generate(datetime.datetime.now(datetime.UTC)
                                                        .replace(tzinfo=pytz.utc))
                )

    try:
        session.add(backed_up)
        session.commit()
        session.refresh(backed_up)

        return bid_funcs.format_bid(backed_up)

    except IntegrityError as ie:
        session.rollback()
        log.fatal(msg=f"Integrity error while rollbacking a bid. Reason:{ie}")

        return JSONResponse(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"reason": "IntegrityError. See logs for info."}
        )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=http_status.HTTP_400_BAD_REQUEST,
        content={"reason": exc.errors()},
    )

if __name__ == "__main__":
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)