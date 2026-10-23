from resize_energy.gui import icon_shapes as ic


def test_every_technology_has_an_icon():
    for key in ("pv", "wind", "biomass", "hydrogen", "battery"):  # keys used by gui/home.py
        assert key in ic.ICONS, key


def test_icon_points_stay_inside_the_grid():
    for key, shapes in ic.ICONS.items():
        assert shapes, key
        for points, _closed, _filled in shapes:
            assert len(points) >= 2
            for x, y in points:
                assert 0 <= x <= ic.GRID and 0 <= y <= ic.GRID, (key, x, y)


def test_cubic_ends_at_the_last_control_point():
    pts = ic.cubic((0, 0), (1, 2), (3, 2), (4, 0))
    assert pts[-1] == (4.0, 0.0)
