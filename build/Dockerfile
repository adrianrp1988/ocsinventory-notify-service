FROM python:3.9-alpine3.18

COPY ./requirements.txt /tmp/

RUN pip install --no-cache-dir --upgrade -r /tmp/requirements.txt

RUN rm /tmp/requirements.txt

WORKDIR /app

COPY ./app .

CMD ["python", "-u", "/app/main.py"]
