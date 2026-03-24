#!/bin/bash
# Elasticsearch Setup Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "Elasticsearch Setup"
echo "=========================================="
echo ""

# Check if Elasticsearch already exists
if [ -d "elasticsearch-8.14.0" ]; then
    echo "✅ Elasticsearch directory already exists: elasticsearch-8.14.0"
    echo "   Skipping download/extraction"
else
    # Check if tar.gz file exists
    if [ -f "elasticsearch-8.14.0-linux-x86_64.tar.gz" ]; then
        echo "✅ Found Elasticsearch archive: elasticsearch-8.14.0-linux-x86_64.tar.gz"
        echo "   Extracting..."
        tar -xzf elasticsearch-8.14.0-linux-x86_64.tar.gz
        echo "✅ Extraction complete"
    else
        echo "❌ Elasticsearch archive not found"
        echo "   Please download: elasticsearch-8.14.0-linux-x86_64.tar.gz"
        echo "   Or run: wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-8.14.0-linux-x86_64.tar.gz"
        exit 1
    fi
fi

# Check Java
echo ""
echo "Checking Java installation..."
if ! command -v java &> /dev/null; then
    echo "❌ Java not found. Elasticsearch requires Java 17+"
    echo "   Please install Java: sudo yum install java-17-openjdk (or equivalent)"
    exit 1
fi

JAVA_VERSION=$(java -version 2>&1 | head -1 | cut -d'"' -f2 | sed '/^1\./s///' | cut -d'.' -f1)
if [ "$JAVA_VERSION" -lt 17 ]; then
    echo "❌ Java version $JAVA_VERSION found. Elasticsearch requires Java 17+"
    exit 1
fi
echo "✅ Java $JAVA_VERSION found"

# Configure Elasticsearch (disable security for development)
ES_DIR="elasticsearch-8.14.0"
ES_CONFIG="$ES_DIR/config/elasticsearch.yml"

if [ -f "$ES_CONFIG" ]; then
    echo ""
    echo "Configuring Elasticsearch..."
    
    # Backup original config
    if [ ! -f "$ES_CONFIG.original" ]; then
        cp "$ES_CONFIG" "$ES_CONFIG.original"
    fi
    
    # Disable security for development
    if ! grep -q "xpack.security.enabled" "$ES_CONFIG"; then
        echo "" >> "$ES_CONFIG"
        echo "# Development settings - disable security" >> "$ES_CONFIG"
        echo "xpack.security.enabled: false" >> "$ES_CONFIG"
        echo "xpack.security.enrollment.enabled: false" >> "$ES_CONFIG"
        echo "✅ Security disabled for development"
    else
        echo "✅ Security already configured"
    fi
    
    # Set network host
    if ! grep -q "network.host" "$ES_CONFIG"; then
        echo "network.host: 0.0.0.0" >> "$ES_CONFIG"
        echo "✅ Network host configured"
    fi
fi

# Create data directory if needed
if [ ! -d "$ES_DIR/data" ]; then
    mkdir -p "$ES_DIR/data"
    echo "✅ Created data directory"
fi

echo ""
echo "=========================================="
echo "✅ Elasticsearch Setup Complete!"
echo "=========================================="
echo ""
echo "To start Elasticsearch:"
echo "  cd $ES_DIR"
echo "  ./bin/elasticsearch"
echo ""
echo "Or run in background:"
echo "  cd $ES_DIR"
echo "  ./bin/elasticsearch -d"
echo ""
echo "Verify it's running:"
echo "  curl http://localhost:9200"
echo ""


