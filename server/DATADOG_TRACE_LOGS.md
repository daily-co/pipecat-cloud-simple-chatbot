# 🔗 Datadog Trace ID Integration with Logs

## ✅ What's Now Configured

Your logging system now automatically includes trace IDs in every log entry, enabling powerful log-trace correlation in Datadog.

### **Enhanced Log Format**
```json
{
  "timestamp": "2025-09-10 16:30:45.123",
  "levelname": "INFO",
  "name": "bot",
  "function": "on_participant_joined",
  "line": 205,
  "message": "Participant joined the room",
  "session_id": "abc123",
  "dd.trace_id": "1234567890123456789",
  "dd.span_id": "9876543210987654321"
}
```

## 🎯 Key Benefits

### **1. Log-Trace Correlation**
- Click on any log in Datadog to see the related trace
- Navigate from traces to see all related logs
- Complete request lifecycle visibility

### **2. Distributed Debugging**
- Follow a single request across all services
- See exact log entries that occurred during a span
- Correlate errors with their trace context

### **3. Advanced Filtering**
```
# Find all logs for a specific trace
dd.trace_id:1234567890123456789

# Find logs within a specific span
dd.span_id:9876543210987654321

# Combine with other filters
service:pipecat-chatbot dd.trace_id:* @participant.name:manager
```

## 🔧 Advanced Usage Patterns

### **1. Adding Context to Logs**
```python
# In your event handlers or functions
logger.bind(
    session_id=session_id,
    participant_id=participant["id"],
    operation="participant_join"
).info("Processing participant join event")
```

### **2. Error Correlation**
```python
try:
    # Your code here
    await process_audio(audio_data)
except Exception as e:
    logger.bind(
        error_type=type(e).__name__,
        error_details=str(e)
    ).error("Audio processing failed")
    raise
```

### **3. Performance Logging**
```python
import time

start_time = time.time()
# Your operation
duration = time.time() - start_time

logger.bind(
    operation="llm_generation",
    duration_ms=duration * 1000,
    model="gpt-4o"
).info("LLM generation completed")
```

## 📊 Datadog UI Features

### **1. Log-to-Trace Navigation**
- In **Logs**: Click the trace icon next to any log entry
- In **APM**: Click "View Related Logs" in trace details
- Automatic correlation using `dd.trace_id` and `dd.span_id`

### **2. Trace Logs Tab**
- Each trace shows a "Logs" tab with all related log entries
- Chronological view of logs within the trace timeline
- Filter logs by severity level within the trace

### **3. Service Map Integration**
- Logs from each service in your map
- Cross-service log correlation
- End-to-end request visibility

## 🔍 Debugging Workflows

### **Scenario 1: Error Investigation**
1. **Find the error**: Filter logs by `@levelname:ERROR`
2. **Get trace context**: Click the trace icon on the error log
3. **Analyze the trace**: See what led to the error
4. **Review all logs**: Check the trace's logs tab for full context

### **Scenario 2: Performance Issues**
1. **Identify slow trace**: Sort traces by duration
2. **View trace logs**: See detailed logging throughout the request
3. **Find bottleneck**: Correlate timing with log messages
4. **Optimize**: Target the specific slow operations

### **Scenario 3: User Session Analysis**
1. **Filter by session**: `session_id:abc123`
2. **View trace timeline**: See all user interactions
3. **Analyze patterns**: Understand user behavior and bot responses

## 🚨 Best Practices

### **1. Structured Logging**
```python
# Good: Structured data
logger.bind(
    participant_count=3,
    room_id=room_url.split("/")[-1],
    bot_state="active"
).info("Room state updated")

# Avoid: Unstructured messages
logger.info(f"Room has {participant_count} participants")
```

### **2. Consistent Field Names**
```python
# Use consistent field names across your application
logger.bind(participant_id=pid).info("Event 1")
logger.bind(participant_id=pid).info("Event 2")  # Same field name
```

### **3. Log Levels**
```python
logger.debug("Detailed debugging info")    # Development only
logger.info("Normal operation events")     # Production info
logger.warning("Unusual but handled")      # Potential issues
logger.error("Errors that need attention") # Immediate attention
```

### **4. Sensitive Data**
```python
# Don't log sensitive information
logger.bind(
    user_id=user_id,          # ✅ OK - anonymized ID
    # password=password,      # ❌ Never log passwords
    # api_key=api_key,        # ❌ Never log API keys
).info("User authenticated")
```

## 🎮 Query Examples

### **Basic Queries**
```
# All logs with trace context
service:pipecat-chatbot dd.trace_id:*

# Errors with traces
service:pipecat-chatbot @levelname:ERROR dd.trace_id:*

# Specific session logs
service:pipecat-chatbot @session_id:abc123
```

### **Advanced Queries**
```
# Slow operations (if you log duration)
service:pipecat-chatbot @duration_ms:>2000

# Participant-specific issues
service:pipecat-chatbot @participant_id:xyz789 @levelname:ERROR

# Function-specific errors
service:pipecat-chatbot @function:process_frame @levelname:ERROR
```

## 🔧 Configuration Options

### **Environment Variables**
Add these to your `.env` for enhanced correlation:

```bash
# Improve trace-log correlation
DD_LOGS_INJECTION=true
DD_TRACE_ANALYTICS_ENABLED=true
DD_TRACE_SAMPLE_RATE=1.0
```

### **Log Sampling** (for high-volume production)
```python
# In your datadog_format function, add sampling logic
import random

def datadog_format(record):
    # Sample 10% of debug logs, 100% of others
    if record["level"].name == "DEBUG" and random.random() > 0.1:
        return None
    
    # Your existing format logic...
```

## 🎯 Monitoring & Alerting

### **Log-Based Alerts**
```
# High error rate in traces
count(last_1h):service:pipecat-chatbot @levelname:ERROR dd.trace_id:* > 10

# Missing trace context (potential issue)
count(last_5m):service:pipecat-chatbot -dd.trace_id:* > 100
```

### **Custom Dashboards**
Create widgets showing:
- Error rate by trace
- Average logs per trace
- Most frequent error patterns
- Session duration metrics

Your logging system now provides complete observability with automatic trace correlation! 🎉
