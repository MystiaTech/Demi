#!/bin/bash
#
# Start the Demi Health Dashboard
#
# Usage: ./scripts/start_dashboard.sh [--port PORT] [--host HOST]
#   Default: port=8080, host=localhost
#

set -e

# Default configuration
HOST="localhost"
PORT=8080

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--port PORT] [--host HOST]"
            echo "  --port PORT    Port to run dashboard on (default: 8080)"
            echo "  --host HOST    Host to bind to (default: localhost)"
            echo "  -h, --help     Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Starting Demi Health Dashboard${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${YELLOW}Host:${NC} $HOST"
echo -e "  ${YELLOW}Port:${NC} $PORT"
echo -e "  ${YELLOW}URL:${NC}  http://$HOST:$PORT"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 not found${NC}"
    exit 1
fi

# Check if required files exist
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [ ! -f "$PROJECT_ROOT/src/monitoring/dashboard.py" ]; then
    echo -e "${RED}Error: Dashboard module not found${NC}"
    echo "Expected: $PROJECT_ROOT/src/monitoring/dashboard.py"
    exit 1
fi

# Check if dashboard static files exist
if [ ! -f "$PROJECT_ROOT/src/monitoring/dashboard_static/index.html" ]; then
    echo -e "${YELLOW}Warning: Dashboard static files not found${NC}"
    echo "Expected: $PROJECT_ROOT/src/monitoring/dashboard_static/index.html"
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down dashboard...${NC}"
    exit 0
}

trap cleanup INT TERM

# Change to project root
cd "$PROJECT_ROOT"

# Start dashboard using Python
echo -e "${GREEN}Starting dashboard server...${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

python3 << EOF
import asyncio
import sys
sys.path.insert(0, '$PROJECT_ROOT')

from src.monitoring.dashboard import Dashboard

async def main():
    dashboard = Dashboard(
        host='$HOST',
        port=$PORT,
        update_interval=5,
        enable_alerts=True,
        enable_metrics_collection=True,
    )
    
    try:
        await dashboard.start()
    except KeyboardInterrupt:
        pass
    finally:
        await dashboard.stop()

if __name__ == "__main__":
    asyncio.run(main())
EOF
