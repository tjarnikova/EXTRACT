import xarray as xr
from pathlib import Path

# ===== INPUTS =====

# Paths
bdir = '/gpfs/data/greenocean/software/runs/clims/'
models_file = 'models.txt'  # Path to text file containing model names

# Load masks and setup
cdomask = xr.open_dataset('/gpfs/home/mep22dku/scratch/SOZONE/windAnalyis/wspdComponents/PlankTOMmask_regridrecalc.nc')
tmask = cdomask.tmask
ATL = xr.open_dataset('/gpfs/home/mep22dku/scratch/SOZONE/UTILS/mesh_mask3pt6_ATL_rg.nc')
ATL = ATL.ATL
ATL_csize = tmask * ATL

# Define parameters
ys = 2010
ye = 2019
phy = ['DIA', 'MIX', 'COC', 'PIC', 'PHA', 'FIX']
#'BAC', 'PRO', 'PTE', 'MES', 'GEL', 'MAC', 

# ===== FUNCTIONS =====

def compute_latitudinal_profiles(dataset, phy, ATL_csize):
    """
    Compute latitudinal profiles for phytoplankton variables.
    
    Parameters
    ----------
    dataset : xr.Dataset
        Input dataset with phytoplankton variables
    phy : list of str
        List of phytoplankton variable names
    ATL_csize : xr.DataArray
        Atlantic mask with cell sizes
        
    Returns
    -------
    xr.Dataset
        Dataset containing latitudinal profiles
    """
    # Implementation of latitudinal profile computation
    # (Add your actual implementation here)
    lat_profiles = dataset[phy].weighted(ATL_csize).mean(dim='x')
    return lat_profiles


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

# Process each model
for mod in mods:
    print(f"\n{'='*60}")
    print(f'Processing {mod}...')
    print(f"{'='*60}")
    
    try:
        # Load regridded integrated data
        input_file = f'{bdir}{mod}/ORCA2_1m_clim_{ys}_{ye}_ptrc_T_int_rg.nc'
        
        # Check if input file exists
        if not Path(input_file).exists():
            print(f"  Warning: Input file not found: {input_file}")
            continue
        
        dataset = xr.open_dataset(input_file)
        
        # Compute latitudinal profiles
        lat_profiles = compute_latitudinal_profiles(dataset, phy, ATL_csize)
        
        # Add metadata
        lat_profiles.attrs['made_in'] = 'compute_latitudinal_profiles.py'
        lat_profiles.attrs['source_file'] = input_file
        lat_profiles.attrs['source_model'] = mod
        
        # Save output
        output_file = f'{bdir}{mod}/ORCA2_1m_clim_{ys}_{ye}_ptrc_T_int_rg_latprof.nc'
        lat_profiles.to_netcdf(output_file)
        print(f'  Saved: {output_file}')
        
    except Exception as e:
        print(f"  ERROR processing {mod}: {e}")

print(f"\n{'='*60}")
print('All models processed!')
print(f"{'='*60}")
