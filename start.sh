#!/bin/bash

# Port definitions
FRONTEND_PORT=3890
BACKEND_PORT=8001
BROWSER_PORT=7070

echo "Cleaning up any processes on ports $FRONTEND_PORT, $BACKEND_PORT, $BROWSER_PORT..."
# Kill any existing processes using these ports
for port in $FRONTEND_PORT $BACKEND_PORT $BROWSER_PORT; do
    PIDS=$(ss -tlnp "sport = :$port" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | sort -u)
    if [ -n "$PIDS" ]; then
        echo "Killing processes on port $port: $PIDS"
        echo "$PIDS" | xargs kill -9 2>/dev/null || true
    fi
done

# Navigate to wikimaker root directory
cd /home/ubuntu/Expeei/wikimaker

# Set up EXIT trap to kill background processes on script exit
cleanup() {
    echo "Shutting down wikimaker services..."
    pkill -P $$ 2>/dev/null || true
    kill $(jobs -p) 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Start standalone browser server
echo "Starting browser server on port $BROWSER_PORT..."
python3 browser_server.py > browser_server.log 2>&1 &

# Start backend server
echo "Starting backend server on port $BACKEND_PORT..."
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port $BACKEND_PORT > backend_server.log 2>&1 &

# Wait a couple of seconds for services to start
sleep 2

# Start Vite frontend
echo "Starting Vite frontend on port $FRONTEND_PORT..."
cd frontend
npx vite --port $FRONTEND_PORT --host 0.0.0.0
