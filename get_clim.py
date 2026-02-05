import xarray as xr
import numpy as np
import glob
import os

runs_dir = '/gpfs/data/greenocean/software/runs/'
clims_dir = '/gpfs/data/greenocean/software/runs/clims/'
runs = ['TOM12_RW_OBi1', 'TOM12_TJ_R4A1', 'TOM12_TJ_LA50', 'TOM12_RY_ERA3', 'TOM12_TJ_LAH3', 'TOM12_TJ_LC51']

def make_yearlist(yrst, yrend, dtype, tr, runsDir):
    yrs = np.arange(yrst, yrend+1, 1)
    ylist = []
    for i in range(0, len(yrs)):
        ty = f'{runsDir}{tr}/ORCA2_1m_{yrs[i]}*{dtype}*.nc'
        t2 = glob.glob(ty)
        if t2:
            ylist.append(t2[0])
    return ylist

# File types to process
varty = ['ptrc_T', 'diad_T']
ys = 2010
ye = 2019

for mod in runs:
    # Create climatology folder for this model if it doesn't exist
    clim_mod_dir = f'{clims_dir}{mod}'
    if not os.path.exists(clim_mod_dir):
        os.makedirs(clim_mod_dir)
        print(f'Created directory: {clim_mod_dir}')
    
    for tvar in varty:
        try:
            # Get files from runs directory
            file_list = make_yearlist(ys, ye, tvar, mod, runs_dir)
            if not file_list:
                print(f'--no files found for {mod} {tvar}')
                continue
                
            w = xr.open_mfdataset(file_list)
            w = w.groupby('time_counter.month').mean('time_counter')
            w = w.rename({'month': 'time'})
            
            # Save to clims directory
            output_path = f'{clim_mod_dir}/ORCA2_1m_clim_{ys}_{ye}_{tvar}.nc'
            w.to_netcdf(output_path)
            print(f'YES {output_path}')
        except Exception as e:
            print(f'--no for {mod} {tvar}: {e}')