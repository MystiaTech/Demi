#!/bin/bash
# Download Piper TTS voices for Demi
# 
# This script downloads recommended Piper voice models optimized for RTX 3060.
# Voices are stored in ~/.demi/voices/piper/
#
# Usage:
#   ./scripts/download_piper_voices.sh [voice_id]
#   ./scripts/download_piper_voices.sh all
#   ./scripts/download_piper_voices.sh en_US-lessac-medium

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VOICES_DIR="${HOME}/.demi/voices/piper"
PIPER_REPO="https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"

# Voice registry - maps voice IDs to their URLs
# Format: "voice_id|model_url|config_url|description"
VOICES=(
    "en_US-lessac-medium|${PIPER_REPO}/en/en_US/lessac/medium/en_US-lessac-medium.onnx|${PIPER_REPO}/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json|Lessac (Medium) - Female, Good quality, ~100MB - RECOMMENDED"
    "en_US-ryan-high|${PIPER_REPO}/en/en_US/ryan/high/en_US-ryan-high.onnx|${PIPER_REPO}/en/en_US/ryan/high/en_US-ryan-high.onnx.json|Ryan (High) - Male, High quality, ~300MB"
    "en_US-libritts-high|${PIPER_REPO}/en/en_US/libritts/high/en_US-libritts-high.onnx|${PIPER_REPO}/en/en_US/libritts/high/en_US-libritts-high.onnx.json|LibriTTS (High) - Female, High quality, Multi-speaker, ~300MB"
)

print_usage() {
    echo "Usage: $0 [voice_id|all]"
    echo ""
    echo "Available voices:"
    for voice_info in "${VOICES[@]}"; do
        IFS='|' read -r voice_id _ _ description <<< "$voice_info"
        echo "  - ${voice_id}: ${description}"
    done
    echo ""
    echo "Examples:"
    echo "  $0 all                      # Download all recommended voices"
    echo "  $0 en_US-lessac-medium      # Download specific voice"
}

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  Demi Piper TTS Voice Downloader${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

check_dependencies() {
    # Check for curl or wget
    if command -v curl &> /dev/null; then
        DOWNLOADER="curl"
    elif command -v wget &> /dev/null; then
        DOWNLOADER="wget"
    else
        echo -e "${RED}Error: Neither curl nor wget is installed.${NC}"
        echo "Please install curl or wget to download voices."
        exit 1
    fi
    
    echo -e "${GREEN}✓ Using downloader: ${DOWNLOADER}${NC}"
}

download_file() {
    local url="$1"
    local dest="$2"
    local desc="$3"
    
    if [ -f "$dest" ]; then
        echo -e "${YELLOW}  Already exists: $(basename "$dest")${NC}"
        return 0
    fi
    
    echo -e "${BLUE}  Downloading: ${desc}...${NC}"
    
    if [ "$DOWNLOADER" = "curl" ]; then
        curl -L --progress-bar -o "$dest" "$url" || {
            echo -e "${RED}  Failed to download: ${desc}${NC}"
            rm -f "$dest"
            return 1
        }
    else
        wget --progress=bar:force -O "$dest" "$url" || {
            echo -e "${RED}  Failed to download: ${desc}${NC}"
            rm -f "$dest"
            return 1
        }
    fi
    
    echo -e "${GREEN}  ✓ Downloaded: $(basename "$dest")${NC}"
    return 0
}

download_voice() {
    local voice_id="$1"
    local found=false
    
    for voice_info in "${VOICES[@]}"; do
        IFS='|' read -r vid model_url config_url description <<< "$voice_info"
        
        if [ "$vid" = "$voice_id" ]; then
            found=true
            echo ""
            echo -e "${BLUE}Downloading: ${description}${NC}"
            echo "  Voice ID: ${voice_id}"
            
            # Download model
            model_path="${VOICES_DIR}/${voice_id}.onnx"
            download_file "$model_url" "$model_path" "model file"
            
            # Download config
            config_path="${VOICES_DIR}/${voice_id}.onnx.json"
            download_file "$config_url" "$config_path" "config file"
            
            echo -e "${GREEN}✓ Successfully installed: ${voice_id}${NC}"
            break
        fi
    done
    
    if [ "$found" = false ]; then
        echo -e "${RED}Error: Unknown voice '${voice_id}'${NC}"
        echo "Run '$0' without arguments to see available voices."
        return 1
    fi
    
    return 0
}

download_all_voices() {
    echo ""
    echo -e "${BLUE}Downloading all recommended voices...${NC}"
    
    for voice_info in "${VOICES[@]}"; do
        IFS='|' read -r voice_id _ _ _ <<< "$voice_info"
        download_voice "$voice_id" || {
            echo -e "${YELLOW}Warning: Failed to download ${voice_id}, continuing...${NC}"
        }
    done
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Voice download complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
}

show_voice_info() {
    echo ""
    echo -e "${BLUE}Installed Voices:${NC}"
    echo "-------------------"
    
    local found_any=false
    for voice_info in "${VOICES[@]}"; do
        IFS='|' read -r voice_id _ _ description <<< "$voice_info"
        model_path="${VOICES_DIR}/${voice_id}.onnx"
        
        if [ -f "$model_path" ]; then
            size=$(du -h "$model_path" 2>/dev/null | cut -f1)
            echo -e "  ${GREEN}✓${NC} ${voice_id} (${size}) - ${description}"
            found_any=true
        else
            echo -e "  ${RED}✗${NC} ${voice_id} - ${description}"
        fi
    done
    
    if [ "$found_any" = false ]; then
        echo "  No voices installed yet."
    fi
    echo ""
    echo "Voice storage location: ${VOICES_DIR}"
}

main() {
    print_header
    
    # Create voices directory
    mkdir -p "$VOICES_DIR"
    
    # Check dependencies
    check_dependencies
    
    # Parse arguments
    if [ $# -eq 0 ]; then
        # No arguments - show usage and available voices
        print_usage
        echo ""
        show_voice_info
        exit 0
    fi
    
    case "$1" in
        all)
            download_all_voices
            show_voice_info
            ;;
        -h|--help|help)
            print_usage
            exit 0
            ;;
        *)
            download_voice "$1"
            echo ""
            show_voice_info
            ;;
    esac
}

# Run main function
main "$@"
