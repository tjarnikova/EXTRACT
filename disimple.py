import xarray as xr

def depth_integrate(ds, variables):
    '''takes an xarray and a list of variables. 
    assumes mol/L as input units, returns in mol/m2'''
    
    mask = xr.open_dataset('/gpfs/home/mep22dku/scratch/SOZONE/UTILS/mesh_mask3pt6_nicedims.nc')
    mask['e3t_m'] = mask.e3t_0 * mask.tmask

    e3t = mask['e3t_m']  # cell thickness in metres
    result = {}
    for var in variables:
        mol_per_m3 = ds[var] * 1000          # mol/L → mol/m3
        result[var] = (mol_per_m3 * e3t).sum(dim='deptht')
        result[var].attrs['units'] = 'mol/m2'
        
    result = xr.Dataset(result)
    
    return result
