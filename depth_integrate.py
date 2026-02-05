import xarray as xr
import glob
from pathlib import Path

# ===== INPUTS =====

# Paths
clims_dir = '/gpfs/data/greenocean/software/users/mep22dku/clims/'

# Load mask
mask = xr.open_dataset('/gpfs/home/mep22dku/scratch/SOZONE/UTILS/mesh_mask3pt6_nicedims.nc')

# Variable lists for different file types
diad_vars = ['PPT', 'PPT_DIA', 'PPT_MIX', 'PPT_COC', 'PPT_PIC', 'PPT_PHA', 'PPT_FIX']
ptrc_vars = ['BAC', 'PRO', 'PTE', 'MES', 'GEL', 'MAC', 'DIA', 'MIX', 'COC', 'PIC', 'PHA', 'FIX']

# ===== FUNCTION =====
def integrate_depth(dataset, var_list, tmesh, suffix='_int'):
    """
    Integrate 4D variables along depth dimension to create 3D variables.
    
    Parameters
    ----------
    dataset : xr.Dataset
        Input dataset with 4D variables (time, depth, y, x)
    var_list : list of str
        Names of variables to integrate
    tmesh : xr.Dataset
        Meshmask dataset containing cell thickness (e3t_0)
    suffix : str, optional
        Suffix to append to integrated variable names (default: '_int')
        Note: This parameter is kept for backwards compatibility but is not used
        
    Returns
    -------
    xr.Dataset
        Dataset containing only integrated versions of variables from var_list
    """
    
    # Find the time dimension name
    time_dim = None
    for var in var_list:
        if var in dataset.data_vars:
            dims = dataset[var].dims
            # Assume first dimension is time
            time_dim = dims[0]
            break
    
    if time_dim is None:
        raise ValueError(f"Could not find time dimension in variables: {var_list}")
    
    # Find the depth dimension name (typically 'deptht', 'depth', 'z', etc.)
    depth_dim = None
    for var in var_list:
        if var in dataset.data_vars:
            dims = dataset[var].dims
            if len(dims) >= 2:  # Should be 4D
                depth_dim = dims[1]
            break
    
    if depth_dim is None:
        raise ValueError(f"Could not find depth dimension in variables: {var_list}")
    
    # Get cell thickness (e3t) and rename dimensions to match dataset
    e3t = tmesh['e3t_0'].copy()
    
    # Rename tmesh dimensions to match dataset dimensions
    dim_mapping = {}
    if 't' in e3t.dims:
        dim_mapping['t'] = time_dim
    if 'z' in e3t.dims:
        dim_mapping['z'] = depth_dim
    
    if dim_mapping:
        e3t = e3t.rename(dim_mapping)
    
    # Handle time dimension: squeeze if singleton, then broadcast if needed
    if time_dim in e3t.dims and e3t.sizes[time_dim] == 1:
        e3t = e3t.squeeze(time_dim, drop=True)
    
    # If e3t doesn't have the dataset's time dimension, add it
    if time_dim not in e3t.dims and time_dim in dataset.dims:
        e3t = e3t.expand_dims({time_dim: dataset[time_dim]})
    
    # Create empty output dataset
    output_ds = xr.Dataset()
    
    # Integrate each variable
    for var in var_list:
        if var not in dataset.data_vars:
            print(f"Warning: variable {var} not found in dataset")
            continue
        
        # Broadcast e3t to match variable dimensions
        e3t_broadcasted = xr.broadcast(dataset[var], e3t)[1]
        
        # Depth-integrated values
        integrated = (dataset[var] * e3t_broadcasted).sum(dim=depth_dim)
        
        # Add to output dataset without suffix
        output_ds[var] = integrated
    
    return output_ds


def process_climatology(filepath, var_list, mask):
    """
    Process a single climatology file by depth-integrating specified variables.
    
    Parameters
    ----------
    filepath : str or Path
        Path to input climatology file
    var_list : list of str
        Variables to integrate
    mask : xr.Dataset
        Meshmask dataset
        
    Returns
    -------
    str or None
        Output filepath if successful, None otherwise
    """
    filepath = Path(filepath)
    
    try:
        print(f"Processing {filepath.name}...")
        
        # Open dataset
        ds = xr.open_dataset(filepath)
        
        # Integrate depth
        ds_int = integrate_depth(ds, var_list, mask)
        
        # Add metadata
        ds_int.attrs['made_in'] = '/gpfs/home/mep22dku/scratch/EXTRACT/depth_integrate.py'
        ds_int.attrs['source_file'] = str(filepath.name)
        
        # Create output filename
        output_file = filepath.parent / f"{filepath.stem}_int.nc"
        
        # Save
        ds_int.to_netcdf(output_file)
        print(f"  Saved to {output_file.name}")
        
        return str(output_file)
        
    except Exception as e:
        print(f"  ERROR processing {filepath.name}: {e}")
        return None


# ===== RUN =====

# Define models to process
models = ['TOM12_RW_OBi1', 'TOM12_TJ_R4A1', 'TOM12_TJ_LA50', 
          'TOM12_RY_ERA3', 'TOM12_TJ_LAH3', 'TOM12_TJ_LC51']
models = ['TOM12_TJ_OBA1','TOM12_TJ_OBC1', 'TOM12_TJ_OBH1' ]
# Process each model
for model in models:
    print(f"\n{'='*60}")
    print(f"Processing model: {model}")
    print(f"{'='*60}")
    
    model_dir = Path(clims_dir) / model
    
    if not model_dir.exists():
        print(f"  Model directory not found: {model_dir}")
        continue
    
    # Find all diad_T climatology files
    diad_files = sorted(model_dir.glob('ORCA2_1m_clim_*_diad_T.nc'))
    for diad_file in diad_files:
        try:
            process_climatology(diad_file, diad_vars, mask)
        except Exception as e:
            print(f"ERROR processing {diad_file.name}: {e}")
    
    # Find all ptrc_T climatology files
    ptrc_files = sorted(model_dir.glob('ORCA2_1m_clim_*_ptrc_T.nc'))
    for ptrc_file in ptrc_files:
        try:
            process_climatology(ptrc_file, ptrc_vars, mask)
        except Exception as e:
            print(f"ERROR processing {ptrc_file.name}: {e}")

print(f"\n{'='*60}")
print("All processing complete!")
print(f"{'='*60}")