import xarray as xr
import numpy as np
import glob
import os
from pathlib import Path

# ===== INPUTS =====

# Paths
runs_dir = '/gpfs/data/greenocean/software/runs/'
clims_dir = '/gpfs/data/greenocean/users/mep22dku/clims/'
models_file = 'models.txt'  # Path to text file containing model names

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


def read_models_from_file(filepath):
    """
    Read model names from a text file (one per line).
    
    Parameters
    ----------
    filepath : str or Path
        Path to text file containing model names
        
    Returns
    -------
    list of str
        List of model names
    """
    models = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    models.append(line)
        print(f"Loaded {len(models)} models from {filepath}")
        return models
    except FileNotFoundError:
        print(f"ERROR: Models file not found: {filepath}")
        return []


# ===== RUN =====

# Read models from file
models = read_models_from_file(models_file)

if not models:
    print("No models to process. Exiting.")
    exit(1)

# Define file types to process
filetypes = ['ptrc_T', 'diad_T']

# Define year range
yrst = 1925
yrend = 1934

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
