import xarray as xr
import numpy as np
import pandas as pd
import os

mask = xr.open_dataset('/gpfs/home/mep22dku/scratch/SOZONE/UTILS/mesh_mask3pt6_nicedims.nc')
regions = {
    'mask_lab': {'x': (115, 130), 'y': (110, 130), 'color': 'red'},
    'mask_nor': {'x': (135, 155), 'y': (120, 145), 'color': 'orange'},
}
for name, r in regions.items():
    submask = np.zeros_like(mask.tmask[0,:,:])
    submask[r['y'][0]:r['y'][1], r['x'][0]:r['x'][1]] = 1
    globals()[name] = submask * mask.tmask[0,:,:]

mask_lab_bool = mask_lab.astype(bool)
mask_nor_bool = mask_nor.astype(bool)

BASE_DIR   = '/gpfs/afm/greenocean/software/runs'
OUTPUT_DIR = '/gpfs/data/greenocean/users/mep22dku/clims'
YEARS      = range(1920, 2025)
VAR        = 'mldr10_1'

with open('models.txt', 'r') as f:
    models = [line.strip() for line in f if line.strip()]

for model in models:
    print(f"Processing {model}...")
    records = []

    for year in YEARS:
        fname = f'ORCA2_1m_{year}0101_{year}1231_grid_T.nc'
        fpath = os.path.join(BASE_DIR, model, fname)

        if not os.path.exists(fpath):
            print(f"  Missing: {fpath}, skipping.")
            continue

        try:
            ds  = xr.open_dataset(fpath)
            mld = ds[VAR]

            mld_lab = mld.where(mask_lab_bool)
            mld_nor = mld.where(mask_nor_bool)

            records.append({
                'time':         pd.Timestamp(f'{year}-01-01'),
                'mld_lab_mean': float(mld_lab.mean(skipna=True)),
                'mld_lab_max':  float(mld_lab.max(skipna=True)),
                'mld_nor_mean': float(mld_nor.mean(skipna=True)),
                'mld_nor_max':  float(mld_nor.max(skipna=True)),
            })
            ds.close()

        except Exception as e:
            print(f"  Error reading {fpath}: {e}")
            continue

    if records:
        df = pd.DataFrame(records).set_index('time')

        out_ds = xr.Dataset(
            {
                'mld_lab_mean': ('time', df['mld_lab_mean'].values),
                'mld_lab_max':  ('time', df['mld_lab_max'].values),
                'mld_nor_mean': ('time', df['mld_nor_mean'].values),
                'mld_nor_max':  ('time', df['mld_nor_max'].values),
            },
            coords={'time': df.index.values},
            attrs={'model': model, 'variable': VAR, 'description': 'Annual MLD diagnostics'}
        )

        # add variable attributes
        out_ds['mld_lab_mean'].attrs = {'long_name': 'Mean MLD in Labrador Sea mask', 'units': 'm'}
        out_ds['mld_lab_max'].attrs  = {'long_name': 'Max MLD in Labrador Sea mask',  'units': 'm'}
        out_ds['mld_nor_mean'].attrs = {'long_name': 'Mean MLD in Nordic Seas mask',  'units': 'm'}
        out_ds['mld_nor_max'].attrs  = {'long_name': 'Max MLD in Nordic Seas mask',   'units': 'm'}

        out_dir  = os.path.join(OUTPUT_DIR, model)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f'{model}_mld_timeseries.nc')
        out_ds.to_netcdf(out_path)
        print(f"  Saved to {out_path}")
