#!/bin/bash
# Check for local Redis conflicts before starting development

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo "🔍 Checking for Redis conflicts..."

# Check if local Redis is running (not Docker)
LOCAL_REDIS=$(ps aux | grep "redis-server" | grep -v "docker\|grep" | head -1)

if [ -n "$LOCAL_REDIS" ]; then
    echo -e "${RED}⚠️  WARNING: Local Redis detected!${NC}"
    echo ""
    echo "A local Redis server is running, which will conflict with Docker Redis."
    echo "The API will connect to local Redis while workers use Docker Redis."
    echo ""
    echo "Process found:"
    echo "$LOCAL_REDIS"
    echo ""
    echo -e "${YELLOW}To fix this, run:${NC}"
    echo "  brew services stop redis"
    echo "  # or"
    echo "  pkill redis-server"
    echo ""
    exit 1
fi

# Check if Docker Redis is running
DOCKER_REDIS=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -E "redis|autodj.*redis")

if [ -z "$DOCKER_REDIS" ]; then
    echo -e "${YELLOW}⚠️  Docker Redis not running${NC}"
    echo ""
    echo "Start it with:"
    echo "  docker-compose -f docker-compose.dev.yml up -d redis"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ Redis configuration OK${NC}"
echo "   Docker Redis: $DOCKER_REDIS"
exit 0
