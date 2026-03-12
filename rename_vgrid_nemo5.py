import xarray as xr
import os
import glob


def rename_and_save(input_path: str, output_path: str) -> None:
    """
    Load vomecrty variable and associated grid_V coordinates from a NetCDF file,
    rename y_grid_V -> y and x_grid_V -> x, then save to a new file.
    """
    ds = xr.open_dataset(input_path)
    ds_sub = ds[["vomecrty", "nav_lat_grid_V", "nav_lon_grid_V"]]
    ds_renamed = ds_sub.rename({
        "y_grid_V": "y",
        "x_grid_V": "x",
    })
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    ds_renamed.to_netcdf(output_path)
    print(f"Saved to {output_path}")


def process_all_files() -> None:
    base_input_dir = "/gpfs/home/mep22dku/scratch/ModelRuns"
    base_output_dir = "/gpfs/data/greenocean/users/mep22dku/clims"

    with open("models.txt", "r") as f:
        models = [line.strip() for line in f if line.strip()]

    if not models:
        print("No models found in models.txt")
        return

    print(f"Found {len(models)} model(s) in models.txt.")

    for model in models:
        input_dir = os.path.join(base_input_dir, model)
        output_dir = os.path.join(base_output_dir, model)

        input_files = glob.glob(os.path.join(input_dir, "ORCA2_7d_*_grid_V.nc"))

        if not input_files:
            print(f"No matching files found for model '{model}' in {input_dir}")
            continue

        print(f"\nModel: {model} — {len(input_files)} file(s) found.")

        for input_path in sorted(input_files):
            filename = os.path.basename(input_path)
            output_path = os.path.join(output_dir, filename)
            print(f"  Processing: {filename}")
            rename_and_save(input_path, output_path)

    print("\nDone.")


process_all_files()
