#!/bin/bash

# Fix Tailwind CSS setup for shadcn/ui compatibility
# This script downgrades Tailwind v4 to v3 and configures everything properly

set -e

echo "========================================="
echo "Fixing Tailwind CSS Setup for shadcn/ui"
echo "========================================="
echo ""

cd frontend-react

echo "📦 Step 1: Removing Tailwind CSS v4..."
npm uninstall tailwindcss @tailwindcss/vite

echo ""
echo "📦 Step 2: Installing Tailwind CSS v3..."
npm install -D tailwindcss@^3.4.1 postcss autoprefixer

echo ""
echo "📝 Step 3: Initializing Tailwind CSS v3 config..."
npx tailwindcss init -p

echo ""
echo "✅ Tailwind CSS v3 installed successfully!"
echo ""
echo "Next steps:"
echo "1. Run: npx shadcn@latest init"
echo "2. Choose the following options:"
echo "   - Style: Default"
echo "   - Base color: Slate"
echo "   - CSS variables: Yes"
echo ""
