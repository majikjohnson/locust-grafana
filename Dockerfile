FROM alpine

WORKDIR /opt/locust
COPY . /opt/locust

RUN apk add --no-cache python3 py3-pip
RUN apk add --no-cache build-base python3-dev libffi-dev gcc musl-dev make \
    && python3 -m pip install --upgrade pip \
    && pip install wheel \
    && pip install -r requirements.txt

ENTRYPOINT [ "locust" ]

ENV PYTHONUNBUFFERED=1