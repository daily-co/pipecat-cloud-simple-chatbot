FROM dailyco/pipecat-base:latest

RUN apt-get update && \
    apt-get install -y gcc pkg-config python3-dev libcairo2-dev gobject-introspection libgirepository1.0-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt requirements.txt

COPY ./assets assets

RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY ./bot.py bot.py
