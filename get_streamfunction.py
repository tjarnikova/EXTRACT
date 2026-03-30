import os
import numpy as np
import xarray as xr

# ── Config ────────────────────────────────────────────────────────────────────
models_file = 'models.txt'
moc_base    = '/gpfs/data/greenocean/software/resources/CDFTOOLS/MOCresults'
year_start  = 1940
year_end    = 1949

# ── Load models ───────────────────────────────────────────────────────────────
with open(models_file) as f:
    models = [line.strip() for line in f if line.strip()]

# ── Extract ───────────────────────────────────────────────────────────────────
for model in models:
    print(f'Processing: {model}')
    
    # Gather files for the requested year range
    files = []
    for year in range(year_start, year_end + 1):
        matches = [os.path.join(moc_base, f) for f in os.listdir(moc_base)
           if (f.startswith(f'{model}_1m_{year}') or f.startswith(f'{model}_7d_{year}'))
           and f.endswith('_MOC.nc')]
        files.extend(sorted(matches))
    
    if not files:
        print(f'  No files found for {model}, skipping')
        continue
    print(f'  Found {len(files)} files')

    # Load, select variable, squeeze x, mean over time
    ds = xr.open_mfdataset(files, combine='by_coords')
    sf = ds['zomsfatl'].squeeze('x').mean(dim='time_counter')

    # Build output dataset keeping nav_lat
    out = xr.Dataset(
        {'zomsfatl': sf},
        coords={k: ds[k] for k in ['nav_lat'] if k in ds}
    )

    outdir  = f'/gpfs/data/greenocean/users/mep22dku/clims/{model}'
    os.makedirs(outdir, exist_ok=True)
    outpath = f'{outdir}/{model}_SF_{year_start}_{year_end}.nc'
    out.to_netcdf(outpath)
    print(f'  Saved to {outpath}')
