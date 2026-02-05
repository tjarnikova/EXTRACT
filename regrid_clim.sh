#!/bin/bash

# Configuration
BASEDIR=/gpfs/data/greenocean/software/runs/clims/

# Define runs to process
runs=("TOM12_RW_OBi1" "TOM12_TJ_R4A1" "TOM12_TJ_LA50" "TOM12_TJ_LAH3" "TOM12_RY_ERA3" "TOM12_TJ_LC51")
runs=("TOM12_TJ_OBA1" "TOM12_TJ_OBC1" "TOM12_TJ_OBH1")

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