"""
extract_ice_sos.py
------------------
For each model in models.txt, find all icemod and grid_T monthly output files,
compute a global mask-weighted mean timeseries of ice presence and SSS,
and save to a per-model cache directory. Skips individual fields if already cached.
Processes whichever fields are available independently.

Usage:
    python extract_ice_sos.py [models.txt]
"""

import glob
import sys
from pathlib import Path

import xarray as xr

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_RUN  = Path('/gpfs/afm/greenocean/software/runs')
BASE_CLIM = Path('/gpfs/data/greenocean/users/mep22dku/clims')

MASK_FILE = '/gpfs/home/mep22dku/scratch/SOZONE/UTILS/mesh_mask3pt6_nicedims.nc'  # adjust as needed

# ---------------------------------------------------------------------------
# Load mask once
# ---------------------------------------------------------------------------

mask      = xr.open_dataset(MASK_FILE)
csize_sum = mask.csize.sum(dim=['y', 'x'])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_models(path='models.txt'):
    """Read model names from a text file, one per line, ignoring blank/comment lines."""
    with open(path) as f:
        return [l.strip() for l in f if l.strip() and not l.startswith('#')]


def glob_files(model, suffix):
    """Return all matching output files for a model, sorted chronologically."""
    return sorted(glob.glob(str(BASE_RUN / model / f'ORCA2_1m_*_{suffix}.nc')))


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def extract(model):
    """
    Compute global mask-weighted mean timeseries of ice presence and/or SSS,
    depending on which raw files are available. Each field is saved and checked
    for cache independently.
    """
    cache_dir = BASE_CLIM / model
    cache_dir.mkdir(parents=True, exist_ok=True)

    # --- ice presence ---
    path_ice  = cache_dir / 'avg_ice_pres.nc'
    if path_ice.exists():
        print(f'[{model}] Ice cache exists, skipping.')
    else:
        files_ice = glob_files(model, 'icemod')
        if not files_ice:
            print(f'[{model}] No icemod files found, skipping ice.')
        else:
            print(f'[{model}] Found {len(files_ice)} icemod files, computing ice...')
            ds_ice  = xr.concat([xr.open_dataset(f) for f in files_ice], dim='time_counter')
            avg_ice = (ds_ice.ice_pres * mask.csize).sum(dim=['y', 'x']) / csize_sum
            avg_ice.attrs.update({'long_name': 'Global mask-weighted mean ice presence', 'model': model})
            avg_ice.to_netcdf(path_ice)
            ds_ice.close()
            print(f'[{model}] Ice saved to {path_ice}')

    # --- sea surface salinity ---
    path_sos  = cache_dir / 'avg_sos.nc'
    if path_sos.exists():
        print(f'[{model}] SSS cache exists, skipping.')
    else:
        files_gridT = glob_files(model, 'grid_T')
        if not files_gridT:
            print(f'[{model}] No grid_T files found, skipping SSS.')
        else:
            print(f'[{model}] Found {len(files_gridT)} grid_T files, computing SSS...')
            ds_gridT = xr.concat([xr.open_dataset(f) for f in files_gridT], dim='time_counter')
            avg_sos  = (ds_gridT.sos * mask.csize).sum(dim=['y', 'x']) / csize_sum
            avg_sos.attrs.update({'long_name': 'Global mask-weighted mean SSS', 'units': 'psu', 'model': model})
            avg_sos.to_netcdf(path_sos)
            ds_gridT.close()
            print(f'[{model}] SSS saved to {path_sos}')


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    models_file = sys.argv[1] if len(sys.argv) > 1 else 'models.txt'
    models = read_models(models_file)
    print(f'Models: {models}\n')

    for model in models:
        extract(model)

    print('\nDone.')
