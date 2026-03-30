"""
compute_diag_int.py

For each model in models.txt, for each year of diaG_T.nc files:
  - Depth-integrate diad_vars over full depth     -> suffix _int
  - Depth-integrate over top 200 m (level 0-15)  -> suffix _top200m
  - Depth-integrate over top 400 m (level 0-18)  -> suffix _top400m

Saves one diag_int file per year per model.

Usage:
    python compute_diag_int.py
"""

import xarray as xr
import pandas as pd
import glob
from pathlib import Path

# ===== PATHS =====
BASE_DIR   = Path('/gpfs/data/greenocean/software/runs')
OUTPUT_DIR = BASE_DIR          # output alongside model run directories
MODELS_TXT = Path('models.txt')
MESH_MASK  = Path('/gpfs/home/mep22dku/scratch/SOZONE/UTILS/mesh_mask3pt6_nicedims.nc')

# ===== VARIABLES =====
diad_vars = [
    'PPT', 'PPT_DIA', 'PPT_MIX', 'PPT_COC', 'PPT_PIC', 'PPT_PHA',
    'PPT_FIX', 'PPTDOC', 'CorgLoss', 'CO3prod', 'CO3diss'
]

# ===== INTEGRATION LEVELS =====
# Level 15 inclusive => bottom of cell ~ 200 m (check: gdept_1d[15] + e3t_1d[15]/2)
# Level 18 inclusive => bottom of cell ~ 400 m (check: gdept_1d[18] + e3t_1d[18]/2)
LEVELS = {
    'int':     None,   # full depth
    'top100m': 9,     # 0-indexed, inclusive
    'top200m': 15,     # 0-indexed, inclusive
    'top400m': 18,     # 0-indexed, inclusive
}


# ===== FUNCTION =====
def integrate_depth(dataset, var_list, tmesh, max_level=None):
    """
    Integrate 4D variables (time, depth, y, x) along the depth dimension.

    Parameters
    ----------
    dataset   : xr.Dataset  – input data with 4D variables
    var_list  : list[str]   – variable names to integrate
    tmesh     : xr.Dataset  – mesh mask containing e3t_0 and tmask
    max_level : int or None – deepest level index to include (0-based, inclusive).
                              None = integrate all levels.

    Returns
    -------
    xr.Dataset with depth-integrated variables (3D: time, y, x)
    """
    # Detect time and depth dimension names from first available variable
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

    # Build masked cell thickness
    e3t = tmesh['e3t_0'].copy() * tmesh['tmask'].values

    # Rename mesh dims (t, z) to match dataset dims
    dim_mapping = {}
    if 't' in e3t.dims:
        dim_mapping['t'] = time_dim
    if 'z' in e3t.dims:
        dim_mapping['z'] = depth_dim
    if dim_mapping:
        e3t = e3t.rename(dim_mapping)

    # Drop singleton time dim from e3t, then re-broadcast to dataset time if needed
    if time_dim in e3t.dims and e3t.sizes[time_dim] == 1:
        e3t = e3t.squeeze(time_dim, drop=True)
    if time_dim not in e3t.dims and time_dim in dataset.dims:
        e3t = e3t.expand_dims({time_dim: dataset[time_dim]})

    # Restrict to requested depth levels
    if max_level is not None:
        level_slice = slice(0, max_level + 1)   # +1: slice end is exclusive
        e3t = e3t.isel({depth_dim: level_slice})

    # Integrate each variable
    output_ds = xr.Dataset()
    for var in var_list:
        if var not in dataset.data_vars:
            print(f"    Warning: '{var}' not found in dataset, skipping.")
            continue

        data = dataset[var]
        if max_level is not None:
            data = data.isel({depth_dim: level_slice})

        e3t_bc   = xr.broadcast(data, e3t)[1]
        integrated = (data * e3t_bc).sum(dim=depth_dim)
        output_ds[var] = integrated

    return output_ds


# ===== MAIN =====
def main():
    # Load mesh mask once
    print(f"Loading mesh mask from {MESH_MASK}")
    tmask = xr.open_dataset(MESH_MASK)

    # Print actual bottom depths of the integration levels for reference
    for label, lvl in LEVELS.items():
        if lvl is not None:
            center    = float(tmask['gdept_1d'].values[lvl])
            thickness = float(tmask['e3t_1d'].values[lvl])
            bottom    = center + thickness / 2.0
            print(f"  {label}: level {lvl}, cell centre {center:.1f} m, "
                  f"bottom {bottom:.1f} m")

    # Read model list
    with open(MODELS_TXT) as f:
        models = [line.strip() for line in f if line.strip()]
    print(f"\nModels: {models}\n")

    for model in models:
        model_dir  = BASE_DIR / model
        output_dir = OUTPUT_DIR / model
        output_dir.mkdir(parents=True, exist_ok=True)

        # Find all diad_T files for this model
        pattern = str(model_dir / '**' / '*diad_T*.nc')
        files   = sorted(glob.glob(pattern, recursive=True))

        if not files:
            print(f"[{model}] No diad_T files found, skipping.")
            continue

        print(f"[{model}] Found {len(files)} diaG_T file(s).")

        for filepath in files:
            filepath = Path(filepath)
            print(f"  Processing {filepath.name} ...")

            ds = xr.open_dataset(filepath)

            # --- integrate at each depth range ---
            all_vars = xr.Dataset()

            for suffix, max_level in LEVELS.items():
                integrated = integrate_depth(ds, diad_vars, tmask, max_level=max_level)

                # Rename variables to include suffix
                rename_map = {v: f"{v}_{suffix}" for v in integrated.data_vars}
                integrated = integrated.rename(rename_map)
                all_vars   = xr.merge([all_vars, integrated])

            # --- tidy up time coordinate ---
            time_dim = [d for d in all_vars.dims if 'time' in d][0]
            try:
                time_pd = pd.to_datetime(
                    [pd.Timestamp(t.isoformat())
                     for t in all_vars[time_dim].values]
                )
                all_vars = all_vars.assign_coords({time_dim: time_pd})
            except Exception as e:
                print(f"    Warning: could not convert time coordinate: {e}")

            # --- attributes ---
            all_vars.attrs['description'] = (
                'Depth-integrated biogeochemical variables from diaG_T.nc. '
                'Suffixes: _int = full depth; _top200m = 0-200 m (levels 0-15); '
                '_top400m = 0-400 m (levels 0-18).'
            )
            all_vars.attrs['model']    = model
            all_vars.attrs['source']   = str(filepath)
            all_vars.attrs['made_in']  = '/gpfs/home/mep22dku/scratch/EXTRACT/compute_diag_int.py'
            all_vars.attrs['mesh_mask'] = str(MESH_MASK)

            for var in all_vars.data_vars:
                if 'units' in ds[var.rsplit('_', 1)[0]].attrs:
                    base_units = ds[var.rsplit('_', 1)[0]].attrs['units']
                    all_vars[var].attrs['units']       = f"({base_units}) * m"
                    all_vars[var].attrs['long_name']   = (
                        f"Depth-integrated {var.rsplit('_', 1)[0]}"
                    )

            # --- save ---
            # Replace diad_T with diag_int in the filename
            # e.g. ORCA2_1m_19520101_19521231_diad_T.nc -> ORCA2_1m_19520101_19521231_diag_int.nc
            output_name = filepath.name.replace('diad_T', 'diag_int')
            output_file = output_dir / output_name
            all_vars.to_netcdf(output_file)
            print(f"    Saved -> {output_file}")

            ds.close()

    print("\nDone.")


if __name__ == '__main__':
    main()
