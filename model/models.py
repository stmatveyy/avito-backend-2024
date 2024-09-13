from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Enum, UUID)

from sqlalchemy.orm import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class Employee(Base):

    __tablename__ = "employee"

    id = Column(UUID(100), primary_key=True, default=uuid.uuid4())
    username = Column(String(50), unique=True, nullable=False)
    first_name = Column(String(50))
    last_name = Column(String(50))
    created_at = Column(DateTime, default=datetime.now())
    updated_at = Column(DateTime, default=datetime.now())


class Organization(Base):

    __tablename__ = "organization"

    id = Column(UUID(100), primary_key=True, default=uuid.uuid4())
    name = Column(String(100), nullable=False)
    description = Column(Text)
    type = Column(Enum("IE", "LLC", "JSC", name="organization_type"), nullable=False)
    created_at = Column(DateTime, default=datetime.now())
    updated_at = Column(DateTime, default=datetime.now())


class OrganizationResponsible(Base):

    __tablename__ = "organization_responsible"

    id = Column(UUID(100), primary_key=True, default=uuid.uuid4())
    organization_id = Column(UUID, ForeignKey('organization.id', ondelete='CASCADE'))
    user_id = Column(UUID, ForeignKey('employee.id', ondelete='CASCADE'))


class Tender(Base):

    __tablename__ = "tender"
    id = Column(String(100), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=False)
    serviceType = Column(Enum("Construction", "Delivery", "Manufacture", name="tenderServiceType"),
                         nullable=False)
    status = Column(Enum("Created", "Published", "Closed", name="tenderStatus"),
                    nullable=False)
    organizationId = Column(UUID(100), ForeignKey('organization.id', ondelete='CASCADE'),
                            nullable=False)
    version = Column(Integer, nullable=False, default=1)
    createdAt = Column(String, nullable=False)


class Bid(Base):

    __tablename__ = "bid"

    id = Column(String(100), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(100), nullable=False)
    status = Column(Enum("Created", "Published", "Canceled", "Approved", "Rejected", name="bidStatus"),
                    nullable=False)
    tenderId = Column(String(100), nullable=False)
    authorType = Column(Enum("Organization", "User", name="bidAuthorType"))
    authorId = Column(UUID(100), nullable=False)
    version = Column(Integer, default=1, nullable=False)
    createdAt = Column(String, nullable=False)


class BidReview(Base):

    __tablename__ = "bidReview"

    id = Column(String(100), primary_key=True, index=True)
    description = Column(String(1000), nullable=False)
    createdAt = Column(String, nullable=False)
