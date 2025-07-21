# docker build --platform linux/arm64 -t axilock/axilock_plugins:trufflehog-v1.0.0 .

# docker push axilock/axilock_plugins:trufflehog-v1.0.0
# # 

#!/bin/bash

# Quick deployment script for TruffleHog plugin to Docker Hub
# Usage: ./quick_deploy.sh [version]

#!/bin/bash

# Quick deployment script for TruffleHog plugin to Docker Hub
# Usage: ./quick_deploy.sh [version]

set -e  # Exit on any error

# Configuration
DOCKER_REPO="axilock/axilock_plugins"
PLUGIN_NAME="trufflehog"
VERSION=${1:-"1.0.0"}

# Colors for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Main deployment function
deploy_plugin() {
    log_info "Starting deployment of $PLUGIN_NAME plugin v$VERSION..."
    
    # Check if Docker is running
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    
    # Check if logged in to Docker Hub
    if ! docker system info 2>/dev/null | grep -q "Username:"; then
        log_warning "Not logged in to Docker Hub. Attempting login..."
        if ! docker login; then
            log_error "Docker Hub login failed. Please check your credentials."
            exit 1
        fi
    fi
    
    # Verify required files exist
    if [[ ! -f "Dockerfile" ]]; then
        log_error "Dockerfile not found in current directory"
        exit 1
    fi
    
    if [[ ! -f "trufflehog_wrapper.py" ]]; then
        log_error "trufflehog_wrapper.py not found in current directory"
        exit 1
    fi
    
    log_success "All required files found"
    
    # Build the image
    log_info "Building Docker image..."
    local build_args="--platform linux/amd64,linux/arm64"
    
    # Check if buildx is available for multi-platform builds
    if docker buildx version >/dev/null 2>&1; then
        log_info "Using Docker Buildx for multi-platform build"
        
        # Create and use buildx builder if it doesn't exist
        if ! docker buildx ls | grep -q "axilock-builder"; then
            log_info "Creating buildx builder..."
            docker buildx create --name axilock-builder --use
        else
            docker buildx use axilock-builder
        fi
        
        # Build and push in one step
        log_info "Building and pushing multi-platform image..."
        if docker buildx build \
            --platform linux/amd64,linux/arm64 \
            -t "$DOCKER_REPO:$PLUGIN_NAME-v$VERSION" \
            -t "$DOCKER_REPO:$PLUGIN_NAME-latest" \
            --push .; then
            log_success "Multi-platform build and push completed!"
        else
            log_error "Multi-platform build failed"
            exit 1
        fi
    else
        log_warning "Docker Buildx not available, building for current platform only"
        
        # Build for current platform
        if docker build -t "$PLUGIN_NAME:latest" .; then
            # Show image size
            local size=$(docker images "$PLUGIN_NAME:latest" --format "table {{.Size}}" | tail -1)
            log_success "Build completed successfully (Size: $size)"
        else
            log_error "Build failed"
            exit 1
        fi
        
        # Tag the image
        log_info "Tagging image for Docker Hub..."
        docker tag "$PLUGIN_NAME:latest" "$DOCKER_REPO:$PLUGIN_NAME-v$VERSION"
        docker tag "$PLUGIN_NAME:latest" "$DOCKER_REPO:$PLUGIN_NAME-latest"
        
        # Push to Docker Hub
        log_info "Pushing to Docker Hub..."
        if docker push "$DOCKER_REPO:$PLUGIN_NAME-v$VERSION" && \
           docker push "$DOCKER_REPO:$PLUGIN_NAME-latest"; then
            log_success "Push completed successfully"
        else
            log_error "Push failed"
            exit 1
        fi
    fi
    
    # Verify the upload
    log_info "Verifying upload by pulling image..."
    if docker pull "$DOCKER_REPO:$PLUGIN_NAME-v$VERSION" >/dev/null 2>&1; then
        log_success "Image successfully verified on Docker Hub"
    else
        log_warning "Could not verify image on Docker Hub (may take a moment to become available)"
    fi
    
    # Show final information
    echo ""
    log_success "🎉 Deployment completed successfully!"
    echo ""
    echo -e "${BLUE}Available tags:${NC}"
    echo -e "  📦 $DOCKER_REPO:$PLUGIN_NAME-v$VERSION"
    echo -e "  📦 $DOCKER_REPO:$PLUGIN_NAME-latest"
    echo ""
    echo -e "${BLUE}To use in your plugin system:${NC}"
    echo -e "${GREEN}self.docker_image = \"$DOCKER_REPO:$PLUGIN_NAME-v$VERSION\"${NC}"
    echo ""
    echo -e "${BLUE}To test the deployed image:${NC}"
    echo -e "${GREEN}docker run --rm -v \"\$(pwd)/test_input:/input:ro\" -v \"\$(pwd)/test_output:/output:rw\" $DOCKER_REPO:$PLUGIN_NAME-v$VERSION${NC}"
}

# Test function
test_deployment() {
    local image="$DOCKER_REPO:$PLUGIN_NAME-v$VERSION"
    
    log_info "Testing deployed image: $image"
    
    # Create test directories
    mkdir -p test_input test_output
    
    # Create test parameters
    cat > test_input/parameters.json << EOF
{
    "repo_url": "https://github.com/trufflesecurity/test_keys",
    "scan_type": "github",
    "only_verified": true
}
EOF
    
    # Create test input
    echo '{}' > test_input/input.json
    
    log_info "Running test scan..."
    if docker run --rm \
        -v "$(pwd)/test_input:/input:ro" \
        -v "$(pwd)/test_output:/output:rw" \
        "$image"; then
        
        if [[ -f "test_output/result.json" ]]; then
            local findings=$(cat test_output/result.json | python3 -c "import sys, json; print(json.load(sys.stdin)['summary']['total_findings'])" 2>/dev/null || echo "unknown")
            log_success "Test completed! Found $findings secrets"
            
            # Clean up test files
            rm -rf test_input test_output
        else
            log_error "Test failed - no output file generated"
            return 1
        fi
    else
        log_error "Test execution failed"
        return 1
    fi
}

# Parse command line arguments
case "${1:-deploy}" in
    "test")
        test_deployment
        ;;
    "deploy")
        deploy_plugin
        ;;
    "both")
        deploy_plugin
        echo ""
        test_deployment
        ;;
    *)
        echo "Usage: $0 [deploy|test|both] [version]"
        echo ""
        echo "Commands:"
        echo "  deploy  - Build and deploy to Docker Hub (default)"
        echo "  test    - Test the deployed image"
        echo "  both    - Deploy then test"
        echo ""
        echo "Examples:"
        echo "  $0 deploy 1.0.0"
        echo "  $0 test"
        echo "  $0 both 1.1.0"
        exit 1
        ;;
esac