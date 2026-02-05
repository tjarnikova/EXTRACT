
YS=2010
YE=2019

BASEDIR=/gpfs/data/greenocean/software/runs/clims

YS=2010
YE=2019
BASEDIR=/gpfs/data/greenocean/software/runs/clims

# Define runs and file types
runs=("TOM12_RW_OBi1" "TOM12_TJ_R4A1" "TOM12_TJ_LA50" "TOM12_TJ_LAH3" "TOM12_RY_ERA3")
file_types=("ptrc_T_int" "ptrc_T_10m" "diad_T_int" "ptrc_T_100m" "LoP_T_100m")

runs=("TOM12_TJ_LAH3")
file_types=("ptrc_T_int")

for run in "${runs[@]}"; do
    DIR=${BASEDIR}/${run}
    echo "Processing ${run}..."
    
    for ftype in "${file_types[@]}"; do
        INFILE="${DIR}/ORCA2_1m_clim_${YS}_${YE}_${ftype}.nc"
        OUTFILE="${DIR}/ORCA2_1m_clim_${YS}_${YE}_${ftype}_rg.nc"
        
        # Check if input file exists before processing
        if [ -f "$INFILE" ]; then
            echo "  Regridding ${ftype}..."
            cdo remapbil,r360x180 "$INFILE" "$OUTFILE"
        else
            echo "  Skipping ${ftype} (file not found)"
        fi
    done
    
    echo "Completed ${run}"
done

echo "All runs completed!"



# DIR=/gpfs/data/greenocean/software/runs/clims/TOM12_RW_OBi1
# cdo remapbil,r360x180 ${DIR}/ORCA2_1m_clim_${YS}_${YE}_grid_T.nc ${DIR}/ORCA2_1m_clim_${YS}_${YE}_grid_T_rg.nc
# cdo remapbil,r360x180 ${DIR}/ORCA2_1m_clim_${YS}_${YE}_diad_T.nc ${DIR}/ORCA2_1m_clim_${YS}_${YE}_diad_T_rg.nc



# cdo remapbil,r360x180 ${DIR}/ORCA2_1m_clim_${YS}_${YE}_ptrc_T.nc ${DIR}/ORCA2_1m_clim_${YS}_${YE}_ptrc_T_rg.nc
# cdo remapbil,r360x180 ${DIR}/ORCA2_1m_clim_${YS}_${YE}_LoP_T.nc ${DIR}/ORCA2_1m_clim_${YS}_${YE}_LoP_T_rg.nc

# DIR=/gpfs/data/greenocean/software/runs/TOM12_TJ_LAH3
# cdo remapbil,r360x180 ${DIR}/ORCA2_1m_clim_${YS}_${YE}_grid_T.nc ${DIR}/ORCA2_1m_clim_${YS}_${YE}_grid_T_rg.nc
# cdo remapbil,r360x180 ${DIR}/ORCA2_1m_clim_${YS}_${YE}_diad_T.nc ${DIR}/ORCA2_1m_clim_${YS}_${YE}_diad_T_rg.nc
# cdo remapbil,r360x180 ${DIR}/ORCA2_1m_clim_${YS}_${YE}_ptrc_T.nc ${DIR}/ORCA2_1m_clim_${YS}_${YE}_ptrc_T_rg.nc
# cdo remapbil,r360x180 ${DIR}/ORCA2_1m_clim_${YS}_${YE}_LoP_T.nc ${DIR}/ORCA2_1m_clim_${YS}_${YE}_LoP_T_rg.nc

# ORCA2_1m_clim_2010_2011_diad_T_int.nc
# ORCA2_1m_clim_2010_2011_ptrc_T_int.nc
# ORCA2_1m_clim_2010_2011_ptrc_T_100m.nc
# ORCA2_1m_clim_2010_2011_LoP_T_100m.nc

# DIR=/gpfs/data/greenocean/software/runs/TOM12_TJ_LA50
# cdo remapbil,r360x180 ${DIR}/ORCA2_1m_clim_${YS}_${YE}_diad_T_int.nc ${DIR}/ORCA2_1m_clim_${YS}_${YE}_diad_T_int_rg.nc
# cdo remapbil,r360x180 ${DIR}/ORCA2_1m_clim_${YS}_${YE}_ptrc_T_int.nc ${DIR}/ORCA2_1m_clim_${YS}_${YE}_ptrc_T_int_rg.nc
# cdo remapbil,r360x180 ${DIR}/ORCA2_1m_clim_${YS}_${YE}_ptrc_T_100m.nc ${DIR}/ORCA2_1m_clim_${YS}_${YE}_ptrc_T_100m_rg.nc
# cdo remapbil,r360x180 ${DIR}/ORCA2_1m_clim_${YS}_${YE}_LoP_T_100m.nc ${DIR}/ORCA2_1m_clim_${YS}_${YE}_LoP_T_100m_rg.nc

# DIR=/gpfs/data/greenocean/software/runs/TOM12_TJ_LAH3
# cdo remapbil,r360x180 ${DIR}/ORCA2_1m_clim_${YS}_${YE}_diad_T_int.nc ${DIR}/ORCA2_1m_clim_${YS}_${YE}_diad_T_int_rg.nc
# cdo remapbil,r360x180 ${DIR}/ORCA2_1m_clim_${YS}_${YE}_ptrc_T_int.nc ${DIR}/ORCA2_1m_clim_${YS}_${YE}_ptrc_T_int_rg.nc
# cdo remapbil,r360x180 ${DIR}/ORCA2_1m_clim_${YS}_${YE}_ptrc_T_100m.nc ${DIR}/ORCA2_1m_clim_${YS}_${YE}_ptrc_T_100m_rg.nc
# cdo remapbil,r360x180 ${DIR}/ORCA2_1m_clim_${YS}_${YE}_LoP_T_100m.nc ${DIR}/ORCA2_1m_clim_${YS}_${YE}_LoP_T_100m_rg.nc
