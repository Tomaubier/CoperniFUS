import sys, argparse
from coperniFUS.viewer import coperniFUSviewer

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--assets_dir_path', dest='assets_dir_path', type=str, help='Specify the directory from which armature assets (stl mesh files, reference images, etc.) will be loaded. Defaults to coperniFUS/example_assets if no path is provided')
    parser.add_argument('--disable_internal_console', dest='disable_internal_console', type=bool, help='Disable internal console to prevent CoperniFUS from redirecting stdout.')
    parser.add_argument('--skip_online_atlas_retreival', dest='skip_online_atlas_retreival', type=bool, help='Prevents BrainGlobeAtlas API from requesting altases available online. Try setting this option to True if CoperniFUS GUI fails to open.')
    parser.add_argument('--disable_threaded_wrappers', dest='disable_threaded_wrappers', type=bool, help='Prevents CoperniFUS from running long operations in a asynchronous way.')
    args = parser.parse_args()

    coperniFUSviewer(assets_dir_path=args.assets_dir_path, disable_internal_console=args.disable_internal_console, skip_online_atlas_retreival=args.skip_online_atlas_retreival)

if __name__ == '__main__':
    sys.exit(main())
