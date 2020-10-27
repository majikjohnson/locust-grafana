FROM python:3-alpine

COPY . /opt/locust
WORKDIR /opt/locust
RUN apk add --no-cache python3-dev libffi-dev gcc musl-dev make
RUN python -m pip install --upgrade pip
RUN pip install -r requirements.txt