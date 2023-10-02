FROM python:3.9-alpine3.18

WORKDIR /app

COPY ./app .

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

RUN rm requirements.txt

CMD ["python", "/app/main.py"]
