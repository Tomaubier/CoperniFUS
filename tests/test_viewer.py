import pytest
from coperniFUS.viewer import Window, pyqtw

@pytest.fixture
def viewer_window(qtbot):
    """Fixture to create CoperniFUS viewer window."""
    window = Window(app=None, running_test=True)
    return window

def test_window_title(viewer_window):
    """Test the window title."""
    assert viewer_window.windowTitle() == "CoperniFUS"
