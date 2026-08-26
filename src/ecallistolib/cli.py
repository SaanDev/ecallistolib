import argparse
from datetime import date
import sys

def cmd_download(args):
    from .download import download_files, list_remote_fits

    try:
        d = date.fromisoformat(args.date)
    except ValueError:
        print("Error: date must be in YYYY-MM-DD format.")
        sys.exit(1)

    remote = list_remote_fits(d, args.hour, args.station)
    if not remote:
        print(f"No files found for {args.station} on {args.date} at hour {args.hour}.")
        sys.exit(0)

    print(f"Found {len(remote)} files. Downloading to {args.out_dir}...")
    paths = download_files(remote, out_dir=args.out_dir)
    for p in paths:
        print(f"Downloaded: {p}")

def cmd_plot(args):
    import matplotlib.pyplot as plt

    from .io import read_fits
    from .plotting import plot_dynamic_spectrum
    from .processing import mitigate_rfi, noise_reduce_mean_clip, noise_reduce_median_clip

    ds = read_fits(args.file)

    if args.rfi:
        ds = mitigate_rfi(ds)

    if args.process == "mean":
        ds = noise_reduce_mean_clip(ds, clip_low=args.clip_low, clip_high=args.clip_high)
        proc_mode = "raw"
    elif args.process == "median":
        ds = noise_reduce_median_clip(ds, clip_low=args.clip_low, clip_high=args.clip_high)
        proc_mode = "raw"
    else:
        proc_mode = args.process

    fig, ax, im = plot_dynamic_spectrum(
        ds,
        process=proc_mode,
        clip_low=None,
        clip_high=None,
        cmap=args.cmap,
        dpi=getattr(args, "dpi", 150.0),
        save_path=args.save,
        savefig_kwargs={"bbox_inches": "tight"} if args.save else None,
    )

    if args.save:
        print(f"Plot saved to {args.save}")
    else:
        plt.show()

def main():
    parser = argparse.ArgumentParser(description="e-CALLISTO Command Line Interface")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Download parser
    parser_down = subparsers.add_parser("download", help="Download FITS files")
    parser_down.add_argument("--date", required=True, help="Date in YYYY-MM-DD format")
    parser_down.add_argument("--hour", type=int, required=True, help="UTC hour (0-23)")
    parser_down.add_argument("--station", required=True, help="Station substring (e.g. 'alaska')")
    parser_down.add_argument("--out-dir", default="./data", help="Output directory")

    # Plot parser
    parser_plot = subparsers.add_parser("plot", help="Plot a FITS file")
    parser_plot.add_argument("file", help="Path to FITS file")
    parser_plot.add_argument("--process", choices=["raw", "mean", "median", "background_subtracted"], default="raw", help="Processing method")
    parser_plot.add_argument("--rfi", action="store_true", help="Apply RFI mitigation")
    parser_plot.add_argument("--clip-low", type=float, default=-5.0, help="Lower clipping threshold (required for mean/median)")
    parser_plot.add_argument("--clip-high", type=float, default=20.0, help="Upper clipping threshold (required for mean/median)")
    parser_plot.add_argument("--cmap", default="inferno", help="Colormap")
    parser_plot.add_argument("--dpi", type=float, default=150.0, help="Plot resolution")
    parser_plot.add_argument("--save", help="Path to save the plot image (if not set, shows interactive plot)")

    args = parser.parse_args()

    if args.command == "download":
        cmd_download(args)
    elif args.command == "plot":
        cmd_plot(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
