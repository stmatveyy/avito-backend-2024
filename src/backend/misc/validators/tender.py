from pydantic import BaseModel, Field


class NewTender(BaseModel):
    name: str = Field(max_length=100)
    description: str = Field(max_length=500)
    serviceType: str = Field()
    organizationId: str = Field(max_length=100)
    creatorUsername: str = Field(max_length=50)
    status: str = Field()
