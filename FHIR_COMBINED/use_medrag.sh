#!/bin/bash
curl -s -X POST http://localhost:8001/chat-agent/compare/set-mode \
  -H 'Content-Type: application/json' \
  -d '{"use_medrag": true}' \
  | python3 -c "import json,sys; r=json.load(sys.stdin); print(f'✅ Now running: {r[\"pipeline_mode\"]}')"
