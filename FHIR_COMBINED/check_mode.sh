#!/bin/bash
curl -s http://localhost:8001/chat-agent/compare/current-mode \
  | python3 -c "import json,sys; r=json.load(sys.stdin); print(f'🔍 Current mode: {r[\"pipeline_mode\"]}')"
