import pytest
from coperniFUS.viewer import Window, pyqtw

@pytest.fixture
def viewer_window(qtbot):
    """Fixture to create CoperniFUS viewer window."""
    window = Window(app=None, running_test=True)
    return window

def test_brain_atlas(viewer_window):
    """Test tha the example atlas has been loaded."""
    assert viewer_window.windowTitle() == "CoperniFUS"
    # assert viewer_window.get_module_object_from_name('BrainAtlas').bg_atlas.atlas_name == 'example_mouse_100um'

