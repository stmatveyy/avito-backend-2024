FROM python:3.12.6 AS build

WORKDIR /home/project
COPY . .

RUN pip install pipenv
RUN pipenv install 

EXPOSE 8080

ENTRYPOINT ["uvicorn", "src.backend.main:app", "--reload", "--port","8080"]

