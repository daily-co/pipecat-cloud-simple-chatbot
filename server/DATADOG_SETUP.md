# Datadog Integration Setup

This project has been configured with comprehensive Datadog monitoring including logging, tracing, and custom metrics.

## Prerequisites

1. **Datadog Account**: You need a Datadog account and API key
2. **Pipecat Base Image**: Using `dailyco/pipecat-base:0.0.7` or later

## Configuration Files

### 1. `datadog.yaml`
Main Datadog agent configuration file:
- Enables logging, tracing, and custom metrics
- Configures Datadog site (update `site` field to match your Datadog instance)
- Sets hostname for identification in Datadog dashboards

### 2. `pre-app.sh`
Script that runs before the bot starts:
- Writes the Datadog API key to the agent config
- Starts the Datadog agent and trace agent services
- Includes debugging commands (commented out)

### 3. `python.d/conf.yaml`
Configures log collection:
- Collects logs from `/var/log/pipecat-chatbot/datadog.log`
- Tags logs with service name `pipecat-chatbot`

### 4. Updated `Dockerfile`
- Installs Datadog Agent 7
- Copies configuration files
- Creates necessary directories and permissions
- Sets up the pre-app script

### 5. Updated `requirements.txt`
Added Datadog Python libraries:
- `ddtrace` - for distributed tracing
- `datadog` - for custom metrics

## Environment Variables

Add your Datadog API key to your `.env` file:
```
DD_API_KEY=your_datadog_api_key_here
```

Then update your secret set:
```bash
pcc secrets set <your-agent-secrets> --file .env
```

## Bot Code Integration

The `bot.py` file includes:

### Logging
- Custom Datadog log formatter that outputs JSON format
- Structured logging with session IDs for searchability
- Logs written to `/var/log/pipecat-chatbot/datadog.log`

### Tracing
- `@tracer.wrap()` decorators on main functions
- Distributed tracing across service calls

### Custom Metrics
- Bot initialization metrics: `pipecat.bot.initialized`
- Participant events:
  - `pipecat.participant.first_joined`
  - `pipecat.participant.joined`
  - `pipecat.participant.left`

## Usage

1. **Set your Datadog API key** in the `.env` file
2. **Update the Datadog site** in `datadog.yaml` if needed (e.g., `us5.datadoghq.com`)
3. **Deploy your bot** - Datadog monitoring will start automatically

## Datadog Features Enabled

- ✅ **Logging**: Structured JSON logs with session tracking
- ✅ **Tracing**: Distributed tracing across function calls
- ✅ **Custom Metrics**: Bot and participant lifecycle metrics

## Customization

### Adding More Metrics
```python
from datadog import statsd

# In your code
statsd.increment("your.custom.metric")
statsd.gauge("your.custom.gauge", value)
statsd.histogram("your.custom.histogram", value)
```

### Adding More Traces
```python
from ddtrace import tracer

@tracer.wrap()
def your_function():
    # Function will be traced
    pass
```

### Adding Structured Logging
```python
# Log with session context
logger.bind(session_id=session_id).info("Your message here")
```

## Troubleshooting

1. **Check agent status** - Uncomment debugging lines in `pre-app.sh`
2. **Log file permissions** - Ensure `/var/log/pipecat-chatbot/` is writable
3. **API key validation** - Verify your Datadog API key is correct
4. **Datadog site** - Ensure the site in `datadog.yaml` matches your account

The Datadog agent logs are available at `/var/log/datadog/agent.log` for debugging.
