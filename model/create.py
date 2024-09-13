from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging
import sys
from os import getenv
log = logging.getLogger(__name__)


POSTGRES_URL: str = getenv("POSTGRES_CONN")
POSTGRES_USERNAME: str = getenv("POSTGRES_USERNAME")
POSTGRES_PASSWORD: str = getenv("POSTGRES_PASSWORD")
POSTGRES_HOST: str = getenv("POSTGRES_HOST")
POSTGRES_PORT: str = getenv("POSTGRES_PORT")
POSTGRES_DATABASE: str = getenv("POSTGRES_DATABASE")
POSTGRES_JDBC_URL: str = getenv("POSTGRES_JDBC_URL")

if POSTGRES_URL:
    if POSTGRES_URL.startswith("postgres://"):
        postgres_url = POSTGRES_URL.replace("postgres://", "postgresql://", 1)
    else:
        postgres_url = POSTGRES_URL

elif POSTGRES_JDBC_URL:
    postgres_url = POSTGRES_JDBC_URL

elif all([POSTGRES_USERNAME,
          POSTGRES_PASSWORD,
          POSTGRES_HOST,
          POSTGRES_DATABASE]):

    if POSTGRES_PORT:
        postgres_url = f"postgresql://{POSTGRES_USERNAME}\
                                    :{POSTGRES_PASSWORD}\
                                    @{POSTGRES_HOST}\
                                    :{POSTGRES_PORT}\
                                    /{POSTGRES_DATABASE}"
    else:
        postgres_url = f"postgresql://{POSTGRES_USERNAME}\
                                    :{POSTGRES_PASSWORD}\
                                    @{POSTGRES_HOST}\
                                    :5432\
                                    /{POSTGRES_DATABASE}"

else:
    log.fatal(msg="Could not connect to database (Parametrs not provided)")
    sys.exit(1)

engine = create_engine(postgres_url)
session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = session_local()
    try:
        yield db
    finally:
        db.close()
