#!/bin/bash
# Fix ElasticSearch disk space issues
# This script removes read-only blocks and fixes unassigned shards

ES_HOST="localhost"
ES_PORT="9200"
ES_USER="elastic"
ES_PASSWORD="P@ssw0rd"
ES_URL="https://${ES_HOST}:${ES_PORT}"

echo "=========================================="
echo "ElasticSearch Disk Space Fix Script"
echo "=========================================="
echo ""

# Step 1: Check cluster health
echo "Step 1: Checking cluster health..."
HEALTH=$(curl -k -s -u "${ES_USER}:${ES_PASSWORD}" "${ES_URL}/_cluster/health" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))")
echo "Cluster status: $HEALTH"
echo ""

# Step 2: Remove read-only blocks from all indices
echo "Step 2: Removing read-only blocks from all indices..."
RESULT=$(curl -k -s -X PUT -u "${ES_USER}:${ES_PASSWORD}" \
  "${ES_URL}/_all/_settings" \
  -H 'Content-Type: application/json' \
  -d '{"index.blocks.read_only_allow_delete": null}')

if echo "$RESULT" | grep -q "acknowledged.*true"; then
    echo "✅ Read-only blocks removed successfully"
else
    echo "⚠️  Warning: May have failed to remove blocks. Response: $RESULT"
fi
echo ""

# Step 3: Try to allocate unassigned shards
echo "Step 3: Attempting to allocate unassigned shards..."
REROUTE=$(curl -k -s -X POST -u "${ES_USER}:${ES_PASSWORD}" \
  "${ES_URL}/_cluster/reroute?retry_failed=true")

if echo "$REROUTE" | grep -q "acknowledged.*true"; then
    echo "✅ Shard allocation attempted"
else
    echo "⚠️  Warning: Shard allocation may have failed"
fi
echo ""

# Step 4: Check disk usage
echo "Step 4: Checking disk usage..."
df -h | grep -E 'Filesystem|/$|elasticsearch' | head -5
echo ""

# Step 5: Final health check
echo "Step 5: Final cluster health check..."
sleep 2
FINAL_HEALTH=$(curl -k -s -u "${ES_USER}:${ES_PASSWORD}" "${ES_URL}/_cluster/health" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"Status: {d.get('status', 'unknown')}, Active Shards: {d.get('active_shards', 0)}, Unassigned: {d.get('unassigned_shards', 0)}\")")
echo "$FINAL_HEALTH"
echo ""

echo "=========================================="
echo "Fix script complete!"
echo "=========================================="
echo ""
echo "If cluster is still RED:"
echo "1. Free up disk space (see df -h output above)"
echo "2. Restart ElasticSearch"
echo "3. Run this script again"
echo ""

