"""
compute_DIC_prov.py

For each model in models.txt, for each year of DIC_top100m_200m.nc files:
  - Average DIC_top100m and DIC_top200m over each province mask
  - Output: {model}_DIC_prov_1940_2024.nc in clims/{model}/

Usage:
    python compute_DIC_prov.py
"""

import xarray as xr
import numpy as np
import pandas as pd
import glob
from pathlib import Path

# ===== PATHS =====
BASE_DIR   = Path('/gpfs/data/greenocean/software/runs')
CLIMS_DIR  = Path('/gpfs/data/greenocean/users/mep22dku/clims')
MODELS_TXT = Path('models.txt')
MASK_ATL   = Path('/gpfs/home/mep22dku/scratch/AMOC-PLANKTOM/AMOC-LoP-202510/data/mask_atl.nc')
MESH_MASK  = Path('/gpfs/home/mep22dku/scratch/SOZONE/UTILS/mesh_mask3pt6_nicedims.nc')

# ===== CONFIG =====
DIC_VARS = ['DIC_top100m', 'DIC_top200m']


# ===== LOAD MASKS ONCE =====
print("Loading masks...")
MA   = xr.open_dataset(MASK_ATL)
mesh = xr.open_dataset(MESH_MASK)

provinces = {
    'GO': mesh.csize,
    'AB': mesh.csize * MA.AB,
    'HA': mesh.csize * MA.HA,
    'NA': mesh.csize * MA.NA,
}


# ===== FUNCTION =====
def province_average(ds, provinces, var_list):
    """
    Weighted spatial average of var_list over each province.

    Parameters
    ----------
    ds         : xr.Dataset   - input data with spatial dims (y, x) + time
    provinces  : dict         - {name: weight_array (y, x)}
    var_list   : list[str]    - variables to average

    Returns
    -------
    xr.Dataset with dims (time, province)
    """
    results = {}

    for var in var_list:
        if var not in ds.data_vars:
            print(f"    Warning: {var} not found, skipping")
            continue

        prov_means = []
        for prov_name, weights in provinces.items():

            # Weighted mean: sum(data * weights) / sum(weights)
            weighted  = (ds[var] * weights).sum(dim=['y', 'x'])
            norm      = weights.sum()
            prov_mean = weighted / norm

            prov_mean = prov_mean.assign_coords(province=prov_name)
            prov_means.append(prov_mean)

        results[var] = xr.concat(prov_means, dim='province')

    return xr.Dataset(results)


# ===== MAIN =====
def main():
    with open(MODELS_TXT) as f:
        models = [line.strip() for line in f if line.strip()]
    print(f"Models: {models}\n")

    for model in models:
        model_dir = BASE_DIR / model
        out_dir   = CLIMS_DIR / model
        out_dir.mkdir(parents=True, exist_ok=True)

        pattern = str(model_dir / '**' / '*DIC_top100m_200m*.nc')
        files   = sorted(glob.glob(pattern, recursive=True))

        if not files:
            print(f"[{model}] No DIC files found, skipping.")
            continue

        print(f"[{model}] Found {len(files)} DIC file(s).")

        yearly_list = []

        for filepath in files:
            filepath = Path(filepath)
            print(f"  Processing {filepath.name} ...", end=' ', flush=True)

            ds = xr.open_dataset(filepath)

            # Province average
            ds_prov = province_average(ds, provinces, DIC_VARS)

            # Annual mean over monthly timesteps
            time_dim  = [d for d in ds_prov.dims if 'time' in d][0]
            ds_annual = ds_prov.mean(dim=time_dim, keep_attrs=True)

            # Extract year from filename e.g. ORCA2_1m_19400101_19401231_DIC...
            try:
                year = int(filepath.name.split('_')[2][:4])
            except Exception:
                year = int(filepath.stem[-4:])

            ds_annual = ds_annual.expand_dims(
                time=pd.to_datetime([f'{year}-07-02'])
            )
            yearly_list.append(ds_annual)
            print("done", flush=True)
            ds.close()

        if not yearly_list:
            print(f"  No data collected for {model}, skipping.")
            continue

        # Concatenate all years
        ds_ts = xr.concat(yearly_list, dim='time')

        # Attributes
        ds_ts.attrs['description'] = (
            'Province-averaged DIC concentration, top 100m and top 200m. '
            'Annual means. Provinces: GO, AB, HA, NA.'
        )
        ds_ts.attrs['model']   = model
        ds_ts.attrs['made_in'] = 'compute_DIC_prov.py'

        for var in ds_ts.data_vars:
            ds_ts[var].attrs['units']     = 'mmol/m3'
            ds_ts[var].attrs['long_name'] = f"Province-averaged {var}"

        # Save
        out_path = out_dir / f"{model}_DIC_prov_1940_2024.nc"
        encoding = {v: {'zlib': True, 'complevel': 4} for v in ds_ts.data_vars}
        ds_ts.to_netcdf(out_path, encoding=encoding)
        print(f"  Saved -> {out_path}")

    print("\nDone.")


if __name__ == '__main__':
    main()
