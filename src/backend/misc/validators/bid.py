from pydantic import BaseModel, Field


class NewBid(BaseModel):
    name: str = Field(max_length=100)
    description: str = Field(max_length=500)
    status: str = Field()
    tenderId: str = Field(max_length=100)
    organizationId: str = Field(max_length=100)
    creatorUsername: str = Field(max_length=50)
    
