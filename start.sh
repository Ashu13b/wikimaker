#!/bin/bash

# Force headless remote browser to minimize memory footprint in container environments
export WIKIMAKER_HEADLESS=1

# Port definition
UNIFIED_PORT=3890

echo "Cleaning up any processes on port $UNIFIED_PORT (and old ports 3890, 8001, 7070)..."
for port in $UNIFIED_PORT 3890 8001 7070; do
    PIDS=$(lsof -t -i :$port 2>/dev/null)
    if [ -n "$PIDS" ]; then
        echo "Killing processes on port $port: $PIDS"
        echo "$PIDS" | xargs kill -9 2>/dev/null || true
    fi
done

# Navigate to wikimaker root directory
cd /home/ubuntu/Expeei/wikimaker

# Build the latest frontend directly with Vite
echo "Building the React frontend..."
cd frontend
npx vite build
cd ..

# Start the unified FastAPI server in the foreground with logging muted
echo "Starting unified Wikimaker server on port $UNIFIED_PORT..."
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port $UNIFIED_PORT --no-access-log --log-level warning


