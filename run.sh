#!/bin/bash

# cURL command to unified server to dialout to +886979118474
# Works with both local and cloud modes

# Daily example response
# {
#     "From": "sip:jameshush@sip.linphone.org",
#     "To": "sip:236fed48c3a13d39--1749708775591@daily-236fed48c3a13d39-pinless-sip.dapp.signalwire.com",
#     "callId": "80305750-70e0-41d3-ba3a-65341d877f21",
#     "callDomain": "11819ca6-14ed-42ce-b33b-fbd050a43597",
#     "sipHeaders": {}
# }

echo "Testing unified server dialout to +886979118474..."
echo "Server mode: ${SERVER_MODE:-local}"
echo ""

curl -X POST http://localhost:7860/start \
  -H "Content-Type: application/json" \
  -d '{
    "From": "+15551234567",
    "To": "+886979118474",
    "callId": "test-dialout-call-'"$(date +%s)"'",
    "callDomain": "test-domain",
    "dialout_settings": [
      {
        "phoneNumber": "+886979118474",
        "callerId": "+15551234567"
      }
    ]
  }'

echo ""
echo "Request completed. Check server logs for details."
