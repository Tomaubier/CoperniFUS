Installation
------------

.. role:: raw-html(raw)
    :format: html

Tested on macOS 15, Ubuntu 24.04.2 LTS, Linux Mint 21.1, Windows 10 & 11 using Python 3.12.

0. Optional but highly recommended: setup a dedicated Python 3.12 environment (I recommended using `miniconda <https://docs.anaconda.com/miniconda/install/>`_) :raw-html:`<br />` - Using `conda`: ``conda create -n coperniFUS_env python=3.12`` :raw-html:`<br />` - Activate the newly created environment using ``conda activate coperniFUS_env``
1. Install ``coperniFUS`` using ``pip`` (if you are using windows, you might need to install Git) :raw-html:`<br />` - ``pip install git+https://github.com/Tomaubier/CoperniFUS.git``

    1a. *For Linux users:* Install ``libxcb-cursor-dev`` to satisfy ``PyQt6`` requirements ``sudo apt-get install -y libxcb-cursor-dev`` `see this post <https://stackoverflow.com/questions/77725761/from-6-5-0-xcb-cursor0-or-libxcb-cursor0-is-needed-to-load-the-qt-xcb-platform>`_ for additional details.

    1b. *For macOS users:* ``k-wave-python`` currently requiers ``fftw hdf5 zlib libomp`` to be installed. This requirement con be satisfied by running ``brew install fftw hdf5 zlib libomp`` using `Homebrew <https://docs.brew.sh/Installation>`_. `See this k-wave-python issue <https://github.com/waltsims/k-wave-python/issues/549>`_ for additional details.

2. Launch ``coperniFUS`` by running ``coperniFUS`` in a terminal. Checkout `this section <usage.rst>`_ for detailed usage instructions.

Alternative installation procedure for development purposes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

0. Same as in the regular installation procedure. Although creating a dedicated environment for development would be recommanded. Feel free to create it using ``conda create -n coperniFUS_DEV_env python=3.12``.
1. `Fork CoperniFUS's repository <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/fork-a-repo>`_
2. Clone your forked repository locally and proceed with the installation by running ``pip install -e .`` from the base directory.

This way, changes made to the source code will directly take effect when relauching CoperniFUS.

.. _running_autonatic_test:

Running automated tests
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In an environnement where CoperniFUS is installed:

1. Install testing dependencies ``pip install pytest pytest-qt``
2. Run ``pytest tests/test_viewer.py``