#!/bin/bash

# AgentEva Portal Setup Script
# This script sets up the development environment

set -e  # Exit on error

echo "========================================="
echo "AgentEva Portal - Setup Script"
echo "========================================="
echo ""

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.11"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"; then
    echo "❌ Error: Python 3.11+ is required (found: $PYTHON_VERSION)"
    echo "Please install Python 3.11 or higher"
    exit 1
fi

echo "✓ Python version: $PYTHON_VERSION"
echo ""

# Navigate to backend directory
cd "$(dirname "$0")/../core/backend" || exit 1

# Check if virtual environment already exists
if [ -d "venv" ]; then
    echo "Virtual environment already exists."
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing virtual environment..."
        rm -rf venv
    else
        echo "Using existing virtual environment."
    fi
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
    echo ""
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip --quiet
echo "✓ pip upgraded"
echo ""

# Install requirements
echo "Installing Python dependencies..."
echo "This may take a few minutes..."
pip install -r requirements.txt --quiet
echo "✓ Dependencies installed"
echo ""

echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Copy .env.example to .env in the root directory:"
echo "   cp ../../.env.example ../../.env"
echo ""
echo "2. Edit .env with your configuration:"
echo "   - Database credentials (PostgreSQL)"
echo "   - OpenAI API key"
echo "   - Pinecone API key and environment"
echo "   - JWT secret"
echo ""
echo "3. Set up PostgreSQL database:"
echo "   createdb ai_support_platform"
echo ""
echo "4. Run database migrations (coming soon):"
echo "   alembic upgrade head"
echo ""
echo "5. Create your first tenant:"
echo "   python ../../scripts/create_tenant.py --name \"Your Company\" --slug \"your-company\" --domain \"yourcompany.com\""
echo ""
echo "6. Start the development server:"
echo "   source venv/bin/activate"
echo "   uvicorn main:app --reload"
echo ""
echo "The API will be available at: http://localhost:8000"
echo "API documentation: http://localhost:8000/docs"
echo ""