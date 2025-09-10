#!/bin/bash

# Write the Datadog API key to the config file
printf "api_key: %s\n" "$DD_API_KEY" >> /etc/datadog-agent/datadog.yaml

# Start the Datadog Agent service
service datadog-agent start || true

# Include the below line only if you need traces (see "Enabling Traces")
# HACK: here we restart the Datadog Trace Agent specifically, since we know it failed to start above
service datadog-agent-trace restart || true

## DEBUGGING

# Check the status of the Datadog Agent subsystems for logging, custom metrics, and traces
# service datadog-agent status
# service datadog-agent-trace status
# datadog-agent status

# Display the Datadog agent log
# cat /var/log/datadog/agent.log
