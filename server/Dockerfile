FROM dailyco/pipecat-base:latest

RUN apt-get update && \
    apt-get install -y \
        gcc pkg-config python3-dev libcairo2-dev \
        gobject-introspection libgirepository1.0-dev \
        libgstreamer1.0-0 libgstreamer-plugins-base1.0-0 \
        gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
        gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly \
        gstreamer1.0-libav gstreamer1.0-tools \
        python3-gi gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt requirements.txt

COPY ./assets assets

RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY ./bot.py bot.py
