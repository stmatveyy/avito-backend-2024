FROM python:3.12.6 AS build

WORKDIR /home/project
COPY . .

RUN pip install -r requirements.txt

EXPOSE 8080

ENTRYPOINT ["python", "main.py"]

