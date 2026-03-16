"""
prov_diag.py

For each model in models.txt, for each diag_int.nc file:
  - Compute area-weighted provincial means across (x, y)
  - Output has dims (province, time_counter)
  - Saves alongside the diag_int file as *_prov.nc

Usage:
    python prov_diag.py
"""

import glob
import xarray as xr
import pandas as pd
from pathlib import Path

# ===== PATHS =====
BASE_DIR   = Path('/gpfs/data/greenocean/software/runs')
MODELS_TXT = Path('models.txt')
MASK_ATL   = Path('/gpfs/home/mep22dku/scratch/AMOC-PLANKTOM/AMOC-LoP-202510/data/mask_atl.nc')
MESH_MASK  = Path('/gpfs/home/mep22dku/scratch/SOZONE/UTILS/mesh_mask3pt6_nicedims.nc')

# ===== VARIABLES =====
PLOT_VARS = ['PPT', 'PPTDOC', 'CorgLoss', 'CO3prod', 'CO3diss']
SUFFIXES  = ['_int', '_top200m', '_top400m']

# ===== MASKS =====
print("Loading masks...")
MA   = xr.open_dataset(MASK_ATL)
mask = xr.open_dataset(MESH_MASK)

provinces = {
    'GO': mask.csize,
    'AB': mask.csize * MA.AB,
    'HA': mask.csize * MA.HA,
    'NA': mask.csize * MA.NA,
}

# ===== MAIN =====
with open(MODELS_TXT) as f:
    models = [l.strip() for l in f if l.strip()]

print(f"Models: {models}\n")

for model in models:
    model_dir = BASE_DIR / model
    files = sorted(glob.glob(str(model_dir / '**' / '*diag_int.nc'), recursive=True))

    if not files:
        print(f"[{model}] No diag_int files found, skipping.")
        continue

    print(f"[{model}] Found {len(files)} diag_int file(s).")

    for filepath in map(Path, files):
        print(f"  Processing {filepath.name} ...")

        ds = xr.open_dataset(filepath).drop_vars('time_centered', errors='ignore')

        ds_out = xr.Dataset()

        for var in PLOT_VARS:
            for suffix in SUFFIXES:
                name = var + suffix
                if name not in ds:
                    print(f"    Warning: '{name}' not found, skipping.")
                    continue

                field = ds[name]  # (time_counter, y, x)

                prov_means = []
                for prov_name, weights in provinces.items():
                    w = weights.broadcast_like(field)
                    weighted_mean = (field * w).sum(dim=['x', 'y']) / w.sum(dim=['x', 'y'])
                    prov_means.append(weighted_mean)

                ds_out[name] = xr.concat(
                    prov_means,
                    dim=pd.Index(list(provinces.keys()), name='province')
                )

        ds_out.attrs['description'] = 'Area-weighted provincial means of depth-integrated biogeochemistry.'
        ds_out.attrs['model']       = model
        ds_out.attrs['source']      = str(filepath)
        ds_out.attrs['made_in']     = str(Path(__file__).resolve())

        output_file = filepath.with_name(filepath.name.replace('diag_int', 'prov_diag'))
        ds_out.to_netcdf(output_file)
        print(f"    Saved -> {output_file}")

        ds.close()

print("\nDone.")
