#!/bin/bash
# Push to GitHub - Run this script

cd /Users/surajpratap/Downloads/Benchmarking-Telugu

echo "=========================================="
echo "Pushing to GitHub..."
echo "Repository: Benchmarking-Special"
echo "=========================================="
echo ""
echo "You'll be prompted for:"
echo "  Username: SurajPratap10"
echo "  Password: Use your GitHub Personal Access Token"
echo ""
echo "Don't have a token? Get one here:"
echo "https://github.com/settings/tokens"
echo ""
echo "Press Enter to continue..."
read

git push special main

echo ""
echo "=========================================="
if [ $? -eq 0 ]; then
    echo "✅ SUCCESS! Code pushed to GitHub!"
    echo "View at: https://github.com/SurajPratap10/Benchmarking-Special"
else
    echo "❌ Push failed. Check authentication."
fi
echo "=========================================="

