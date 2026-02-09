import xarray as xr
import numpy as np
import glob
from pathlib import Path

# ===== INPUTS =====

models_file = 'models.txt'  # Path to text file containing model names

# ===== FUNCTIONS =====

def get_limiter(run='TOM12_TJ_LC00', year=1920, dataset_note=None):
    """
    Extract limiting nutrient (LN) and limiting value (LV) for each phytoplankton functional type.
    
    Parameters
    ----------
    run : str
        Model run name (e.g., 'TOM12_TJ_LC00')
    year : int
        Year to process
    dataset_note : str, optional
        Note to add to output dataset metadata
        
    Returns
    -------
    xr.Dataset
        Dataset containing LV and LN variables for each PFT
    """
    tdir = f'/gpfs/data/greenocean/software/runs/{run}/'
    tfi = f'ORCA2_1m_{year}0101_{year}1231_diad_T.nc'
    w = xr.open_dataset(f'{tdir}/{tfi}')
    print(f'{run} {year}')
    
    # Load meshmask
    tmesh = xr.open_dataset('/gpfs/data/greenocean/software/resources/regrid/mesh_mask3_6.nc')
    tm = tmesh.tmask.isel(t=0)
    
    # Broadcast mask
    tm_broad, _ = xr.broadcast(tm, w['nav_lat'])
    tm_broad = tm_broad.expand_dims(time=w.time_counter)
    
    # PFTs
    pfts = ['dia', 'mix', 'coc', 'pic', 'pha', 'fix']
    
    # Nutrient codes
    limiter_codes = dict(fe=3, p=4, si=5, n=6)
    
    for pft in pfts:
        varlist = [
            f'lim3fe_{pft}',   # Fe
            f'lim4po4_{pft}',  # P
            f'lim6din_{pft}',  # N
        ]
        if pft == 'dia':
            varlist.insert(2, f'lim5si_{pft}')  # Si at index 2
        
        # Stack
        stacked = xr.concat([w[v] for v in varlist], dim='nutrient')
        stacked = stacked.where(stacked != 0, np.nan)
        
        # Replace NaNs with infinity for min calculation
        stacked_for_min = stacked.fillna(np.inf)
        
        # LV (Limiting Value)
        lv_name = f'LV_{pft.upper()}'
        lv_result = stacked_for_min.min(dim='nutrient')
        # Convert inf back to NaN
        lv_result = lv_result.where(np.isfinite(lv_result.values), np.nan)
        w[lv_name] = lv_result
        
        # LN (Limiting Nutrient)
        min_idx = stacked_for_min.argmin(dim='nutrient').values.astype(float)
        min_idx[tm_broad.values == 0] = np.nan
        
        if pft == 'dia':
            order = ['fe', 'p', 'si', 'n']
        else:
            order = ['fe', 'p', 'n']
        
        mapping = np.full_like(min_idx, np.nan)
        for i, nutr in enumerate(order):
            mapping[min_idx == i] = limiter_codes[nutr]
        
        ln_name = f'LN_{pft.upper()}'
        w[ln_name] = w[lv_name].copy()
        w[ln_name].data = mapping
    
    # Output vars
    outvars = []
    for pft in pfts:
        outvars.extend([f'LV_{pft.upper()}', f'LN_{pft.upper()}'])
    
    output_ds = w[outvars]
    output_ds.attrs['limiter_codes'] = "3 = Fe, 4 = P, 5 = Si, 6 = N"
    if dataset_note is not None:
        output_ds.attrs['note'] = dataset_note
    
    outfile = f'{tdir}/ORCA2_1m_{year}0101_{year}1231_LoP_T.nc'
    try:
        output_ds.to_netcdf(outfile)
        print(f'Saved {run} {year}:\n{outfile}\n')
    except Exception as e:
        print(f'Failed to save {run} {year}: {e}\n')
    
    return output_ds


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
mods = read_models_from_file(models_file)

if not mods:
    print("No models to process. Exiting.")
    exit(1)

# Process each model and year
for mod in mods:
    print(f"\n{'='*60}")
    print(f"Processing model: {mod}")
    print(f"{'='*60}")
    
    for year in range(1940, 2024):
        try:
            get_limiter(mod, year, 'made in /gpfs/home/mep22dku/scratch/EXTRACT/extract-LoP.py')
        except Exception as e:
            print(f'  Error for {mod}, {year}: {e}')

print(f"\n{'='*60}")
print("All models processed!")
print(f"{'='*60}")
