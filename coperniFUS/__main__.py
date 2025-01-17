from coperniFUS.viewer import coperniFUSviewer
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--assets_dir_path', dest='assets_dir_path', type=str, help='Specify the directory from which armature assets (stl mesh files, reference images, etc.) will be loaded. Defaults to coperniFUS/example_assets if no path is provided')
    args = parser.parse_args()

    coperniFUSviewer(assets_dir_path=args.assets_dir_path)

if __name__ == '__main__':
    sys.exit(main())
