#!/bin/bash
#
# Memory profiling script for Demi
# Runs memory profiling and generates reports
#

set -e

# Default configuration
DEFAULT_DURATION=60
DEFAULT_INTERVAL=30
OUTPUT_DIR="${HOME}/.demi/memory_profiles"
PIDFILE="${OUTPUT_DIR}/memory_profile.pid"

# Parse arguments
DURATION_MINUTES=$DEFAULT_DURATION
SAMPLE_INTERVAL=$DEFAULT_INTERVAL
COMMAND="run"

while [[ $# -gt 0 ]]; do
    case $1 in
        --duration)
            DURATION_MINUTES="$2"
            shift 2
            ;;
        --interval)
            SAMPLE_INTERVAL="$2"
            shift 2
            ;;
        --report)
            COMMAND="report"
            shift
            ;;
        --format)
            REPORT_FORMAT="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS] [COMMAND]"
            echo ""
            echo "Commands:"
            echo "  run               Run memory profiling (default)"
            echo "  report            Generate report from latest profile"
            echo ""
            echo "Options:"
            echo "  --duration N      Profile duration in minutes (default: 60)"
            echo "  --interval N      Sample interval in seconds (default: 30)"
            echo "  --format TYPE     Report format: text, html, json (default: text)"
            echo "  --help, -h        Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                           # Profile for 60 minutes, 30s intervals"
            echo "  $0 --duration 120            # Profile for 2 hours"
            echo "  $0 --duration 3600 --interval 60  # Profile for 1 hour, 60s intervals"
            echo "  $0 report                    # Generate text report"
            echo "  $0 report --format html      # Generate HTML report"
            exit 0
            ;;
        run|report)
            COMMAND="$1"
            shift
            ;;
        *)
            # Try to interpret as duration if numeric
            if [[ "$1" =~ ^[0-9]+$ ]]; then
                DURATION_MINUTES="$1"
            fi
            shift
            ;;
    esac
done

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

setup() {
    echo -e "${GREEN}Setting up memory profiling...${NC}"
    mkdir -p "$OUTPUT_DIR"
    
    # Check for required tools
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: python3 not found${NC}"
        exit 1
    fi
    
    # Check for psutil
    if ! python3 -c "import psutil" 2>/dev/null; then
        echo -e "${YELLOW}Warning: psutil not installed. Install with: pip install psutil${NC}"
    fi
    
    echo "Output directory: $OUTPUT_DIR"
    echo "Duration: $DURATION_MINUTES minutes"
    echo "Sample interval: $SAMPLE_INTERVAL seconds"
}

run_profiler() {
    echo -e "${GREEN}Starting memory profiler...${NC}"
    
    # Save PID for potential signal handling
    echo $$ > "$PIDFILE"
    
    python3 << EOF
import asyncio
import sys
import time
import json
import signal
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, '/home/mystiatech/projects/Demi')

try:
    from tests.profiling import MemoryProfiler, LeakDetector
except ImportError as e:
    print(f"Error importing profiling modules: {e}")
    print("Make sure you're running from the project directory")
    sys.exit(1)

# Handle signals gracefully
interrupted = False

def signal_handler(sig, frame):
    global interrupted
    interrupted = True
    print("\nReceived signal, stopping profiler...")

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

async def profile():
    profiler = MemoryProfiler(
        warning_threshold_mb=8192,   # 8GB warning
        critical_threshold_mb=10240  # 10GB critical
    )
    detector = LeakDetector(
        min_growth_threshold_mb=50,
        min_growth_percent=5,
        observation_periods=6,
        period_minutes=10,
    )
    
    profiler.start_profiling()
    detector.start_monitoring()
    
    output_dir = Path("$OUTPUT_DIR")
    duration = $DURATION_MINUTES * 60
    start_time = time.time()
    
    print(f"Profiling started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Duration: $DURATION_MINUTES minutes")
    print(f"Sample interval: $SAMPLE_INTERVAL seconds")
    print(f"Press Ctrl+C to stop early")
    print("")
    
    snapshots = []
    leak_detected_flag = False
    
    try:
        while time.time() - start_time < duration and not interrupted:
            await asyncio.sleep($SAMPLE_INTERVAL)
            
            snapshot = profiler.take_snapshot()
            detector.add_observation(snapshot)
            snapshots.append(snapshot.to_dict())
            
            # Log progress
            elapsed = time.time() - start_time
            progress = (elapsed / duration) * 100
            elapsed_str = f"{int(elapsed // 60):02d}:{int(elapsed % 60):02d}"
            remaining = max(0, duration - elapsed)
            remaining_str = f"{int(remaining // 60):02d}:{int(remaining % 60):02d}"
            
            # Check thresholds
            alerts = profiler.check_thresholds(snapshot)
            alert_indicator = ""
            if alerts:
                if "CRITICAL" in alerts[0]:
                    alert_indicator = " 🔴 CRITICAL"
                else:
                    alert_indicator = " 🟡 WARNING"
            
            print(f"[{progress:5.1f}%] {elapsed_str} elapsed, {remaining_str} remaining | "
                  f"Memory: {snapshot.rss_mb:7.1f}MB, "
                  f"Objects: {snapshot.objects_count:,}{alert_indicator}")
            
            # Check for leaks
            if detector.check_for_leaks() and not leak_detected_flag:
                leaks = detector.get_suspected_leaks()
                print(f"\\n⚠️  WARNING: Potential leak detected!")
                for leak in leaks:
                    print(f"    Growth: {leak.growth_mb:.1f}MB ({leak.growth_percent:.1f}%)")
                leak_detected_flag = True
    
    except KeyboardInterrupt:
        print("\\nProfiling interrupted by user")
    
    finally:
        profiler.stop_profiling()
        
        # Generate final report
        end_time = time.time()
        actual_duration = (end_time - start_time) / 60  # minutes
        
        # Generate growth analysis
        growth_stats = detector.calculate_growth_rate()
        
        report = {
            "start_time": datetime.fromtimestamp(start_time).isoformat(),
            "end_time": datetime.now().isoformat(),
            "duration_minutes": actual_duration,
            "sample_count": len(snapshots),
            "snapshots": snapshots,
            "leak_detected": detector.check_for_leaks(),
            "suspected_leaks": [leak.to_dict() for leak in detector.get_suspected_leaks()],
            "growth_analysis": growth_stats,
            "interrupted": interrupted,
        }
        
        # Save JSON report
        timestamp = int(start_time)
        report_file = output_dir / f"memory_profile_{timestamp}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Save HTML report
        html_report = profiler.generate_report(format="html")
        html_file = output_dir / f"memory_profile_{timestamp}.html"
        with open(html_file, 'w') as f:
            f.write(html_report)
        
        # Save text report
        text_report = profiler.generate_report(format="text")
        text_file = output_dir / f"memory_profile_{timestamp}.txt"
        with open(text_file, 'w') as f:
            f.write(text_report)
        
        print(f"\\n{'='*60}")
        print("Memory Profile Summary")
        print('='*60)
        
        if snapshots:
            initial = snapshots[0]["rss_mb"]
            final = snapshots[-1]["rss_mb"]
            max_mem = max(s['rss_mb'] for s in snapshots)
            growth = final - initial
            growth_pct = (growth / initial) * 100 if initial > 0 else 0
            
            print(f"Duration: {actual_duration:.1f} minutes")
            print(f"Samples collected: {len(snapshots)}")
            print("")
            print(f"Memory Usage:")
            print(f"  Initial: {initial:8.1f} MB")
            print(f"  Final:   {final:8.1f} MB")
            print(f"  Peak:    {max_mem:8.1f} MB")
            print(f"  Growth:  {growth:+8.1f} MB ({growth_pct:+.1f}%)")
            print("")
            print(f"Growth Rate:")
            print(f"  MB/hour: {growth_stats['growth_rate_mb_per_hour']:.2f}")
            print(f"  %%/hour:  {growth_stats['growth_percent_per_hour']:.2f}")
            print(f"  7-day projection: {growth_stats['projected_7day_growth_percent']:.1f}%")
            
            if detector.check_for_leaks():
                print("")
                print(f"⚠️  LEAK DETECTED")
                for leak in detector.get_suspected_leaks():
                    print(f"  - Growth: {leak.growth_mb:.1f}MB ({leak.growth_percent:.1f}%) "
                          f"Confidence: {leak.confidence:.0%}")
            elif growth_stats['projected_7day_growth_percent'] > 5:
                print("")
                print(f"⚠️  WARNING: High growth rate projected")
            else:
                print("")
                print(f"✓ No leaks detected")
        
        print("")
        print(f"Reports saved:")
        print(f"  JSON: {report_file}")
        print(f"  HTML: {html_file}")
        print(f"  Text: {text_file}")
        print('='*60)
        
        # Remove PID file
        pid_file = Path("$PIDFILE")
        if pid_file.exists():
            pid_file.unlink()

asyncio.run(profile())
EOF
}

generate_report() {
    echo -e "${GREEN}Generating memory report...${NC}"
    
    latest_report=$(ls -t "${OUTPUT_DIR}"/memory_profile_*.json 2>/dev/null | head -1)
    
    if [ -z "$latest_report" ]; then
        echo -e "${YELLOW}No memory profile reports found in $OUTPUT_DIR${NC}"
        return 1
    fi
    
    echo "Latest report: $latest_report"
    
    # Determine format
    FORMAT="${REPORT_FORMAT:-text}"
    
    if [ "$FORMAT" = "html" ]; then
        # Generate HTML from JSON
        html_file="${latest_report%.json}.html"
        if [ -f "$html_file" ]; then
            echo "Opening HTML report: $html_file"
            # Try to open with xdg-open if available
            if command -v xdg-open &> /dev/null; then
                xdg-open "$html_file" 2>/dev/null || echo "Report saved to: $html_file"
            else
                echo "Report saved to: $html_file"
            fi
        else
            echo -e "${YELLOW}HTML report not found${NC}"
        fi
    else
        # Display text summary
        python3 << EOF
import json
from pathlib import Path

report_file = Path("$latest_report")
with open(report_file) as f:
    report = json.load(f)

print("\\n" + "="*60)
print("Memory Profile Report")
print("="*60)
print(f"Duration: {report['duration_minutes']:.1f} minutes")
print(f"Samples: {report['sample_count']}")
print(f"Leak detected: {report['leak_detected']}")

if report['snapshots']:
    snapshots = report['snapshots']
    initial = snapshots[0]['rss_mb']
    final = snapshots[-1]['rss_mb']
    max_mem = max(s['rss_mb'] for s in snapshots)
    
    print(f"\\nMemory Usage:")
    print(f"  Initial: {initial:8.1f} MB")
    print(f"  Final:   {final:8.1f} MB")
    print(f"  Peak:    {max_mem:8.1f} MB")
    print(f"  Growth:  {final - initial:+8.1f} MB ({((final - initial) / initial) * 100:+.1f}%)")

if report.get('growth_analysis'):
    ga = report['growth_analysis']
    print(f"\\nGrowth Projection:")
    print(f"  Rate: {ga['growth_rate_mb_per_hour']:.2f} MB/hour")
    print(f"  7-day: {ga['projected_7day_growth_percent']:.1f}%")

if report['suspected_leaks']:
    print(f"\\nSuspected Leaks:")
    for leak in report['suspected_leaks']:
        print(f"  - {leak['growth_mb']:.1f}MB ({leak['growth_percent']:.1f}%) "
              f"at {leak['detected_at']}")

print("\\n" + "="*60)
EOF
    fi
}

# Command dispatcher
case "$COMMAND" in
    run)
        setup
        run_profiler
        ;;
    report)
        generate_report
        ;;
    *)
        echo "Unknown command: $COMMAND"
        echo "Use --help for usage information"
        exit 1
        ;;
esac
