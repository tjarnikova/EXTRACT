#!/bin/bash

# Configuration
BASEDIR=/gpfs/data/greenocean/users/mep22dku/clims/
MODELS_FILE="models.txt"  # Path to text file containing model names

# Check if models file exists
if [ ! -f "$MODELS_FILE" ]; then
    echo "ERROR: Models file not found: $MODELS_FILE"
    exit 1
fi

# Read models from file into an array
runs=()
while IFS= read -r line; do
    # Remove leading/trailing whitespace
    line=$(echo "$line" | xargs)
    # Skip empty lines and comments (lines starting with #)
    if [ -n "$line" ] && [[ ! "$line" =~ ^# ]]; then
        runs+=("$line")
    fi
done < "$MODELS_FILE"

# Check if any models were loaded
if [ ${#runs[@]} -eq 0 ]; then
    echo "ERROR: No models found in $MODELS_FILE"
    exit 1
fi

echo "Loaded ${#runs[@]} models from $MODELS_FILE"

# Process each run
for run in "${runs[@]}"; do
    DIR=${BASEDIR}/${run}
    echo "Processing ${run}..."
    
    # Check if directory exists
    if [ ! -d "$DIR" ]; then
        echo "  Directory not found: ${DIR}"
        continue
    fi
    
    # Find all climatology files (matching pattern ORCA2_1m_clim_*_*.nc but not already regridded)
    for INFILE in ${DIR}/ORCA2_1m_clim_*_*.nc; do
        # Skip if no files found
        [ -e "$INFILE" ] || continue
        
        # Skip if already regridded (ends with _rg.nc)
        if [[ "$INFILE" == *_rg.nc ]]; then
            continue
        fi
        
        # Get filename without path
        BASENAME=$(basename "$INFILE")
        
        # Create output filename by inserting _rg before .nc
        OUTFILE="${INFILE%.nc}_rg.nc"
        
        # Skip if output already exists
        if [ -f "$OUTFILE" ]; then
            echo "  Skipping ${BASENAME} (already regridded)"
            continue
        fi
        
        echo "  Regridding ${BASENAME}..."
        cdo remapbil,r360x180 "$INFILE" "$OUTFILE"
    done
    
    echo "Completed ${run}"
done

echo "All runs completed!"
