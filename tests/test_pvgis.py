import io
import json
import urllib.error

import pytest

from resize_energy.core.pvgis import PVGISError, build_url, fetch_pvcalc, parse_pvcalc

# Shape documented for the PVGIS PVcalc JSON output (only the fields RESize reads).
SAMPLE = {
    "inputs": {"location": {"latitude": 45.07, "longitude": 7.69}},
    "outputs": {
        "totals": {"fixed": {"E_y": 1200.0, "H(i)_y": 1500.0, "SD_y": 40.0}},
    },
}


def test_parse_pvcalc():
    r = parse_pvcalc(SAMPLE)
    assert r.annual_irradiation_kwh_m2 == pytest.approx(1500.0)
    assert r.annual_yield_kwh_per_kwp == pytest.approx(1200.0)
    assert r.implied_performance_ratio == pytest.approx(0.8)


def test_parse_pvcalc_scales_with_peak_power():
    data = {"outputs": {"totals": {"fixed": {"E_y": 2400.0, "H(i)_y": 1500.0}}}}
    assert parse_pvcalc(data, peakpower_kw=2.0).annual_yield_kwh_per_kwp == pytest.approx(1200.0)


@pytest.mark.parametrize("bad", [{}, {"outputs": {}}, {"outputs": {"totals": {"fixed": {}}}}])
def test_parse_pvcalc_rejects_unexpected_format(bad):
    with pytest.raises(PVGISError):
        parse_pvcalc(bad)


def test_build_url_contains_parameters():
    url = build_url(45.07, 7.69, tilt_deg=30, azimuth_deg=-10, loss_pct=14)
    assert url.startswith("https://re.jrc.ec.europa.eu/api/")
    for part in ("lat=45.07000", "lon=7.69000", "angle=30", "aspect=-10", "outputformat=json"):
        assert part in url


def test_build_url_rejects_invalid_coordinates():
    with pytest.raises(ValueError):
        build_url(95, 0, 30, 0)


def _http_error(url, code, body=b""):
    return urllib.error.HTTPError(url, code, "err", {}, io.BytesIO(body))


def test_fetch_falls_back_to_next_endpoint_on_403():
    calls = []

    def fake_urlopen(request, timeout=None):
        calls.append(request.full_url)
        if len(calls) == 1:
            raise _http_error(request.full_url, 403)
        return io.BytesIO(json.dumps(SAMPLE).encode())

    r = fetch_pvcalc(45.07, 7.69, 30, 0, urlopen=fake_urlopen)
    assert len(calls) == 2
    assert "v5_3" in calls[0] and "v5_2" in calls[1]
    assert r.annual_irradiation_kwh_m2 == pytest.approx(1500.0)


def test_fetch_reports_server_message_when_all_endpoints_refuse():
    def fake_urlopen(request, timeout=None):
        raise _http_error(request.full_url, 403, b'{"message": "blocked"}')

    with pytest.raises(PVGISError) as info:
        fetch_pvcalc(45.07, 7.69, 30, 0, urlopen=fake_urlopen)
    assert "403" in str(info.value)
    assert "blocked" in str(info.value)


def test_fetch_busy_server_does_not_try_other_endpoints():
    calls = []

    def fake_urlopen(request, timeout=None):
        calls.append(1)
        raise _http_error(request.full_url, 529)

    with pytest.raises(PVGISError):
        fetch_pvcalc(45.07, 7.69, 30, 0, urlopen=fake_urlopen)
    assert len(calls) == 1


def test_parse_reports_server_message():
    with pytest.raises(PVGISError) as info:
        parse_pvcalc({"message": "lat: out of range", "status": 400})
    assert "out of range" in str(info.value)


def test_fetch_retries_other_headers_when_reply_is_empty():
    calls = []

    def fake_urlopen(request, timeout=None):
        calls.append(request.get_header("Accept"))
        if len(calls) == 1:
            return io.BytesIO(b"")
        return io.BytesIO(json.dumps(SAMPLE).encode())

    r = fetch_pvcalc(45.07, 7.69, 30, 0, urlopen=fake_urlopen)
    assert len(calls) == 2
    assert calls[0] == "application/json" and calls[1] == "*/*"
    assert r.annual_irradiation_kwh_m2 == pytest.approx(1500.0)


def test_fetch_non_json_reply_shows_the_start_of_the_body():
    def fake_urlopen(request, timeout=None):
        return io.BytesIO(b"<html><body>Access denied by firewall</body></html>")

    with pytest.raises(PVGISError) as info:
        fetch_pvcalc(45.07, 7.69, 30, 0, urlopen=fake_urlopen)
    message = str(info.value)
    assert "did not return JSON" in message
    assert "Access denied by firewall" in message


def test_fetch_non_json_empty_reply_is_described():
    def fake_urlopen(request, timeout=None):
        return io.BytesIO(b"")

    with pytest.raises(PVGISError) as info:
        fetch_pvcalc(45.07, 7.69, 30, 0, urlopen=fake_urlopen)
    assert "empty reply" in str(info.value)


def test_fetch_accepts_json_with_byte_order_mark():
    def fake_urlopen(request, timeout=None):
        return io.BytesIO(b"\xef\xbb\xbf" + json.dumps(SAMPLE).encode())

    r = fetch_pvcalc(45.07, 7.69, 30, 0, urlopen=fake_urlopen)
    assert r.implied_performance_ratio == pytest.approx(0.8)
