import xarray as xr
import numpy as np
import pandas as pd
import glob
from pathlib import Path

# ===== INPUTS =====

# Paths
baseDir = '/gpfs/data/greenocean/software/resources/CDFTOOLS/MOCresults/'
clims_dir = '/gpfs/data/greenocean/users/mep22dku/clims/'
models_file = 'models.txt'  # Path to text file containing model names

# ===== FUNCTION =====
def compute_amoc_timeseries(model, yrst, yrend, baseDir, clims_dir):
    """
    Compute two AMOC timeseries:
      a) Maximum overturning at 26.5°N (nearest nav_lat) below 500 m depth
      b) Maximum overturning north of 0°N and below 500 m depth (monthly varying location)
         Also saves the depth and latitude of the maximum for (b).

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
    tuple of (xarray.DataArray, xarray.Dataset) or (None, None)
        (amoc_26n, amoc_north_ds) or (None, None) if processing failed
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
        pattern = f'{baseDir}{model}_*_{yr}0101*MOC.nc'
        matching_files = glob.glob(pattern)
        if matching_files:
            file_list.append(matching_files[0])

    if not file_list:
        print(f"  No files found for {model}")
        return None, None

    print(f"  Found {len(file_list)} files")

    try:
        moc_dataset = xr.open_mfdataset(file_list)

        # ----------------------------------------------------------------
        # Identify dimension names and extract coordinate arrays as numpy
        # ----------------------------------------------------------------
        da_full   = moc_dataset.zomsfatl.squeeze()   # (time_counter, depthw, y) — drops any singleton dims (e.g. x)
        depth_dim = [d for d in da_full.dims if d not in ('time_counter', 'y')][0]

        # nav_lat: may be a coord or a variable; may be 2-D (y, x) — squeeze to 1-D
        nav_lat_da = moc_dataset['nav_lat'] if 'nav_lat' in moc_dataset else moc_dataset.coords['nav_lat']
        if nav_lat_da.ndim > 1:
            nav_lat_da = nav_lat_da.isel({d: 0 for d in nav_lat_da.dims if d != 'y'})
        nav_lat = nav_lat_da.values   # 1-D numpy array, length y

        depth_vals = da_full[depth_dim].values   # 1-D numpy array, length depthw

        # ----------------------------------------------------------------
        # Build integer index arrays for the two filters (avoids xr.where NaN issues)
        # ----------------------------------------------------------------
        deep_idx  = np.where(depth_vals < -500)[0]         # depth levels below 500 m (depthw is negative)
        north_idx = np.where(nav_lat > 0)[0]               # y-indices north of 0°N

        # ================================================================
        # (a) Maximum AMOC at 26.5°N, below 500 m
        # ================================================================
        y_26n      = int(np.abs(nav_lat - 26.5).argmin())
        lat_actual = nav_lat[y_26n]
        print(f"  (a) Nearest nav_lat to 26.5°N: {lat_actual:.3f}°N  (y={y_26n})")

        atl_26n      = da_full.isel(y=y_26n).squeeze()           # (time, depth)
        atl_26n_deep = atl_26n.isel({depth_dim: deep_idx})       # (time, deep_depth)
        # Mask exact zeros (land/bottom boundary fill values) before taking max
        atl_26n_deep = atl_26n_deep.where(atl_26n_deep != 0)
        amoc_26n     = atl_26n_deep.max(dim=depth_dim)
        amoc_26n.name = 'AMOC_26N'

        # ================================================================
        # (b) Maximum AMOC north of 0°N, below 500 m — monthly, with location
        # ================================================================
        atl_north = da_full.isel({depth_dim: deep_idx, 'y': north_idx})  # (time, deep_depth, north_y)
        # Mask exact zeros (land/bottom boundary fill values) before taking max
        atl_north = atl_north.where(atl_north != 0)
        amoc_north = atl_north.max(dim=[depth_dim, 'y'])
        amoc_north.name = 'AMOC_north'

        # Find location of maximum at each timestep using numpy on loaded values
        # Use a masked array so NaNs (from zero-masking) are ignored by argmax
        vals = atl_north.values   # (time, n_deep, n_north)
        n_time, n_deep, n_north = vals.shape

        vals_masked = np.ma.masked_invalid(vals)
        flat_idx    = np.ma.argmax(vals_masked.reshape(n_time, -1), axis=1)
        deep_pos, north_pos = np.unravel_index(flat_idx, (n_deep, n_north))

        # Map back to actual coordinate values
        depth_at_max = depth_vals[deep_idx[deep_pos]]    # metres
        lat_at_max   = nav_lat[north_idx[north_pos]]     # degrees north

        # ----------------------------------------------------------------
        # Convert cftime → pandas DatetimeIndex
        # ----------------------------------------------------------------
        time_pd = pd.to_datetime(
            [pd.Timestamp(t.isoformat()) for t in amoc_26n.time_counter.values]
        )
        amoc_26n   = amoc_26n.assign_coords(time_counter=time_pd)
        amoc_north = amoc_north.assign_coords(time_counter=time_pd)

        # ----------------------------------------------------------------
        # Build location DataArrays for (b)
        # ----------------------------------------------------------------
        depth_da = xr.DataArray(
            depth_at_max, coords={'time_counter': time_pd}, dims='time_counter',
            name='AMOC_north_depth',
            attrs={'units': 'm', 'long_name': 'Depth of maximum AMOC north of 0°N'}
        )
        lat_da = xr.DataArray(
            lat_at_max, coords={'time_counter': time_pd}, dims='time_counter',
            name='AMOC_north_lat',
            attrs={'units': 'degrees_north', 'long_name': 'Latitude of maximum AMOC north of 0°N'}
        )

        # ================================================================
        # Save (a): AMOC at 26.5°N
        # ================================================================
        ds_26n = amoc_26n.to_dataset()
        ds_26n.attrs.update({
            'made_in':       '/gpfs/home/mep22dku/scratch/EXTRACT/get_AMOC.py',
            'source_years':  f'{yrst}-{yrend}',
            'source_model':  model,
            'description':   'Maximum Atlantic overturning at 26.5°N below 500 m depth',
            'latitude_used': float(lat_actual),
        })
        out_26n = output_dir / f'{model}_AMOC_26N_{yrst}_{yrend}.nc'
        ds_26n.to_netcdf(out_26n)
        print(f"  (a) Saved to {out_26n}")

        # ================================================================
        # Save (b): Basin-wide AMOC north of 0°N + location
        # ================================================================
        ds_north = xr.Dataset({
            'AMOC_north':       amoc_north,
            'AMOC_north_depth': depth_da,
            'AMOC_north_lat':   lat_da,
        })
        ds_north.attrs.update({
            'made_in':      '/gpfs/home/mep22dku/scratch/EXTRACT/get_AMOC.py',
            'source_years': f'{yrst}-{yrend}',
            'source_model': model,
            'description':  (
                'Maximum Atlantic overturning north of 0°N and below 500 m depth. '
                'Location (depth, latitude) of the maximum is saved per timestep.'
            ),
        })
        out_north = output_dir / f'{model}_AMOC_north_{yrst}_{yrend}.nc'
        ds_north.to_netcdf(out_north)
        print(f"  (b) Saved to {out_north}")

        return amoc_26n, ds_north

    except Exception as e:
        print(f"  ERROR processing {model}: {e}")
        return None, None


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
                if line and not line.startswith('#'):
                    models.append(line)
        print(f"Loaded {len(models)} models from {filepath}")
        return models
    except FileNotFoundError:
        print(f"ERROR: Models file not found: {filepath}")
        return []


# ===== RUN =====

models = read_models_from_file(models_file)

if not models:
    print("No models to process. Exiting.")
    exit(1)

yrst  = 1920
yrend = 2024

for model in models:
    print(f"\n{'='*60}")
    print(f"Processing model: {model}")
    print(f"{'='*60}")

    try:
        amoc_26n, amoc_north_ds = compute_amoc_timeseries(model, yrst, yrend, baseDir, clims_dir)
    except Exception as e:
        print(f"ERROR processing {model}: {e}")

print(f"\n{'='*60}")
print("All processing complete!")
print(f"{'='*60}")
