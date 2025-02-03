import weakref

import pyqtgraph as pg

pg.mkQApp()

def test_getViewWidget():
    view = pg.PlotWidget()
    vref = weakref.ref(view)
    item = pg.InfiniteLine()
    view.addItem(item)
    assert item.getViewWidget() is view
    del view
    assert vref() is None
    assert item.getViewWidget() is None

def test_getViewWidget_deleted():
    view = pg.PlotWidget()
    item = pg.InfiniteLine()
    view.addItem(item)
    assert item.getViewWidget() is view
    
    # Arrange to have Qt automatically delete the view widget
    obj = pg.QtWidgets.QWidget()
    view.setParent(obj)
    del obj

    assert not pg.Qt.isQObjectAlive(view)
    assert item.getViewWidget() is None

# import pytest
# from coperniFUS.viewer import Window, pyqtw

# @pytest.fixture
# def viewer_window(qtbot):
#     """Fixture to create CoperniFUS viewer window."""
#     window = Window(app=None, running_test=True)
#     return window

# def test_brain_atlas(viewer_window):
#     """Test tha the example atlas has been loaded."""
#     assert viewer_window.windowTitle() == "CoperniFUS"
#     # assert viewer_window.get_module_object_from_name('BrainAtlas').bg_atlas.atlas_name == 'example_mouse_100um'

