FROM alpine

COPY . /opt/locust
WORKDIR /opt/locust
RUN apk add --no-cache build-base python3 python3-dev py3-pip libffi-dev gcc musl-dev make
RUN python3 -m pip install --upgrade pip && pip install wheel
RUN pip install -r requirements.txt
ENTRYPOINT [ "locust" ]

ENV PYTHONUNBUFFERED=1