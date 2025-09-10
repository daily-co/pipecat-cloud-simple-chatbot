FROM dailyco/pipecat-base:0.0.7

# Install the Datadog Agent
# (note that you can literally use "dummy"—or anything else—as the API key)
RUN apt-get -y update; apt-get -y install curl
RUN DD_API_KEY=dummy \
    DD_INSTALL_ONLY=true \
    bash -c "$(curl -L https://install.datadoghq.com/scripts/install_script_agent7.sh)"

# Configure Datadog Agent
COPY ./datadog.yaml /etc/datadog-agent
# Include the below line if you need logging (see "Enabling Logging")
COPY ./python.d /etc/datadog-agent/conf.d/python.d

# Include the below lines only if you need traces or custom metrics (see "Enabling Traces" or "Enabling Custom Metrics")
# Prepare file system for the Datadog Agent to use for Unix Sockets
RUN mkdir -p /var/run/datadog/
RUN chown dd-agent:dd-agent /var/run/datadog/

# Create directory for bot logs
RUN mkdir -p /var/log/pipecat-chatbot/
RUN chown dd-agent:dd-agent /var/log/pipecat-chatbot/

# Start Datadog Agent (move pre-app script to expected place where it'll be invoked by Pipecat Cloud base image)
COPY --chmod=755 ./pre-app.sh /app/

COPY ./requirements.txt requirements.txt

COPY ./assets assets

RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY ./bot.py bot.py
