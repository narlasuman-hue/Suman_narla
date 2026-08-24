#!/bin/bash

# Load sample data into Database Metadata Catalog
# Usage: ./scripts/load_sample_data.sh

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}Database Metadata Catalog - Sample Data Loader${NC}"
echo "=================================================="
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${BLUE}Activating virtual environment...${NC}"
    if [ -d "venv" ]; then
        source venv/bin/activate
    elif [ -d ".venv" ]; then
        source .venv/bin/activate
    else
        echo -e "${RED}Error: Virtual environment not found${NC}"
        echo "Please create one with: python -m venv venv"
        exit 1
    fi
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please copy .env.example to .env and configure your database settings"
    exit 1
fi

# Initialize database schema first
echo -e "${BLUE}Initializing database schema...${NC}"
python -c "from src.catalog.database import init_db; init_db()" || true

echo -e "${BLUE}Loading sample data...${NC}"
python -m src.sample_data

echo ""
echo -e "${GREEN}✅ Sample data loaded successfully!${NC}"
echo ""
echo "Next steps:"
echo "  1. Start the backend API: python main.py"
echo "  2. Start the frontend: cd frontend && npm start"
echo "  3. Open http://localhost:3000 in your browser"
echo ""
echo "API Documentation: http://localhost:8000/docs"
