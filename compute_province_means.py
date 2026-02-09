import numpy as np
import xarray as xr
import glob
from pathlib import Path
import pandas as pd


# ===== INPUTS =====
models_file = 'models.txt'  # Path to text file containing model names
model = 'TOM12_TJ_LA50'
filetype = 'ptrc'  # or 'diad'
variable = 'NO3'   # or 'PO4', 'Fer', 'Si', 'PPINT', 'Cflx', 'EXP', etc.
depth = 0          # surface=0, or specific depth index, or None for 2D variables

# Paths
baseDir = '/gpfs/data/greenocean/software/runs/'

# Load masks
MA = xr.open_dataset('/gpfs/home/mep22dku/scratch/AMOC-PLANKTOM/AMOC-LoP-202510/data/mask_atl.nc')
mask = xr.open_dataset('/gpfs/home/mep22dku/scratch/SOZONE/UTILS/mesh_mask3pt6_nicedims.nc')

# Define provinces
provinces = {
    'GO': mask.csize,
    'AB': mask.csize * MA.AB,
    'HA': mask.csize * MA.HA,
    'NA': mask.csize * MA.NA
}

# ===== FUNCTION =====
def compute_averages(model, filetype, variable, depth, provinces, baseDir):
    """Compute province averages for a variable across all available years"""
    
    # Create model-specific output directory
    output_dir = Path(f'/gpfs/data/greenocean/users/mep22dku/clims/{model}/')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all files with specific pattern: ORCA2_1m_YYYYMMDD_YYYYMMDD_{filetype}_{letter}.nc
    pattern = f'{baseDir}/{model}/ORCA2_1m_????????_????????_{filetype}_?.nc'
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"No files found for {model}, {filetype}")
        return None
    
    # Extract years using regex to find 4-digit year in filename
    import re
    years = []
    for f in files:
        match = re.search(r'_(\d{4})', f)
        if match:
            years.append(int(match.group(1)))
    
    if not years:
        print(f"Could not extract years from filenames")
        return None
    
    yrst, yrend = min(years), max(years)
    print(f"Processing {model} - {filetype} - {variable}")
    print(f"Found {len(files)} files from {yrst} to {yrend}")
    
    all_results = []
    
    for i, filepath in enumerate(files):
        year = years[i] if i < len(years) else None
        
        # Print progress every 5 years
        if year and year % 5 == 0:
            print(f"  Processing year {year}...")
        
        try:
            with xr.open_dataset(filepath) as ds:
                # Handle EXP100 special case
                if variable == 'EXP100' and 'EXP' in ds:
                    var_data = (ds['EXP'].isel(deptht=9) + ds['EXP'].isel(deptht=10)) / 2
                elif variable in ds:
                    var_data = ds[variable]
                    # Apply depth selection only if variable has depth dimension
                    if 'deptht' in var_data.dims:
                        if depth is not None:
                            var_data = var_data.isel(deptht=depth)
                    # If no depth dimension, depth parameter is ignored
                else:
                    continue
                
                # Compute province means
                province_means = []
                province_names = []
                
                for prov_name, prov_mask in provinces.items():
                    masked_data = var_data.where(prov_mask > 0)
                    spatial_dims = [d for d in masked_data.dims if d not in ['time_counter', 'time']]
                    prov_mean = masked_data.mean(dim=spatial_dims)
                    province_means.append(prov_mean)
                    province_names.append(prov_name)
                
                # Stack into dataset
                stacked = xr.concat(province_means, dim='province')
                stacked['province'] = province_names
                all_results.append(stacked)
        
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
            continue
    
    # Concatenate and save
    if all_results:
        combined = xr.concat(all_results, dim='time_counter')
        
        # Convert cftime to pandas datetime
        time_pd = pd.to_datetime([pd.Timestamp(t.isoformat()) for t in combined.time_counter.values])
        combined = combined.assign_coords(time_counter=time_pd)
        
        combined.attrs['made_in'] = '/gpfs/home/mep22dku/scratch/EXTRACT/compute_province_means.py'
        output_file = output_dir / f"{model}_{filetype}_{variable}_d{depth}_provinces.nc"
        combined.to_netcdf(output_file)
        print(f"Saved to {output_file}")
        return combined
    
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

# Define variables to extract
ptrc_vars = [
    ('Fer', 0),
    ('Si', 0),
   ('NO3', 0),
   ('PO4', 0),
   ('DIC', 0),
   ('Alkalini', 0)
]

diad_vars = [
    ('TChl', 0),
    ('Cflx', None),
    ('PPINT', None),
    ('EXP100', None)
]

# Loop over models and variables
for model in models:
    print(f"\n{'='*60}")
    print(f"Processing model: {model}")
    print(f"{'='*60}")

    # Process ptrc variables
    for variable, depth in ptrc_vars:
        try:
            print(f"\n--- {variable} at depth {depth} ---")
            result = compute_averages(model, 'ptrc', variable, depth, provinces, baseDir)
        except Exception as e:
            print(f"ERROR processing {model} - ptrc - {variable}: {e}")

    # Process diad variables
    for variable, depth in diad_vars:
        try:
            print(f"\n--- {variable} at depth {depth} ---")
            result = compute_averages(model, 'diad', variable, depth, provinces, baseDir)
        except Exception as e:
            print(f"ERROR processing {model} - diad - {variable}: {e}")

print(f"\n{'='*60}")
print("All processing complete!")
print(f"{'='*60}")
