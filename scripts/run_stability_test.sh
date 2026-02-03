#!/bin/bash
#
# Long-running stability test runner for Demi
# Runs 7-day (168 hour) stability test with monitoring
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DURATION_HOURS=${1:-168}  # Default: 7 days
CHECKPOINT_INTERVAL=${2:-60}  # Minutes
LOG_DIR="${HOME}/.demi/stability_logs"
CHECKPOINT_DIR="${HOME}/.demi/stability_checkpoints"
PIDFILE="${LOG_DIR}/stability_test.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Helper Functions
# ============================================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# ============================================================================
# Setup
# ============================================================================

setup() {
    log_info "Setting up stability test environment..."
    
    # Create directories
    mkdir -p "$LOG_DIR"
    mkdir -p "$CHECKPOINT_DIR"
    
    # Check Python environment
    if ! command -v python3 &> /dev/null; then
        log_error "python3 not found"
        exit 1
    fi
    
    # Verify test files exist
    if [ ! -f "$PROJECT_DIR/tests/stability/long_running.py" ]; then
        log_error "Stability test files not found at $PROJECT_DIR/tests/stability/"
        exit 1
    fi
    
    # Check if already running
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            log_warn "Stability test already running (PID: $PID)"
            echo "Use '$0 stop' to stop it first"
            exit 1
        else
            log_warn "Removing stale PID file"
            rm -f "$PIDFILE"
        fi
    fi
    
    log_info "Environment ready"
    log_info "  Log directory: $LOG_DIR"
    log_info "  Checkpoint directory: $CHECKPOINT_DIR"
    log_info "  Duration: $DURATION_HOURS hours"
    log_info "  Checkpoint interval: $CHECKPOINT_INTERVAL minutes"
}

# ============================================================================
# Start Test
# ============================================================================

start_test() {
    log_info "Starting ${DURATION_HOURS} hour stability test..."
    
    # Check for existing checkpoint
    if [ -f "${CHECKPOINT_DIR}/stability_test_checkpoint.json" ]; then
        log_warn "Existing checkpoint found - test will resume from checkpoint"
        echo ""
        cat "${CHECKPOINT_DIR}/stability_test_checkpoint.json"
        echo ""
        read -p "Continue with resume? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Starting fresh (removing old checkpoint)..."
            rm -f "${CHECKPOINT_DIR}/stability_test_checkpoint.json"
        fi
    fi
    
    # Run test with output logging
    cd "$PROJECT_DIR"
    nohup python3 -m tests.stability.long_running \
        --duration "$DURATION_HOURS" \
        --checkpoint-interval "$CHECKPOINT_INTERVAL" \
        > "${LOG_DIR}/stability_test.log" 2>&1 &
    
    PID=$!
    echo $PID > "$PIDFILE"
    
    log_info "Stability test started with PID: $PID"
    echo ""
    echo "  Monitor logs: tail -f ${LOG_DIR}/stability_test.log"
    echo "  Check status: $0 status"
    echo "  Stop test:    $0 stop"
    echo ""
    
    # Show initial log output
    sleep 2
    if [ -f "${LOG_DIR}/stability_test.log" ]; then
        tail -n 20 "${LOG_DIR}/stability_test.log"
    fi
}

# ============================================================================
# Status
# ============================================================================

status() {
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            log_info "Stability test is running (PID: $PID)"
            
            # Calculate uptime if we can
            if [ -f "${LOG_DIR}/stability_test.log" ]; then
                START_TIME=$(head -1 "${LOG_DIR}/stability_test.log" | grep -oP '\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}' || echo "")
                if [ -n "$START_TIME" ]; then
                    START_EPOCH=$(date -d "$START_TIME" +%s 2>/dev/null || echo "0")
                    if [ "$START_EPOCH" != "0" ]; then
                        NOW_EPOCH=$(date +%s)
                        UPTIME_SEC=$((NOW_EPOCH - START_EPOCH))
                        UPTIME_HOURS=$((UPTIME_SEC / 3600))
                        UPTIME_MIN=$(((UPTIME_SEC % 3600) / 60))
                        echo "  Uptime: ${UPTIME_HOURS}h ${UPTIME_MIN}m"
                    fi
                fi
            fi
            
            echo ""
            echo "Recent activity:"
            if [ -f "${LOG_DIR}/stability_test.log" ]; then
                tail -n 10 "${LOG_DIR}/stability_test.log"
            fi
            
            # Show checkpoint if exists
            if [ -f "${CHECKPOINT_DIR}/stability_test_checkpoint.json" ]; then
                echo ""
                log_info "Latest checkpoint:"
                cat "${CHECKPOINT_DIR}/stability_test_checkpoint.json" | python3 -m json.tool 2>/dev/null || cat "${CHECKPOINT_DIR}/stability_test_checkpoint.json"
            fi
        else
            log_warn "Stability test is not running (stale PID file)"
            rm -f "$PIDFILE"
            
            # Show last checkpoint if available
            if [ -f "${CHECKPOINT_DIR}/stability_test_checkpoint.json" ]; then
                log_info "Last checkpoint:"
                cat "${CHECKPOINT_DIR}/stability_test_checkpoint.json" | python3 -m json.tool 2>/dev/null || cat "${CHECKPOINT_DIR}/stability_test_checkpoint.json"
            fi
        fi
    else
        log_warn "No stability test running"
        
        # Show last checkpoint if available
        if [ -f "${CHECKPOINT_DIR}/stability_test_checkpoint.json" ]; then
            log_info "Last checkpoint (test may have completed):"
            cat "${CHECKPOINT_DIR}/stability_test_checkpoint.json" | python3 -m json.tool 2>/dev/null || cat "${CHECKPOINT_DIR}/stability_test_checkpoint.json"
        fi
    fi
}

# ============================================================================
# Stop Test
# ============================================================================

stop_test() {
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        log_warn "Stopping stability test (PID: $PID)..."
        
        # Send graceful shutdown signal
        kill "$PID" 2>/dev/null || true
        
        # Wait for graceful shutdown
        for i in {1..10}; do
            if ! ps -p "$PID" > /dev/null 2>&1; then
                log_info "Stability test stopped gracefully"
                rm -f "$PIDFILE"
                return 0
            fi
            echo -n "."
            sleep 1
        done
        echo
        
        # Force kill if still running
        log_error "Force killing stability test..."
        kill -9 "$PID" 2>/dev/null || true
        rm -f "$PIDFILE"
    else
        log_warn "No stability test running"
    fi
}

# ============================================================================
# Generate Report
# ============================================================================

report() {
    log_info "Generating stability test report..."
    
    # Check for log file
    if [ -f "${LOG_DIR}/stability_test.log" ]; then
        echo ""
        echo "=== Test Log Summary ==="
        echo "Last 100 lines:"
        tail -n 100 "${LOG_DIR}/stability_test.log"
    fi
    
    # Check for checkpoint
    if [ -f "${CHECKPOINT_DIR}/stability_test_checkpoint.json" ]; then
        echo ""
        echo "=== Final Checkpoint ==="
        cat "${CHECKPOINT_DIR}/stability_test_checkpoint.json" | python3 -m json.tool 2>/dev/null || cat "${CHECKPOINT_DIR}/stability_test_checkpoint.json"
    fi
    
    # Check for errors
    if [ -f "${LOG_DIR}/stability_test.log" ]; then
        ERROR_COUNT=$(grep -c "ERROR\|error\|Error" "${LOG_DIR}/stability_test.log" 2>/dev/null || echo 0)
        echo ""
        echo "=== Error Summary ==="
        echo "Total errors: $ERROR_COUNT"
        if [ "$ERROR_COUNT" -gt 0 ]; then
            echo "Recent errors:"
            grep -i "error" "${LOG_DIR}/stability_test.log" | tail -n 10
        fi
    fi
    
    # Generate summary
    echo ""
    echo "=== Report Complete ==="
    echo "Log file: ${LOG_DIR}/stability_test.log"
    echo "Checkpoint: ${CHECKPOINT_DIR}/stability_test_checkpoint.json"
}

# ============================================================================
# Email/Webhook Notifications
# ============================================================================

send_notification() {
    local subject="$1"
    local message="$2"
    
    # Check for webhook URL
    if [ -n "$STABILITY_WEBHOOK_URL" ]; then
        log_info "Sending webhook notification..."
        curl -s -X POST \
            -H "Content-Type: application/json" \
            -d "{\"subject\":\"$subject\",\"message\":\"$message\"}" \
            "$STABILITY_WEBHOOK_URL" > /dev/null 2>&1 || true
    fi
    
    # Check for email
    if [ -n "$STABILITY_EMAIL" ] && command -v mail &> /dev/null; then
        log_info "Sending email notification..."
        echo "$message" | mail -s "$subject" "$STABILITY_EMAIL" 2>/dev/null || true
    fi
}

notify_completion() {
    if [ -f "${CHECKPOINT_DIR}/stability_test_checkpoint.json" ]; then
        PROGRESS=$(cat "${CHECKPOINT_DIR}/stability_test_checkpoint.json" | grep -oP '"progress_percent":\s*\K[0-9.]+' || echo "N/A")
        send_notification "Demi Stability Test Update" "Progress: ${PROGRESS}%"
    fi
}

# ============================================================================
# Watch Mode
# ============================================================================

watch_mode() {
    log_info "Starting watch mode (press Ctrl+C to exit)..."
    while true; do
        clear
        status
        sleep 5
    done
}

# ============================================================================
# Cleanup
# ============================================================================

cleanup() {
    log_info "Cleaning up stability test data..."
    read -p "This will remove all logs and checkpoints. Continue? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$LOG_DIR"
        rm -rf "$CHECKPOINT_DIR"
        log_info "Cleanup complete"
    else
        log_info "Cleanup cancelled"
    fi
}

# ============================================================================
# Help
# ============================================================================

show_help() {
    cat << EOF
Demi Stability Test Runner

Usage: $0 [DURATION_HOURS] [CHECKPOINT_MINUTES] [COMMAND]

Commands:
    start       Start the stability test (default)
    stop        Stop the running test
    restart     Restart the test
    status      Check test status
    report      Generate final report
    watch       Watch mode (continuous status updates)
    cleanup     Remove all test data
    help        Show this help message

Environment Variables:
    STABILITY_WEBHOOK_URL   Webhook URL for notifications
    STABILITY_EMAIL         Email for notifications

Examples:
    $0                              # Run 7-day test (default)
    $0 24                           # Run 24-hour test
    $0 168 30 start                 # Run 7-day test with 30-min checkpoints
    $0 status                       # Check test status
    $0 stop                         # Stop running test
    $0 report                       # Generate final report
    $0 cleanup                      # Clean up test data

Requirements:
    - Python 3.8+
    - tests/stability/ module installed
    - ~/.demi/ directory writable

For more information, see:
    - tests/stability/README.md
    - .planning/phases/09-integration-testing/09-02-PLAN.md
EOF
}

# ============================================================================
# Main Command Dispatcher
# ============================================================================

# Parse arguments
CMD="${3:-start}"

# If first arg is a command, shift
if [[ "$1" =~ ^(start|stop|restart|status|report|watch|cleanup|help)$ ]]; then
    CMD="$1"
    DURATION_HOURS="${2:-168}"
    CHECKPOINT_INTERVAL="${3:-60}"
fi

case "$CMD" in
    start)
        setup
        start_test
        ;;
    status)
        status
        ;;
    stop)
        stop_test
        ;;
    restart)
        stop_test
        sleep 2
        setup
        start_test
        ;;
    report)
        report
        ;;
    watch)
        watch_mode
        ;;
    cleanup)
        cleanup
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $CMD"
        show_help
        exit 1
        ;;
esac
