"""
compute_DIC_top100m_200m.py

For each model in models.txt, for each year of ptrc_T.nc files:
  - Depth-average DIC over top 100m (levels 0-9)
  - Depth-average DIC over top 200m (levels 0-15)
  - Output: DIC_top100m, DIC_top200m in mmol/m3

Usage:
    python compute_DIC_top100m_200m.py
"""

import xarray as xr
import pandas as pd
import glob
from pathlib import Path

# ===== PATHS =====
BASE_DIR   = Path('/gpfs/data/greenocean/software/runs')
OUTPUT_DIR = BASE_DIR
MODELS_TXT = Path('models.txt')
MESH_MASK  = Path('/gpfs/home/mep22dku/scratch/SOZONE/UTILS/mesh_mask3pt6_nicedims.nc')

# ===== VARIABLES =====
ptrc_vars = ['DIC']

# ===== INTEGRATION LEVELS =====
LEVELS = {
    'top100m': 9,    # 0-indexed, inclusive
    'top200m': 15,   # 0-indexed, inclusive
}


# ===== FUNCTION =====
def integrate_depth(dataset, var_list, tmesh, max_level=None):
    """
    Depth-average 4D variables (time, depth, y, x) over specified levels.
    Returns depth-averaged variables (3D: time, y, x) in mmol/m3.
    """
    time_dim = depth_dim = None
    for var in var_list:
        if var in dataset.data_vars:
            dims = dataset[var].dims
            time_dim  = dims[0]
            depth_dim = dims[1] if len(dims) >= 2 else None
            break

    if time_dim is None:
        raise ValueError(f"Could not find time dimension from variables: {var_list}")
    if depth_dim is None:
        raise ValueError(f"Could not find depth dimension from variables: {var_list}")

    e3t = tmesh['e3t_0'].copy() * tmesh['tmask'].values

    dim_mapping = {}
    if 't' in e3t.dims:
        dim_mapping['t'] = time_dim
    if 'z' in e3t.dims:
        dim_mapping['z'] = depth_dim
    if dim_mapping:
        e3t = e3t.rename(dim_mapping)

    if time_dim in e3t.dims and e3t.sizes[time_dim] == 1:
        e3t = e3t.squeeze(time_dim, drop=True)
    if time_dim not in e3t.dims and time_dim in dataset.dims:
        e3t = e3t.expand_dims({time_dim: dataset[time_dim]})

    if max_level is not None:
        level_slice = slice(0, max_level + 1)
        e3t = e3t.isel({depth_dim: level_slice})

    output_ds = xr.Dataset()
    for var in var_list:
        if var not in dataset.data_vars:
            print(f"    Warning: '{var}' not found in dataset, skipping.")
            print(f"    Available vars: {list(dataset.data_vars)}")
            continue

        data = dataset[var]
        if max_level is not None:
            data = data.isel({depth_dim: level_slice})

        e3t_bc     = xr.broadcast(data, e3t)[1]
        integrated = (data * e3t_bc).sum(dim=depth_dim)

        # Divide by total thickness to get mean concentration, mol -> mmol
        total_depth    = e3t_bc.sum(dim=depth_dim)
        output_ds[var] = (integrated / total_depth) * 1000

    return output_ds


# ===== MAIN =====
def main():
    print(f"Loading mesh mask from {MESH_MASK}")
    tmask = xr.open_dataset(MESH_MASK)

    # Print actual bottom depths of integration levels for reference
    for label, lvl in LEVELS.items():
        center = float(tmask['gdept_1d'].values[lvl])
        bottom = center + float(tmask['e3t_1d'].values[lvl]) / 2.0
        print(f"  {label}: level {lvl}, cell centre {center:.1f} m, bottom {bottom:.1f} m")

    with open(MODELS_TXT) as f:
        models = [line.strip() for line in f if line.strip()]
    print(f"\nModels: {models}\n")

    for model in models:
        model_dir  = BASE_DIR / model
        output_dir = OUTPUT_DIR / model
        output_dir.mkdir(parents=True, exist_ok=True)

        pattern = str(model_dir / '**' / '*ptrc_T*.nc')
        files   = sorted(glob.glob(pattern, recursive=True))

        if not files:
            print(f"[{model}] No ptrc_T files found, skipping.")
            continue

        print(f"[{model}] Found {len(files)} ptrc_T file(s).")

        for filepath in files:
            filepath = Path(filepath)
            print(f"  Processing {filepath.name} ...")

            ds = xr.open_dataset(filepath)

            # Print available variables on first file to help identify DIC name
            if filepath == Path(files[0]):
                print(f"    Available variables: {list(ds.data_vars)}")

            all_vars = xr.Dataset()
            for suffix, max_level in LEVELS.items():
                integrated = integrate_depth(ds, ptrc_vars, tmask, max_level=max_level)
                rename_map = {v: f"{v}_{suffix}" for v in integrated.data_vars}
                integrated = integrated.rename(rename_map)
                all_vars   = xr.merge([all_vars, integrated])

            # Tidy time coordinate
            time_dim = [d for d in all_vars.dims if 'time' in d][0]
            try:
                time_pd = pd.to_datetime(
                    [pd.Timestamp(t.isoformat()) for t in all_vars[time_dim].values]
                )
                all_vars = all_vars.assign_coords({time_dim: time_pd})
            except Exception as e:
                print(f"    Warning: could not convert time coordinate: {e}")

            # Attributes
            all_vars.attrs['description'] = (
                'Depth-averaged DIC concentration over top 100m and top 200m '
                'from ptrc_T.nc. Units: mmol/m3.'
            )
            all_vars.attrs['model']     = model
            all_vars.attrs['source']    = str(filepath)
            all_vars.attrs['made_in']   = 'compute_DIC_top100m_200m.py'
            all_vars.attrs['mesh_mask'] = str(MESH_MASK)

            for var in all_vars.data_vars:
                all_vars[var].attrs['units']     = 'mmol/m3'
                all_vars[var].attrs['long_name'] = (
                    f"Depth-averaged DIC, "
                    f"{'top 100m' if '100m' in var else 'top 200m'}"
                )

            # Save
            output_name = filepath.name.replace('ptrc_T', 'DIC_top100m_200m')
            output_file = output_dir / output_name
            all_vars.to_netcdf(output_file)
            print(f"    Saved -> {output_file}")

            ds.close()

    print("\nDone.")


if __name__ == '__main__':
    main()
