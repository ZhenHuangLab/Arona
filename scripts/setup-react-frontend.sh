#!/bin/bash

# Setup script for React + TypeScript + Vite frontend
# This script initializes the new React frontend for RAG-Anything

set -e  # Exit on error

echo "========================================="
echo "RAG-Anything React Frontend Setup"
echo "========================================="
echo ""

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    echo "   Visit: https://nodejs.org/"
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js version 18+ is required. Current version: $(node -v)"
    exit 1
fi

echo "✅ Node.js version: $(node -v)"
echo "✅ npm version: $(npm -v)"
echo ""

# Get project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend-react"

echo "📁 Project root: $PROJECT_ROOT"
echo "📁 Frontend directory: $FRONTEND_DIR"
echo ""

# Check if frontend-react already exists
if [ -d "$FRONTEND_DIR" ]; then
    echo "⚠️  Directory 'frontend-react' already exists."
    read -p "Do you want to remove it and start fresh? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Removing existing frontend-react directory..."
        rm -rf "$FRONTEND_DIR"
    else
        echo "❌ Setup cancelled."
        exit 1
    fi
fi

# Create React + TypeScript + Vite project
echo "🚀 Creating Vite + React + TypeScript project..."
cd "$PROJECT_ROOT"
npm create vite@latest frontend-react -- --template react-ts

# Navigate to frontend directory
cd "$FRONTEND_DIR"

echo ""
echo "📦 Installing dependencies..."
npm install

echo ""
echo "🎨 Installing Tailwind CSS..."
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

echo ""
echo "🧩 Installing shadcn/ui..."
# Note: shadcn/ui requires manual init, we'll provide instructions
echo "   (Manual step required - see instructions below)"

echo ""
echo "📚 Installing additional packages..."
npm install \
  @tanstack/react-query \
  @tanstack/react-query-devtools \
  zustand \
  react-router-dom \
  axios \
  react-hook-form \
  zod \
  @hookform/resolvers \
  lucide-react \
  sonner \
  react-dropzone \
  clsx \
  tailwind-merge

echo ""
echo "🛠️  Installing dev dependencies..."
npm install -D \
  @types/node \
  @vitejs/plugin-react \
  eslint \
  prettier \
  vitest \
  @testing-library/react \
  @testing-library/jest-dom \
  @testing-library/user-event \
  @playwright/test

echo ""
echo "✅ Dependencies installed successfully!"
echo ""

# Create directory structure
echo "📂 Creating directory structure..."
mkdir -p src/api
mkdir -p src/components/ui
mkdir -p src/components/layout
mkdir -p src/components/chat
mkdir -p src/components/documents
mkdir -p src/components/common
mkdir -p src/hooks
mkdir -p src/store
mkdir -p src/types
mkdir -p src/utils
mkdir -p src/views

echo "✅ Directory structure created!"
echo ""

# Create .env.example
echo "📝 Creating .env.example..."
cat > .env.example << 'EOF'
# Backend API URL
VITE_API_BASE_URL=http://localhost:8000

# App Configuration
VITE_APP_TITLE=RAG-Anything
VITE_APP_VERSION=2.0.0

# Development
VITE_DEV_PORT=5173
EOF

# Create .env from .env.example
cp .env.example .env

echo "✅ Environment files created!"
echo ""

# Create .prettierrc
echo "📝 Creating Prettier configuration..."
cat > .prettierrc << 'EOF'
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 2,
  "useTabs": false,
  "arrowParens": "always",
  "endOfLine": "lf"
}
EOF

echo "✅ Prettier configuration created!"
echo ""

# Create .eslintrc.cjs
echo "📝 Creating ESLint configuration..."
cat > .eslintrc.cjs << 'EOF'
module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react-hooks/recommended',
  ],
  ignorePatterns: ['dist', '.eslintrc.cjs'],
  parser: '@typescript-eslint/parser',
  plugins: ['react-refresh'],
  rules: {
    'react-refresh/only-export-components': [
      'warn',
      { allowConstantExport: true },
    ],
    '@typescript-eslint/no-explicit-any': 'warn',
    '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
  },
}
EOF

echo "✅ ESLint configuration created!"
echo ""

# Update package.json scripts
echo "📝 Updating package.json scripts..."
npm pkg set scripts.dev="vite"
npm pkg set scripts.build="tsc && vite build"
npm pkg set scripts.preview="vite preview"
npm pkg set scripts.lint="eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0"
npm pkg set scripts.format="prettier --write \"src/**/*.{ts,tsx,css}\""
npm pkg set scripts.test="vitest"
npm pkg set scripts.test:ui="vitest --ui"
npm pkg set scripts.e2e="playwright test"

echo "✅ Package.json scripts updated!"
echo ""

echo "========================================="
echo "✅ React Frontend Setup Complete!"
echo "========================================="
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Initialize shadcn/ui:"
echo "   cd $FRONTEND_DIR"
echo "   npx shadcn-ui@latest init"
echo "   (Choose: TypeScript, Tailwind CSS, src/components/ui)"
echo ""
echo "2. Install shadcn/ui components:"
echo "   npx shadcn-ui@latest add button"
echo "   npx shadcn-ui@latest add dialog"
echo "   npx shadcn-ui@latest add input"
echo "   npx shadcn-ui@latest add dropdown-menu"
echo "   npx shadcn-ui@latest add card"
echo "   npx shadcn-ui@latest add toast"
echo ""
echo "3. Start development server:"
echo "   npm run dev"
echo ""
echo "4. Backend should be running on:"
echo "   http://localhost:8000"
echo ""
echo "5. Frontend will be available on:"
echo "   http://localhost:5173"
echo ""
echo "📚 Documentation:"
echo "   - Migration Guide: docs/REACT_MIGRATION_GUIDE.md"
echo "   - Task File: _TASKs/T2_react-frontend-migration.md"
echo ""
echo "Happy coding! 🚀"
echo ""

