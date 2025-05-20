import sys, argparse
from coperniFUS.viewer import coperniFUSviewer

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--assets_dir_path', dest='assets_dir_path', type=str, help='Specify the directory from which armature assets (stl mesh files, reference images, etc.) will be loaded. Defaults to coperniFUS/example_assets if no path is provided')
    parser.add_argument('--disable_internal_console', dest='disable_internal_console', type=bool, help='Disable internal console to prevent CoperniFUS from redirecting stdout.')
    args = parser.parse_args()

    coperniFUSviewer(assets_dir_path=args.assets_dir_path, disable_internal_console=args.disable_internal_console)

if __name__ == '__main__':
    sys.exit(main())
