FROM alpine:3.22.1

WORKDIR /application

RUN apk update && apk add --no-cache python3 py3-pip sqlite bash
RUN python3 -m venv venv

COPY . .
RUN ./venv/bin/python -m pip install --no-cache-dir -r requirements.txt
RUN sqlite3 database.db < schema.sql
RUN mkdir storage

EXPOSE 5000

CMD [ "bash", "-c", "./venv/bin/gunicorn -w $((2 * $(nproc) + 1)) -b 0.0.0.0:5000 app:app" ]