import xarray as xr
import numpy as np
from pathlib import Path

# ===== INPUTS =====

models_file = 'models.txt'  # Path to text file containing model names
base_dir = '/gpfs/data/greenocean/software/runs/'

# Year range
year_start = 1953
year_end = 2023

# PFTs
pfts = ['DIA', 'MIX', 'COC', 'PIC', 'PHA', 'FIX']

# Depth levels to average over (in meters)
depth_levels = [10, 100]

# ===== FUNCTIONS =====

def average_top_meters(dataset, var_list, depth_meters, tmesh):
    """
    Average variables over the top x meters.
    
    Parameters
    ----------
    dataset : xr.Dataset
        Input dataset with 4D variables (time, depth, y, x)
    var_list : list of str
        Names of variables to average
    depth_meters : int or float
        Depth in meters over which to average (e.g., 100 for top 100m)
    tmesh : xr.Dataset
        Meshmask dataset containing depth info and cell thickness
        
    Returns
    -------
    xr.Dataset
        Dataset with averaged variables
    """
    # Get depth dimension name
    depth_dim = 'deptht'
    time_dim = 'time_counter'
    
    # Get depth coordinates and cell thickness
    depths = dataset[depth_dim].values
    e3t = tmesh['e3t_0'].copy()
    
    # Rename tmesh dimensions to match dataset dimensions
    dim_mapping = {}
    if 't' in e3t.dims:
        dim_mapping['t'] = time_dim
    if 'z' in e3t.dims:
        dim_mapping['z'] = depth_dim
    
    if dim_mapping:
        e3t = e3t.rename(dim_mapping)
    
    # Handle time dimension: squeeze if singleton, then broadcast if needed
    if time_dim in e3t.dims and e3t.sizes[time_dim] == 1:
        e3t = e3t.squeeze(time_dim, drop=True)
    
    # If e3t doesn't have the dataset's time dimension, add it
    if time_dim not in e3t.dims and time_dim in dataset.dims:
        e3t = e3t.expand_dims({time_dim: dataset[time_dim]})
    
    # Find indices where depth <= depth_meters
    depth_mask = depths <= depth_meters
    depth_indices = [i for i, mask in enumerate(depth_mask) if mask]
    
    if not depth_indices:
        raise ValueError(f"No depths found <= {depth_meters} meters")
    
    # Create output dataset
    output_ds = xr.Dataset()
    
    # Average each variable over the selected depth range
    for var in var_list:
        if var not in dataset.data_vars:
            print(f"Warning: variable {var} not found in dataset")
            continue
        
        # Select data within the depth range
        var_subset = dataset[var].isel({depth_dim: depth_indices})
        e3t_subset = e3t.isel({depth_dim: depth_indices})
        
        # Broadcast e3t to match variable dimensions
        e3t_broadcasted = xr.broadcast(var_subset, e3t_subset)[1]
        
        # Depth-weighted average
        weighted_sum = (var_subset * e3t_broadcasted).sum(dim=depth_dim)
        total_thickness = e3t_broadcasted.sum(dim=depth_dim)
        averaged = weighted_sum / total_thickness
        
        # Add to output dataset with suffix
        output_ds[f'{var}_avg_{int(depth_meters)}m'] = averaged
    
    return output_ds


def process_year(model, year, pfts, depth_levels, base_dir, tmesh):
    """
    Process a single year for a model.
    
    Parameters
    ----------
    model : str
        Model name
    year : int
        Year to process
    pfts : list of str
        List of PFT names (uppercase)
    depth_levels : list of int
        Depth levels to average over
    base_dir : str
        Base directory containing model runs
    tmesh : xr.Dataset
        Meshmask dataset
        
    Returns
    -------
    bool
        True if successful, False otherwise
    """
    model_dir = Path(base_dir) / model
    
    # File paths
    lop_file = model_dir / f'ORCA2_1m_{year}0101_{year}1231_LoP_T.nc'
    limphy_file = model_dir / f'ORCA2_1m_{year}0101_{year}1231_limphy.nc'
    output_file = model_dir / f'ORCA2_1m_{year}0101_{year}1231_LNL_T.nc'
    
    # Check if input files exist
    if not lop_file.exists():
        print(f"  Warning: LoP file not found: {lop_file}")
        return False
    
    if not limphy_file.exists():
        print(f"  Warning: limphy file not found: {limphy_file}")
        return False
    
    # Check if output already exists
    if output_file.exists():
        print(f"  Skipping {year} (output already exists)")
        return True
    
    try:
        print(f"  Processing {year}...")
        
        # Open datasets
        lop_ds = xr.open_dataset(lop_file)
        limphy_ds = xr.open_dataset(limphy_file)
        
        # Build variable lists
        ln_vars = [f'LN_{pft}' for pft in pfts]
        light_vars = [f'lim8light_{pft.lower()}' for pft in pfts]
        
        # Create combined output dataset
        output_ds = xr.Dataset()
        
        # Process each depth level
        for depth in depth_levels:
            # Average LN variables from LoP file
            ln_averaged = average_top_meters(lop_ds, ln_vars, depth, tmesh)
            
            # Average light limitation variables from limphy file
            light_averaged = average_top_meters(limphy_ds, light_vars, depth, tmesh)
            
            # Merge into output dataset
            output_ds = xr.merge([output_ds, ln_averaged, light_averaged])
        
        # Add metadata
        output_ds.attrs['made_in'] = '/gpfs/home/mep22dku/scratch/EXTRACT/create_LNL_files.py'
        output_ds.attrs['source_files'] = f'{lop_file.name}, {limphy_file.name}'
        output_ds.attrs['source_model'] = model
        output_ds.attrs['year'] = year
        output_ds.attrs['description'] = 'Top 10m and 100m averages of limiting nutrient (LN) and light limitation variables'
        
        # Save output
        output_ds.to_netcdf(output_file)
        print(f"  Saved: {output_file.name}")
        
        # Close datasets
        lop_ds.close()
        limphy_ds.close()
        
        return True
        
    except Exception as e:
        print(f"  ERROR processing {year}: {e}")
        return False


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

# Load meshmask once (used for all calculations)
print("Loading meshmask...")
tmesh = xr.open_dataset('/gpfs/data/greenocean/software/resources/regrid/mesh_mask3_6.nc')

# Read models from file
models = read_models_from_file(models_file)

if not models:
    print("No models to process. Exiting.")
    exit(1)

# Process each model
for model in models:
    print(f"\n{'='*60}")
    print(f"Processing model: {model}")
    print(f"{'='*60}")
    
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    for year in range(year_start, year_end + 1):
        result = process_year(model, year, pfts, depth_levels, base_dir, tmesh)
        if result:
            success_count += 1
        else:
            fail_count += 1
    
    print(f"\nSummary for {model}:")
    print(f"  Processed: {success_count} years")
    print(f"  Failed/Missing: {fail_count} years")

print(f"\n{'='*60}")
print("All models processed!")
print(f"{'='*60}")
