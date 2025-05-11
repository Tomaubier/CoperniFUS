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

Alternative installation procedure for development purposes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Same as in the regular installation procedure
2. Same as in the regular installation procedure. Although creating a dedicated environment for development would be recommanded. Feel free to create it using ``conda create -n coperniFUS_DEV_env python=3.12``.
3. `Fork CoperniFUS's repository <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo>`_
4. Clone your forked repository locally and proceed with the installation by running ``pip install -e .`` from the base directory.
This way, changes made to the source code will directly take effect when relauching CoperniFUS.