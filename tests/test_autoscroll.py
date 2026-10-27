from resize_energy.gui.zone_layout import autoscroll_step


def test_no_scroll_in_the_middle():
    assert autoscroll_step(400, 0, 800) == 0


def test_scrolls_up_near_the_top_and_down_near_the_bottom():
    assert autoscroll_step(10, 0, 800) < 0
    assert autoscroll_step(790, 0, 800) > 0


def test_step_grows_towards_the_edge_and_is_capped():
    near = abs(autoscroll_step(80, 0, 800))
    edge = abs(autoscroll_step(0, 0, 800))
    beyond = abs(autoscroll_step(-200, 0, 800))
    assert 0 < near < edge == beyond == 26


def test_small_view_still_has_a_dead_zone():
    assert autoscroll_step(50, 0, 100) == 0
    assert autoscroll_step(0, 0, 100) < 0
