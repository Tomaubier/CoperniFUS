Installation
------------

Tested on macOS 15, Ubuntu 24.04.2 LTS, Windows 10 & 11 using Python 3.12.

1. Make sure you have `Blender 4.1 <https://download.blender.org/release/Blender4.1/>`_ installed on your system. It will be used by `trimesh <https://trimesh.org>`_ to perform boolean operations.

**1a. For Ubuntu users:** Make sure that the path to the Blender is defined in the system ``PATH``. You can add it by running ``echo 'export PATH="/path/to/blender_executable_parent_dir:$PATH"'>>~/.bashrc``

2. Optional but highly recommended: setup a dedicated Python 3.12 environment (I recommended using `miniconda <https://docs.anaconda.com/miniconda/install/>`_)
    - Using `conda`: ``conda create -n coperniFUS_env python=3.12``
    - Activate the newly created environment using ``conda activate coperniFUS_env``
3. Install ``coperniFUS`` using ``pip`` (if you are using windows, you might need to install Git)
    - ``pip install git+https://github.com/Tomaubier/CoperniFUS.git``

**3a. For Ubuntu users:** Install ``libxcb-cursor-dev`` to satisfy ``PyQt6`` requirements ``sudo apt-get install -y libxcb-cursor-dev`` `see <https://stackoverflow.com/questions/77725761/from-6-5-0-xcb-cursor0-or-libxcb-cursor0-is-needed-to-load-the-qt-xcb-platform>`_ for additional details.

4. Launch ``coperniFUS`` by running ``coperniFUS`` in a terminal.

Alternative installation procedure for development purposes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

1. Same as in the regular installation procedure
2. Same as in the regular installation procedure. Although creating a dedicated environment for development would be recommanded. Feel free to create it using ``conda create -n coperniFUS_DEV_env python=3.12``.
3. `Fork CoperniFUS's repository <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo>`_
4. Clone your forked repository locally and proceed with the installation by running ``pip install -e .`` from the base directory.
This way, changes made to the source code will directly take effect when relauching CoperniFUS.

Troubleshooting
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

No backend found for boolean operations
+++++++++++++++++++++++++++++++++++++++++

1. Make sure that Blender is in the system PATH variable (please refer to Installation step 1b)
2. On linux you can check that Blender is correctly installed by running ``which blender`` in the terminal. The path to the executable should be returned. Additionaly, you can ensure that ``trimesh`` finds blender as its backend by running ``python`` in the terminal (with coperniFUS_env activated) and execute:

.. code-block:: python
    >>> import trimesh
    >>> trimesh.interfaces.blender.exists
    True

3. Check `this github issue <https://github.com/mikedh/trimesh/issues/333#issuecomment-657241179>`_ if the bug persists.