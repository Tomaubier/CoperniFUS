import pytest
from coperniFUS.viewer import Window, pyqtw

@pytest.fixture
def viewer_window(qtbot):
    """ Fixture to create CoperniFUS viewer window. """
    window = Window(app=None)
    return window

def test_brain_atlas(viewer_window):
    """ Test that the example mouse atlas has been loaded."""
    batlas_module = viewer_window.get_module_object_from_name('BrainAtlas') # Get BrainAtlasModule handle
    batlas_module.add_reference_atlas('example_mouse_100um') # Loading demo atlas
    batlas_module.add_structure_layer(structure='Cerebrum (CH)', hemisphere='Left Hemisphere') # Loading a brain structure
    assert len(batlas_module.layers) == 2

# TODO implement more