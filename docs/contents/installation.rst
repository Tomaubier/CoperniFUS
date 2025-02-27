Installation
------------

Tested on macOS 15, Windows 10 & 11 using Python 3.12.

1. Make sure you have `Blender 4.1 <https://download.blender.org/release/Blender4.1/>`_ installed on your system. It will be used by `trimesh <https://trimesh.org>`_ to perform boolean operations.
2. Optional but highly recommended: setup a dedicated Python 3.12 environment (I recommended using `miniconda <https://docs.anaconda.com/miniconda/install/>`_)
    - Using `conda`: ``conda create -n coperniFUS_env python=3.12``
    - Activate the newly created environment using ``conda activate coperniFUS_env``
3. Install ``coperniFUS`` using ``pip`` (if you are using windows, you might need to install Git)
    - ``pip install git+https://github.com/Tomaubier/CoperniFUS.git``
4. Launch ``coperniFUS`` by running ``coperniFUS`` in a terminal.