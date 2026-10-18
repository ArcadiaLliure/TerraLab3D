"""Fixtures d'integració amb assets reals, sense descàrregues implícites."""

import pytest


@pytest.fixture(scope="module")
def real_observation_and_response():
    from test_black_marble_simulation_step7_5_1 import read_real_pair

    observation, response, _ = read_real_pair()
    return observation, response
