#!/bin/bash
#
# Demi Quick Install Script
# Automates the installation of Demi AI Companion
# 
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/yourusername/demi/main/docs/deployment/quick-install.sh | bash
#   
# Options:
#   --install-dir DIR    Install to specific directory (default: ~/demi)
#   --skip-discord       Skip Discord configuration
#   --model MODEL        Specify Ollama model (default: llama3.2:1b)
#   --dry-run            Check requirements without installing
#   --help               Show this help message

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
INSTALL_DIR="${INSTALL_DIR:-$HOME/demi}"
SKIP_DISCORD=false
MODEL="llama3.2:1b"
DRY_RUN=false
REPO_URL="https://github.com/yourusername/demi.git"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --install-dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --skip-discord)
            SKIP_DISCORD=true
            shift
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            echo "Demi Quick Install Script"
            echo ""
            echo "Usage:"
            echo "  curl -fsSL ... | bash"
            echo "  curl -fsSL ... | bash -s -- [options]"
            echo ""
            echo "Options:"
            echo "  --install-dir DIR    Install to specific directory (default: ~/demi)"
            echo "  --skip-discord       Skip Discord configuration"
            echo "  --model MODEL        Specify Ollama model (default: llama3.2:1b)"
            echo "  --dry-run            Check requirements without installing"
            echo "  --help               Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python version
check_python() {
    log_info "Checking Python version..."
    
    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
        PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
        
        if [[ "$PYTHON_MAJOR" -ge 3 && "$PYTHON_MINOR" -ge 10 ]]; then
            log_success "Python $PYTHON_VERSION found (>= 3.10)"
            return 0
        else
            log_error "Python $PYTHON_VERSION found, but 3.10+ required"
            return 1
        fi
    else
        log_error "Python 3 not found"
        return 1
    fi
}

# Check available RAM
check_ram() {
    log_info "Checking available RAM..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        AVAILABLE_RAM=$(free -m | awk '/^Mem:/{print $7}')
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        AVAILABLE_RAM=$(vm_stat | grep "Pages free" | awk '{print $3}' | sed 's/\.//' | awk '{print int($1*4096/1024/1024)}')
    else
        log_warn "Could not determine RAM on this OS"
        return 0
    fi
    
    if [[ $AVAILABLE_RAM -lt 6144 ]]; then
        log_warn "Available RAM is ${AVAILABLE_RAM}MB. 8GB+ recommended"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        log_success "Available RAM: ${AVAILABLE_RAM}MB"
    fi
}

# Check disk space
check_disk() {
    log_info "Checking disk space..."
    
    if command_exists df; then
        AVAILABLE_GB=$(df -BG "$HOME" | awk 'NR==2 {print $4}' | sed 's/G//')
        
        if [[ $AVAILABLE_GB -lt 10 ]]; then
            log_warn "Only ${AVAILABLE_GB}GB free. 10GB+ recommended"
            read -p "Continue anyway? (y/N) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        else
            log_success "Available disk: ${AVAILABLE_GB}GB"
        fi
    fi
}

# Install system dependencies
install_system_deps() {
    log_info "Installing system dependencies..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Debian/Ubuntu
        if command_exists apt-get; then
            log_info "Updating package list..."
            sudo apt-get update
            
            log_info "Installing packages..."
            sudo apt-get install -y python3 python3-pip python3-venv python3-dev ffmpeg espeak git curl
        # Fedora
        elif command_exists dnf; then
            sudo dnf install -y python3 python3-pip python3-devel ffmpeg espeak git curl
        # Arch
        elif command_exists pacman; then
            sudo pacman -S --needed python python-pip ffmpeg espeak git curl
        else
            log_warn "Unknown package manager. Please install manually:"
            log_warn "  - Python 3.10+"
            log_warn "  - FFmpeg"
            log_warn "  - espeak"
            log_warn "  - Git"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        if command_exists brew; then
            brew install python ffmpeg espeak git opus
        else
            log_warn "Homebrew not found. Please install: https://brew.sh"
            log_warn "Then run: brew install python ffmpeg espeak git opus"
        fi
    else
        log_warn "Unknown OS. Please install dependencies manually."
    fi
}

# Install Ollama
install_ollama() {
    log_info "Checking Ollama..."
    
    if command_exists ollama; then
        log_success "Ollama already installed"
        return 0
    fi
    
    log_info "Installing Ollama..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        curl -fsSL https://ollama.com/install.sh | sh
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        if command_exists brew; then
            brew install ollama
        else
            log_error "Please install Ollama manually from https://ollama.ai"
            exit 1
        fi
    else
        log_error "Please install Ollama manually from https://ollama.ai"
        exit 1
    fi
    
    log_success "Ollama installed"
}

# Pull Ollama model
pull_model() {
    log_info "Pulling Ollama model: $MODEL"
    
    # Start Ollama in background if not running
    if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        log_info "Starting Ollama server..."
        ollama serve &
        OLLAMA_PID=$!
        sleep 5
    fi
    
    ollama pull "$MODEL"
    log_success "Model $MODEL pulled successfully"
    
    # Kill background Ollama if we started it
    if [[ -n "$OLLAMA_PID" ]]; then
        kill $OLLAMA_PID 2>/dev/null || true
    fi
}

# Clone repository
clone_repo() {
    log_info "Cloning Demi repository..."
    
    if [[ -d "$INSTALL_DIR" ]]; then
        log_warn "Directory $INSTALL_DIR already exists"
        read -p "Remove and re-clone? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$INSTALL_DIR"
        else
            log_info "Using existing directory"
            return 0
        fi
    fi
    
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    log_success "Repository cloned to $INSTALL_DIR"
}

# Setup Python virtual environment
setup_venv() {
    log_info "Setting up Python virtual environment..."
    
    cd "$INSTALL_DIR"
    python3 -m venv venv
    source venv/bin/activate
    
    log_info "Upgrading pip..."
    pip install --upgrade pip
    
    log_info "Installing Python dependencies..."
    pip install -r requirements.txt
    
    log_success "Virtual environment set up"
}

# Generate secrets
generate_secrets() {
    log_info "Generating secure secrets..."
    
    JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    JWT_REFRESH_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    
    log_success "Secrets generated"
}

# Create environment file
create_env() {
    log_info "Creating environment configuration..."
    
    cd "$INSTALL_DIR"
    
    if [[ -f ".env" ]]; then
        log_warn ".env file already exists"
        read -p "Overwrite? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return 0
        fi
        cp .env .env.backup.$(date +%Y%m%d)
    fi
    
    # Create .env from example
    cp .env.example .env
    
    # Update with generated secrets
    sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$JWT_SECRET/" .env
    sed -i "s/JWT_REFRESH_SECRET_KEY=.*/JWT_REFRESH_SECRET_KEY=$JWT_REFRESH_SECRET/" .env
    
    # Update database path
    sed -i "s|DEMI_DB_PATH=.*|DEMI_DB_PATH=$HOME/.demi/emotions.db|" .env
    sed -i "s|DATABASE_URL=.*|DATABASE_URL=sqlite:///$HOME/.demi/demi.db|" .env
    
    log_success ".env file created"
}

# Setup Discord configuration
setup_discord() {
    if [[ "$SKIP_DISCORD" == true ]]; then
        log_info "Skipping Discord configuration (--skip-discord)"
        return 0
    fi
    
    echo ""
    log_info "═══════════════════════════════════════════════════════════"
    log_info "Discord Bot Configuration (Optional)"
    log_info "═══════════════════════════════════════════════════════════"
    echo ""
    
    echo "To enable Discord integration:"
    echo "  1. Go to https://discord.com/developers/applications"
    echo "  2. Click 'New Application' and name it 'Demi'"
    echo "  3. Go to 'Bot' section and click 'Add Bot'"
    echo "  4. Copy the token (you'll paste it below)"
    echo "  5. Enable 'Message Content Intent' in the Bot section"
    echo "  6. Go to 'OAuth2' → 'URL Generator'"
    echo "     - Select scopes: bot, applications.commands"
    echo "     - Select permissions: Send Messages, Read Messages"
    echo "  7. Use the generated URL to invite the bot to your server"
    echo ""
    
    read -p "Do you want to configure Discord now? (y/N) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter Discord Bot Token: " DISCORD_TOKEN
        if [[ -n "$DISCORD_TOKEN" ]]; then
            sed -i "s/DISCORD_BOT_TOKEN=.*/DISCORD_BOT_TOKEN=$DISCORD_TOKEN/" .env
            log_success "Discord token configured"
        fi
        
        read -p "Enter Ramble Channel ID (optional): " CHANNEL_ID
        if [[ -n "$CHANNEL_ID" ]]; then
            sed -i "s/DISCORD_RAMBLE_CHANNEL_ID=.*/DISCORD_RAMBLE_CHANNEL_ID=$CHANNEL_ID/" .env
            log_success "Channel ID configured"
        fi
    fi
}

# Create data directory
setup_data_dir() {
    log_info "Creating data directory..."
    
    mkdir -p "$HOME/.demi"
    chmod 755 "$HOME/.demi"
    
    log_success "Data directory created at $HOME/.demi"
}

# Create systemd service
setup_systemd() {
    if [[ "$OSTYPE" != "linux-gnu"* ]]; then
        return 0
    fi
    
    if ! command_exists systemctl; then
        return 0
    fi
    
    echo ""
    read -p "Set up systemd service for auto-start? (y/N) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Creating systemd service..."
        
        SERVICE_FILE="/etc/systemd/system/demi.service"
        
        sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Demi AI Companion
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment=PATH=$INSTALL_DIR/venv/bin
ExecStart=$INSTALL_DIR/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

        sudo systemctl daemon-reload
        sudo systemctl enable demi
        
        log_success "Systemd service created"
        log_info "Start with: sudo systemctl start demi"
        log_info "Check status: sudo systemctl status demi"
    fi
}

# Run verification tests
verify_installation() {
    log_info "Verifying installation..."
    
    cd "$INSTALL_DIR"
    source venv/bin/activate
    
    # Check Python can import key modules
    python3 -c "import fastapi, discord, sqlalchemy" 2>/dev/null
    if [[ $? -eq 0 ]]; then
        log_success "Python dependencies verified"
    else
        log_warn "Some Python dependencies may be missing"
    fi
    
    # Check configuration
    python3 main.py --dry-run 2>/dev/null
    if [[ $? -eq 0 ]]; then
        log_success "Configuration validated"
    else
        log_warn "Configuration validation failed - you may need to edit .env"
    fi
}

# Print completion message
print_completion() {
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    log_success "Demi installation complete! 🎉"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo "Installation directory: $INSTALL_DIR"
    echo "Data directory: $HOME/.demi"
    echo ""
    echo "Quick start:"
    echo "  cd $INSTALL_DIR"
    echo "  source venv/bin/activate"
    echo ""
    echo "Before starting Demi:"
    echo "  1. Start Ollama: ollama serve"
    echo "  2. Review config: nano .env"
    echo ""
    echo "To start Demi:"
    echo "  python main.py"
    echo ""
    echo "To check status:"
    echo "  curl http://localhost:8000/api/v1/status"
    echo ""
    echo "Documentation:"
    echo "  - First Run Guide: docs/deployment/first-run.md"
    echo "  - User Guide: docs/user-guide/"
    echo "  - API Docs: docs/api/"
    echo ""
    
    if [[ "$SKIP_DISCORD" != true ]]; then
        echo "Discord Setup:"
        echo "  If you haven't configured Discord yet, edit .env and add:"
        echo "    DISCORD_BOT_TOKEN=your-token"
        echo "    DISCORD_RAMBLE_CHANNEL_ID=your-channel-id"
        echo ""
    fi
    
    echo "═══════════════════════════════════════════════════════════"
}

# Main installation flow
main() {
    echo "═══════════════════════════════════════════════════════════"
    echo "           Demi AI Companion - Quick Installer"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    
    if [[ "$DRY_RUN" == true ]]; then
        log_info "DRY RUN MODE - Checking requirements only"
        check_python
        check_ram
        check_disk
        log_success "All requirements met!"
        exit 0
    fi
    
    # Pre-flight checks
    log_info "Starting pre-flight checks..."
    check_python || exit 1
    check_ram
    check_disk
    
    echo ""
    log_info "Installation will proceed to: $INSTALL_DIR"
    read -p "Continue? (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]] && [[ -n $REPLY ]]; then
        log_info "Installation cancelled"
        exit 0
    fi
    
    # Installation steps
    install_system_deps
    install_ollama
    pull_model
    clone_repo
    setup_venv
    generate_secrets
    create_env
    setup_data_dir
    setup_discord
    verify_installation
    setup_systemd
    
    # Print completion
    print_completion
}

# Run main function
main
