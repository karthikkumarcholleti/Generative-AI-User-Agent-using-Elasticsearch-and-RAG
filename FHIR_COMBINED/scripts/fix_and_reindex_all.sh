#!/bin/bash
# Complete fix and reindex script
# This will restart ElasticSearch and reindex all data

ES_DIR="/home/kchollet/LLM_UA/fhir_karthik/FHIR_COMBINED/elasticsearch-8.14.0"
BACKEND_DIR="/home/kchollet/LLM_UA/fhir_karthik/FHIR_COMBINED/FHIR_LLM_UA/backend"
ES_URL="https://localhost:9200"
ES_USER="elastic"
ES_PASSWORD="P@ssw0rd"

echo "=========================================="
echo "COMPLETE SYSTEM FIX AND REINDEX"
echo "=========================================="
echo ""

# Step 1: Stop ElasticSearch
echo "Step 1: Stopping ElasticSearch..."
pkill -f elasticsearch
sleep 5
echo "✅ ElasticSearch stopped"
echo ""

# Step 2: Start ElasticSearch
echo "Step 2: Starting ElasticSearch with new configuration..."
cd "$ES_DIR"
nohup ./bin/elasticsearch > /dev/null 2>&1 &
ES_PID=$!
echo "✅ ElasticSearch started (PID: $ES_PID)"
echo "   Waiting for cluster to be ready..."
echo ""

# Step 3: Wait for ElasticSearch to be ready
echo "Step 3: Waiting for ElasticSearch cluster to be ready..."
MAX_WAIT=120
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    HEALTH=$(curl -k -s -u "${ES_USER}:${ES_PASSWORD}" "${ES_URL}/_cluster/health" 2>/dev/null | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null)
    
    if [ "$HEALTH" = "green" ] || [ "$HEALTH" = "yellow" ]; then
        echo "✅ Cluster is ready (status: $HEALTH)"
        break
    fi
    
    if [ $WAITED -eq 0 ]; then
        echo -n "   Waiting"
    fi
    echo -n "."
    sleep 2
    WAITED=$((WAITED + 2))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo ""
    echo "⚠️  Warning: ElasticSearch may not be fully ready, but continuing..."
else
    echo ""
fi
echo ""

# Step 4: Remove read-only blocks
echo "Step 4: Removing read-only blocks..."
curl -k -s -X PUT -u "${ES_USER}:${ES_PASSWORD}" \
  "${ES_URL}/_all/_settings" \
  -H 'Content-Type: application/json' \
  -d '{"index.blocks.read_only_allow_delete": null}' > /dev/null
echo "✅ Read-only blocks removed"
echo ""

# Step 5: Check cluster health
echo "Step 5: Checking cluster health..."
HEALTH=$(curl -k -s -u "${ES_USER}:${ES_PASSWORD}" "${ES_URL}/_cluster/health" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"Status: {d.get('status')}, Active: {d.get('active_shards')}, Unassigned: {d.get('unassigned_shards')}\")" 2>/dev/null)
echo "$HEALTH"
echo ""

# Step 6: Reindex all data
echo "Step 6: Starting reindexing process..."
echo "   This will index all patients with embeddings"
echo "   This may take 30-60 minutes..."
echo ""
cd "$BACKEND_DIR"
python3 scripts/reindex_with_embeddings.py

REINDEX_EXIT=$?
if [ $REINDEX_EXIT -eq 0 ]; then
    echo ""
    echo "✅ Reindexing completed successfully!"
else
    echo ""
    echo "⚠️  Reindexing may have had issues (exit code: $REINDEX_EXIT)"
fi
echo ""

# Step 7: Final verification
echo "Step 7: Final system verification..."
echo ""
echo "Cluster Health:"
curl -k -s -u "${ES_USER}:${ES_PASSWORD}" "${ES_URL}/_cluster/health" | python3 -m json.tool 2>/dev/null | grep -E '"status"|"active_shards"|"unassigned_shards"' | head -3
echo ""

echo "Index Status:"
curl -k -s -u "${ES_USER}:${ES_PASSWORD}" "${ES_URL}/_cat/indices/patient_data?v" 2>/dev/null
echo ""

echo "=========================================="
echo "SYSTEM FIX COMPLETE!"
echo "=========================================="
echo ""
echo "Next: Test the system with:"
echo "  cd $BACKEND_DIR"
echo "  python3 scripts/test_comprehensive_queries.py"
echo ""

