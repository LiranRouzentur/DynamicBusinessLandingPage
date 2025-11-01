#!/bin/bash
# Pre-commit hook for corpus validation
# Install: cp agents/corpus/tools/pre-commit-hook.sh .git/hooks/pre-commit

# Check if any corpus files are staged
if git diff --cached --name-only | grep -q "^agents/corpus/"; then
    echo "🔍 Validating corpus changes..."
    
    # Rebuild index if needed
    cd "$(git rev-parse --show-toplevel)"
    python agents/corpus/tools/rebuild_index.py
    
    # Validate all corpus files
    python agents/corpus/tools/validate.py --all
    
    if [ $? -ne 0 ]; then
        echo "❌ Corpus validation failed. Commit aborted."
        exit 1
    fi
    
    echo "✓ Corpus validation passed"
fi

exit 0

