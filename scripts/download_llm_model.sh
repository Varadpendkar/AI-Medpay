#!/usr/bin/env bash
# Download and setup LLM model for AI-MedPay RAG Chatbot
# This script downloads a quantized Llama 2 7B Chat model (4.2 GB)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODEL_DIR="${PROJECT_ROOT}/models/llm"
MODEL_NAME="llama-2-7b-chat.Q4_K_M.gguf"
MODEL_PATH="${MODEL_DIR}/${MODEL_NAME}"
SYMLINK_PATH="${MODEL_DIR}/ggml-model-q4_0.gguf"

# Model download URL (Hugging Face)
MODEL_URL="https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/${MODEL_NAME}"

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}🚀 AI-MedPay LLM Model Setup${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""
echo -e "${YELLOW}This will download Llama 2 7B Chat (quantized Q4_K_M)${NC}"
echo -e "${YELLOW}Model size: ~4.2 GB${NC}"
echo -e "${YELLOW}License: Meta Llama 2 Community License (Commercial use allowed)${NC}"
echo ""

# Check if model already exists
if [ -f "$SYMLINK_PATH" ]; then
    echo -e "${GREEN}✅ Model already exists at: ${SYMLINK_PATH}${NC}"
    MODEL_SIZE=$(ls -lh "$SYMLINK_PATH" | awk '{print $5}')
    echo -e "${GREEN}   Size: ${MODEL_SIZE}${NC}"
    echo ""
    read -p "Do you want to re-download? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Skipping download. Using existing model.${NC}"
        exit 0
    fi
fi

# Create model directory
echo -e "${BLUE}📂 Creating model directory...${NC}"
mkdir -p "$MODEL_DIR"
echo -e "${GREEN}✅ Directory created: ${MODEL_DIR}${NC}"
echo ""

# Check available disk space
AVAILABLE_SPACE=$(df -h "$MODEL_DIR" | awk 'NR==2 {print $4}')
echo -e "${BLUE}💾 Available disk space: ${AVAILABLE_SPACE}${NC}"
echo -e "${YELLOW}⚠️  Required: ~5 GB${NC}"
echo ""

read -p "Continue with download? (Y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Nn]$ ]]; then
    echo -e "${YELLOW}Download cancelled.${NC}"
    exit 0
fi

# Download model
echo ""
echo -e "${BLUE}⬇️  Downloading model from Hugging Face...${NC}"
echo -e "${BLUE}URL: ${MODEL_URL}${NC}"
echo -e "${BLUE}Destination: ${MODEL_PATH}${NC}"
echo ""

# Use curl with progress bar
if command -v curl &> /dev/null; then
    echo -e "${GREEN}Using curl to download...${NC}"
    curl -L --progress-bar \
        -o "$MODEL_PATH" \
        "$MODEL_URL" || {
        echo -e "${RED}❌ Download failed!${NC}"
        exit 1
    }
elif command -v wget &> /dev/null; then
    echo -e "${GREEN}Using wget to download...${NC}"
    wget --show-progress \
        -O "$MODEL_PATH" \
        "$MODEL_URL" || {
        echo -e "${RED}❌ Download failed!${NC}"
        exit 1
    }
else
    echo -e "${RED}❌ Neither curl nor wget found. Please install one of them.${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Download complete!${NC}"

# Verify download
if [ -f "$MODEL_PATH" ]; then
    MODEL_SIZE=$(ls -lh "$MODEL_PATH" | awk '{print $5}')
    echo -e "${GREEN}   Downloaded: ${MODEL_SIZE}${NC}"
    
    # Check if size is reasonable (should be ~4GB)
    SIZE_BYTES=$(stat -f%z "$MODEL_PATH" 2>/dev/null || stat -c%s "$MODEL_PATH" 2>/dev/null)
    if [ "$SIZE_BYTES" -lt 3000000000 ]; then
        echo -e "${RED}⚠️  Warning: File size seems too small. Download may be incomplete.${NC}"
        echo -e "${YELLOW}Expected: ~4.2 GB, Got: ${MODEL_SIZE}${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ Model file not found after download!${NC}"
    exit 1
fi

# Create symlink for standard naming
echo ""
echo -e "${BLUE}🔗 Creating symlink...${NC}"
ln -sf "$MODEL_PATH" "$SYMLINK_PATH"
echo -e "${GREEN}✅ Symlink created: ${SYMLINK_PATH} -> ${MODEL_NAME}${NC}"

# Install llama-cpp-python if not installed
echo ""
echo -e "${BLUE}📦 Checking llama-cpp-python installation...${NC}"

# Activate virtual environment if it exists
if [ -d "${PROJECT_ROOT}/AImedenv" ]; then
    source "${PROJECT_ROOT}/AImedenv/bin/activate"
    echo -e "${GREEN}✅ Virtual environment activated${NC}"
fi

# Check if llama-cpp-python is installed
if python -c "import llama_cpp" 2>/dev/null; then
    echo -e "${GREEN}✅ llama-cpp-python is already installed${NC}"
else
    echo -e "${YELLOW}⚠️  llama-cpp-python not found. Installing...${NC}"
    echo ""
    
    # Detect platform
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS - check for Apple Silicon
        if [[ $(uname -m) == "arm64" ]]; then
            echo -e "${BLUE}🍎 Detected Apple Silicon (M1/M2/M3)${NC}"
            echo -e "${BLUE}Installing with Metal acceleration...${NC}"
            CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python
        else
            echo -e "${BLUE}🍎 Detected Intel Mac${NC}"
            echo -e "${BLUE}Installing CPU-only version...${NC}"
            pip install llama-cpp-python
        fi
    else
        echo -e "${BLUE}🐧 Detected Linux/Other${NC}"
        echo -e "${BLUE}Installing CPU-only version...${NC}"
        echo -e "${YELLOW}For GPU support, see: https://github.com/abetlen/llama-cpp-python${NC}"
        pip install llama-cpp-python
    fi
    
    echo -e "${GREEN}✅ llama-cpp-python installed${NC}"
fi

# Test model loading
echo ""
echo -e "${BLUE}🧪 Testing model load...${NC}"
cat > /tmp/test_llm.py << 'EOF'
import sys
from pathlib import Path
try:
    from llama_cpp import Llama
    model_path = sys.argv[1]
    print(f"Loading model from: {model_path}")
    llm = Llama(model_path=model_path, n_ctx=512, verbose=False)
    print("✅ Model loaded successfully!")
    
    # Test generation
    print("\n🧪 Testing text generation...")
    response = llm("Q: What is 2+2? A:", max_tokens=10, temperature=0.0, echo=False)
    answer = response['choices'][0]['text'].strip()
    print(f"Test output: {answer[:50]}...")
    print("\n✅ Model is working correctly!")
    
except Exception as e:
    print(f"❌ Error loading model: {e}")
    sys.exit(1)
EOF

python /tmp/test_llm.py "$SYMLINK_PATH" || {
    echo -e "${RED}❌ Model test failed!${NC}"
    echo -e "${YELLOW}The model downloaded but couldn't be loaded.${NC}"
    echo -e "${YELLOW}You may need to reinstall llama-cpp-python.${NC}"
    exit 1
}

rm /tmp/test_llm.py

# Set environment variable
echo ""
echo -e "${BLUE}⚙️  Setting environment variable...${NC}"
export LLAMA_MODEL_PATH="$SYMLINK_PATH"
echo -e "${GREEN}export LLAMA_MODEL_PATH=\"$SYMLINK_PATH\"${NC}"

# Success summary
echo ""
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}✅ LLM Model Setup Complete!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo -e "${GREEN}Model Details:${NC}"
echo -e "  📍 Location: ${SYMLINK_PATH}"
echo -e "  📦 Size: $(ls -lh "$SYMLINK_PATH" | awk '{print $5}')"
echo -e "  🏷️  Name: Llama 2 7B Chat (Q4_K_M)"
echo -e "  📜 License: Meta Llama 2 Community (Commercial OK)"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo -e "  1. Restart your Flask server"
echo -e "  2. Index documents: ${YELLOW}python scripts/index_docs.py${NC}"
echo -e "  3. Test chatbot: ${YELLOW}open http://127.0.0.1:5001/${NC}"
echo -e "  4. Click chat bubble and ask a question!"
echo ""
echo -e "${BLUE}Environment Variable (add to your shell config):${NC}"
echo -e "  ${YELLOW}export LLAMA_MODEL_PATH=\"$SYMLINK_PATH\"${NC}"
echo ""
echo -e "${GREEN}🎉 Your AI chatbot is now ready with full LLM responses!${NC}"
echo ""
