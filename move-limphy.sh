#!/bin/bash

# Configuration
BASE_RUN_DIR="/gpfs/home/mep22dku/scratch/ModelRuns"
BASE_RESULTS_DIR="/gpfs/data/greenocean/software/runs"
MODELS_FILE="models.txt"

# Check if models file exists
if [ ! -f "$MODELS_FILE" ]; then
    echo "ERROR: Models file not found: $MODELS_FILE"
    exit 1
fi

# Read models from file into an array
models=()
while IFS= read -r line; do
    # Remove leading/trailing whitespace
    line=$(echo "$line" | xargs)
    # Skip empty lines and comments (lines starting with #)
    if [ -n "$line" ] && [[ ! "$line" =~ ^# ]]; then
        models+=("$line")
    fi
done < "$MODELS_FILE"

# Check if any models were loaded
if [ ${#models[@]} -eq 0 ]; then
    echo "ERROR: No models found in $MODELS_FILE"
    exit 1
fi

echo "Loaded ${#models[@]} models from $MODELS_FILE"
echo ""

# Process each model
for model in "${models[@]}"; do
    echo "=================================================="
    echo "Processing model: $model"
    echo "=================================================="
    
    RUN_DIR="${BASE_RUN_DIR}/${model}"
    RESULTS_DIR="${BASE_RESULTS_DIR}/${model}"
    
    echo "Run directory: $RUN_DIR"
    echo "Results directory: $RESULTS_DIR"
    echo ""
    
    # Check if run directory exists
    if [ ! -d "$RUN_DIR" ]; then
        echo "Warning: Run directory $RUN_DIR does not exist, skipping"
        echo ""
        continue
    fi
    
    # Check if results directory exists
    if [ ! -d "$RESULTS_DIR" ]; then
        echo "Error: Results directory $RESULTS_DIR does not exist, skipping"
        echo ""
        continue
    fi
    
    # Change to run directory
    cd "$RUN_DIR" || { echo "Error: Cannot access $RUN_DIR, skipping"; echo ""; continue; }
    
    # Find and move files matching the pattern FROM run directory TO results directory
    count=0
    for file in ORCA2*limphy*; do
        # Check if any files match (avoid error if no matches)
        if [ ! -e "$file" ]; then
            echo "No files matching pattern ORCA2*limphy* found in $RUN_DIR"
            break
        fi
        
        echo "Moving $file to $RESULTS_DIR"
        mv "$file" "$RESULTS_DIR/"
        
        echo "Creating symlink for $file"
        ln -s "$RESULTS_DIR/$file" "$file"
        
        ((count++))
    done
    
    echo "Done! Moved and linked $count file(s) for $model"
    echo ""
done

echo "=================================================="
echo "All models processed!"
echo "=================================================="
