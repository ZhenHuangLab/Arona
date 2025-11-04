#!/bin/bash
# Git Migration Script: RAG-Anything → Arona
# This script helps you migrate to your own GitHub repository with fresh history
#
# IMPORTANT: 
# 1. Create an empty repository on GitHub first: https://github.com/new
# 2. Replace ZhenHuangLab with your actual GitHub username below
# 3. Review each command before executing

set -e  # Exit on error

echo "🚀 Starting Git Migration: RAG-Anything → Arona"
echo "================================================"
echo ""

# Configuration
GITHUB_USERNAME="ZhenHuangLab"  # ⚠️ REPLACE THIS WITH YOUR GITHUB USERNAME!
REPO_NAME="Arona"
NEW_REMOTE_URL="https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"

# Verify we're in the right directory
if [ ! -d ".git" ]; then
    echo "❌ Error: Not in a git repository. Please run this from the project root."
    exit 1
fi

echo "📋 Current Configuration:"
echo "  GitHub Username: ${GITHUB_USERNAME}"
echo "  Repository Name: ${REPO_NAME}"
echo "  New Remote URL: ${NEW_REMOTE_URL}"
echo ""

# Check if placeholder is still there
if [ "$GITHUB_USERNAME" = "GITHUB_USERNAME" ]; then
    echo "❌ Error: Please replace GITHUB_USERNAME with your actual GitHub username!"
    echo "   Edit this file and update the GITHUB_USERNAME variable."
    exit 1
fi

# Confirm before proceeding
read -p "⚠️  This will create a fresh git history. Continue? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "❌ Migration cancelled."
    exit 0
fi

echo ""
echo "Step 1: Creating orphan branch with fresh history..."
git checkout --orphan fresh-start

echo ""
echo "Step 2: Staging all files..."
git add -A

echo ""
echo "Step 3: Creating initial commit..."
git commit -m "Initial commit: Arona - Modern Multimodal RAG System

- Migrated from RAG-Anything with custom React frontend
- Implemented document processing and knowledge graph visualization
- Added multimodal query capabilities
- Configured for external LLM providers
- Built with FastAPI backend and React + TypeScript frontend"

echo ""
echo "Step 4: Removing old main branch..."
git branch -D main || echo "Note: main branch may not exist"

echo ""
echo "Step 5: Renaming current branch to main..."
git branch -m main

echo ""
echo "Step 6: Removing old remote..."
git remote remove origin || echo "Note: origin may not exist"

echo ""
echo "Step 7: Adding new remote..."
git remote add origin "$NEW_REMOTE_URL"

echo ""
echo "Step 8: Verifying remote configuration..."
git remote -v

echo ""
echo "✅ Local migration complete!"
echo ""
echo "📤 Next step: Push to GitHub"
echo "   Run: git push -u origin main --force"
echo ""
echo "⚠️  Make sure you've created an empty repository at:"
echo "   ${NEW_REMOTE_URL}"
echo ""
echo "After pushing, verify at:"
echo "   https://github.com/${GITHUB_USERNAME}/${REPO_NAME}"

