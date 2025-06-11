#!/bin/bash

# Depth level (customize if needed)
LEVEL=2

# Ignore pattern
IGNORE="node_modules,.next,dist,.git,venv"

echo "📁 Project Root: $(pwd)"
echo "==============================="
npx tree-cli -L "$LEVEL" -I "$IGNORE"
echo ""

# Loop through each subdirectory
for dir in */ ; do
    # Skip ignored folders
    if [[ "$IGNORE" == *"${dir%/}"* ]]; then
        continue
    fi

    echo "📂 $dir"
    echo "-------------------------------"
    (cd "$dir" && npx tree-cli -L "$LEVEL" -I "$IGNORE")
    echo ""
done
