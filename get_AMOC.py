import xarray as xr
import numpy as np
import pandas as pd
import glob
from pathlib import Path

# ===== INPUTS =====

# Paths
baseDir = '/gpfs/data/greenocean/software/resources/CDFTOOLS/MOCresults/'
clims_dir = '/gpfs/data/greenocean/users/mep22dku/clims/'

# ===== FUNCTION =====
def compute_amoc_timeseries(model, yrst, yrend, baseDir, clims_dir):
    """
    Compute AMOC timeseries as maximum overturning at 26°N in the Atlantic.
    
    Parameters:
    -----------
    model : str
        Model name (e.g., 'TOM12_TJ_LA50')
    yrst : int
        Start year
    yrend : int
        End year
    baseDir : str
        Directory containing MOC result files
    clims_dir : str
        Directory to save AMOC timeseries outputs
    
    Returns:
    --------
    xarray.DataArray or None
        The AMOC timeseries, or None if processing failed
    """
    
    # Create model-specific output directory
    output_dir = Path(clims_dir) / model
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Processing AMOC for {model}")
    print(f"  Years: {yrst} to {yrend}")
    
    # Build file list
    yrs = np.arange(yrst, yrend + 1, 1)
    file_list = []
    
    for yr in yrs:
        pattern = f'{baseDir}{model}_1m_{yr}0101*MOC.nc'
        matching_files = glob.glob(pattern)
        if matching_files:
            file_list.append(matching_files[0])
    
    if not file_list:
        print(f"  No files found for {model}")
        return None
    
    print(f"  Found {len(file_list)} files")
    
    try:
        # Open all MOC files
        moc_dataset = xr.open_mfdataset(file_list)
        
        # Extract Atlantic overturning at 26°N (y=94)
        atl_at_26 = moc_dataset.zomsfatl.sel(y=94).squeeze()
        
        # Calculate max along the depth dimension
        depth_dim = [d for d in atl_at_26.dims if d != 'time_counter'][0]
        max_atl = atl_at_26.max(dim=depth_dim)
        
        # Rename to AMOC
        max_atl.name = 'AMOC'
        
        # Convert cftime to pandas datetime
        time_pd = pd.to_datetime([pd.Timestamp(t.isoformat()) for t in max_atl.time_counter.values])
        max_atl = max_atl.assign_coords(time_counter=time_pd)
        
        # Convert to dataset and add metadata
        amoc_ds = max_atl.to_dataset()
        amoc_ds.attrs['made_in'] = '/gpfs/home/mep22dku/scratch/EXTRACT/get_AMOC.py'
        amoc_ds.attrs['source_years'] = f'{yrst}-{yrend}'
        amoc_ds.attrs['source_model'] = model
        amoc_ds.attrs['description'] = 'Maximum Atlantic overturning at 26°N'
        
        # Save to output directory
        output_file = output_dir / f'{model}_AMOC_{yrst}_{yrend}.nc'
        amoc_ds.to_netcdf(output_file)
        print(f"  Saved to {output_file}")
        
        return max_atl
        
    except Exception as e:
        print(f"  ERROR processing {model}: {e}")
        return None


# ===== RUN =====

# Define models to process
models = ['TOM12_TJ_LA50', 'TOM12_TJ_LC51', 'TOM12_TJ_LAH3']

# Define year range
yrst = 1940
yrend = 2020

# Loop over models
for model in models:
    print(f"\n{'='*60}")
    print(f"Processing model: {model}")
    print(f"{'='*60}")
    
    try:
        result = compute_amoc_timeseries(model, yrst, yrend, baseDir, clims_dir)
    except Exception as e:
        print(f"ERROR processing {model}: {e}")

print(f"\n{'='*60}")
print("All processing complete!")
print(f"{'='*60}")
