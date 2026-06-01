"""Tests for path-type-aware MechanicalUnit spectrum selection."""

import json
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from calculations.mechanical_spectrum_select import (
    mechanical_unit_spectrum_for_path,
    parse_mechanical_unit_json_to_bands,
    spectrum_origin_sequence,
)


def _unit(outlet=None, inlet=None, radiated=None):
    return SimpleNamespace(
        outlet_levels_json=outlet,
        inlet_levels_json=inlet,
        radiated_levels_json=radiated,
        name="MU-1",
    )


def test_parse_valid_dict():
    js = json.dumps({"63": 1, "125": 2, "250": 3, "500": 4, "1000": 5, "2000": 6, "4000": 7, "8000": 8})
    bands = parse_mechanical_unit_json_to_bands(js)
    assert bands == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]


def test_supply_prefers_outlet():
    o = json.dumps({"63": 10, "125": 10, "250": 10, "500": 10, "1000": 10, "2000": 10, "4000": 10, "8000": 10})
    i = json.dumps({"63": 20, "125": 20, "250": 20, "500": 20, "1000": 20, "2000": 20, "4000": 20, "8000": 20})
    u = _unit(outlet=o, inlet=i, radiated=None)
    bands, origin = mechanical_unit_spectrum_for_path(u, "supply", "auto")
    assert origin == "outlet"
    assert bands[0] == 10.0


def test_return_prefers_inlet():
    o = json.dumps({"63": 10, "125": 10, "250": 10, "500": 10, "1000": 10, "2000": 10, "4000": 10, "8000": 10})
    i = json.dumps({"63": 20, "125": 20, "250": 20, "500": 20, "1000": 20, "2000": 20, "4000": 20, "8000": 20})
    u = _unit(outlet=o, inlet=i, radiated=None)
    bands, origin = mechanical_unit_spectrum_for_path(u, "return", "auto")
    assert origin == "inlet"
    assert bands[0] == 20.0


def test_exhaust_like_supply_uses_outlet_first():
    o = json.dumps({"63": 5, "125": 5, "250": 5, "500": 5, "1000": 5, "2000": 5, "4000": 5, "8000": 5})
    i = json.dumps({"63": 99, "125": 99, "250": 99, "500": 99, "1000": 99, "2000": 99, "4000": 99, "8000": 99})
    u = _unit(outlet=o, inlet=i, radiated=None)
    bands, origin = mechanical_unit_spectrum_for_path(u, "exhaust", "auto")
    assert origin == "outlet"
    assert bands[0] == 5.0


def test_supply_falls_back_to_inlet_then_radiated():
    i = json.dumps({"63": 2, "125": 2, "250": 2, "500": 2, "1000": 2, "2000": 2, "4000": 2, "8000": 2})
    r = json.dumps({"63": 3, "125": 3, "250": 3, "500": 3, "1000": 3, "2000": 3, "4000": 3, "8000": 3})
    u = _unit(outlet=None, inlet=i, radiated=r)
    bands, origin = mechanical_unit_spectrum_for_path(u, "supply", "auto")
    assert origin == "inlet"
    u2 = _unit(outlet=None, inlet=None, radiated=r)
    bands2, origin2 = mechanical_unit_spectrum_for_path(u2, "supply", "auto")
    assert origin2 == "radiated"
    assert bands2[0] == 3.0


def test_preference_radiated_first_on_supply():
    o = json.dumps({"63": 1, "125": 1, "250": 1, "500": 1, "1000": 1, "2000": 1, "4000": 1, "8000": 1})
    r = json.dumps({"63": 7, "125": 7, "250": 7, "500": 7, "1000": 7, "2000": 7, "4000": 7, "8000": 7})
    u = _unit(outlet=o, inlet=None, radiated=r)
    bands, origin = mechanical_unit_spectrum_for_path(u, "supply", "radiated")
    assert origin == "radiated"
    assert bands[0] == 7.0


def test_preference_empty_radiated_falls_back():
    o = json.dumps({"63": 1, "125": 1, "250": 1, "500": 1, "1000": 1, "2000": 1, "4000": 1, "8000": 1})
    u = _unit(outlet=o, inlet=None, radiated=None)
    bands, origin = mechanical_unit_spectrum_for_path(u, "supply", "radiated")
    assert origin == "outlet"
    assert bands[0] == 1.0


def test_spectrum_origin_sequence_preferred_first():
    assert spectrum_origin_sequence("return", "outlet")[0] == "outlet"
    assert spectrum_origin_sequence("supply", "inlet")[0] == "inlet"


@pytest.mark.parametrize("bad", ["", None, "{"])
def test_parse_rejects_invalid(bad):
    assert parse_mechanical_unit_json_to_bands(bad) is None
