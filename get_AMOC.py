

clims_dir = '/gpfs/data/greenocean/users/mep22dku/clims/'

def make_AMOClist(yrst, yrend, tr, baseDir = '/gpfs/data/greenocean/software/resources/CDFTOOLS/MOCresults/'):
    yrs = np.arange(yrst,yrend+1,1)
    ylist = []
    for i in range(0,len(yrs)):
        tyr = yrs[i]
        ty = f'{baseDir}{tr}_1m_{tyr}0101*MOC.nc'
        t2 = glob.glob(ty)
        ylist.append(t2[0])
    return ylist

def get_max_amoc(moc_dataset):
    atl_at_26 = moc_dataset.zomsfatl.sel(y=94).squeeze()
    
    # Calculate max along the depth dimension
    max_atl = atl_at_26.max(dim=[d for d in atl_at_26.dims if d != 'time_counter'][0])
    
    # Rename to AMOC
    max_atl.name = 'AMOC'
    
    # Convert cftime to pandas datetime
    time_pd = pd.to_datetime([pd.Timestamp(t.isoformat()) for t in max_atl.time_counter.values])
    max_atl = max_atl.assign_coords(time_counter=time_pd)
    ## TODO - save in a netcdf that also has an attribute called made_in which says what script it comes from, in clims_dir/{model}
    
    return max_atl

### RUN ###
runs = ['TOM12_TJ_LA50','TOM12_TJ_LC51','TOM12_TJ_LAH3']
yrst = 1940
yren = 2020
max_atl = get_max_amoc(xr.open_mfdataset(make_AMOClist(yrst, yren, run_ID)))