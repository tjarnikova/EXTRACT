import xarray as xr
import numpy as np
import glob
import os
from pathlib import Path

# ===== INPUTS =====

# Paths
runs_dir = '/gpfs/data/greenocean/software/runs/'
clims_dir = '/gpfs/data/greenocean/users/mep22dku/clims/'

# ===== FUNCTION =====
def compute_climatology(model, filetype, yrst, yrend, runs_dir, clims_dir):
    """
    Compute monthly climatology for a model and file type across specified years.
    
    Parameters:
    -----------
    model : str
        Model name (e.g., 'TOM12_TJ_LA50')
    filetype : str
        File type to process (e.g., 'ptrc_T', 'diad_T')
    yrst : int
        Start year
    yrend : int
        End year
    runs_dir : str
        Directory containing model run files
    clims_dir : str
        Directory to save climatology outputs
    
    Returns:
    --------
    xarray.Dataset or None
        The computed climatology dataset, or None if processing failed
    """
    
    # Create model-specific output directory
    output_dir = Path(clims_dir) / model
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Processing {model} - {filetype}")
    print(f"  Years: {yrst} to {yrend}")
    
    # Build file list
    yrs = np.arange(yrst, yrend + 1, 1)
    file_list = []
    
    for yr in yrs:
        pattern = f'{runs_dir}{model}/ORCA2_1m_{yr}*{filetype}*.nc'
        matching_files = glob.glob(pattern)
        if matching_files:
            file_list.append(matching_files[0])
    
    if not file_list:
        print(f"  No files found for {model} {filetype}")
        return None
    
    print(f"  Found {len(file_list)} files")
    
    try:
        # Open all files and compute monthly climatology
        ds = xr.open_mfdataset(file_list)
        clim = ds.groupby('time_counter.month').mean('time_counter')
        clim = clim.rename({'month': 'time'})
        
        # Add metadata
        clim.attrs['made_in'] = '/gpfs/home/mep22dku/scratch/EXTRACT/get_clim.py'
        clim.attrs['source_years'] = f'{yrst}-{yrend}'
        clim.attrs['source_model'] = model
        
        # Save to output directory
        output_file = output_dir / f'ORCA2_1m_clim_{yrst}_{yrend}_{filetype}.nc'
        clim.to_netcdf(output_file)
        print(f"  Saved to {output_file}")
        
        return clim
        
    except Exception as e:
        print(f"  ERROR processing {model} {filetype}: {e}")
        return None


# ===== RUN =====

# Define models to process
models = ['TOM12_RW_OBi1', 'TOM12_TJ_R4A1', 'TOM12_TJ_LA50', 
          'TOM12_RY_ERA3', 'TOM12_TJ_LAH3', 'TOM12_TJ_LC51']

# Define file types to process
filetypes = ['ptrc_T', 'diad_T']

# Define year range
yrst = 2010
yrend = 2019

# Loop over models and file types
for model in models:
    print(f"\n{'='*60}")
    print(f"Processing model: {model}")
    print(f"{'='*60}")
    
    for filetype in filetypes:
        try:
            result = compute_climatology(model, filetype, yrst, yrend, runs_dir, clims_dir)
        except Exception as e:
            print(f"ERROR processing {model} - {filetype}: {e}")

print(f"\n{'='*60}")
print("All processing complete!")
print(f"{'='*60}")