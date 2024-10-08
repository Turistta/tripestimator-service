from json import JSONDecodeError

import pytest

from models.route_models import Route, Transportation, TransportationMode
from models.utils_models import Coordinates
from parsers.route_parsers import RouteParser


class TestRouteParser:

    @pytest.fixture
    def valid_response(self):
        return """
        {
            "routes": [{
                "legs": [{
                    "startLocation": {"latLng": {"latitude": 40.7128, "longitude": -74.0060}},
                    "endLocation": {"latLng": {"latitude": 34.0522, "longitude": -118.2437}}
                }],
                "distanceMeters": 3935745,
                "duration": "12960s",
                "polyline": {"encodedPolyline": "ayusdgfyuiasdfY`GsDeB"},
                "travelAdvisory": {
                    "transitFare": {"units": 50, "nanos": 990000000},
                    "fuelConsumptionMicroliters": 150000
                }
            }]
        }
        """

    def test_successful_parse(self, valid_response):
        parser = RouteParser()
        result = parser.parse(valid_response, TransportationMode.CAR)

        assert isinstance(result, Route)
        assert result.origin == Coordinates(latitude=40.7128, longitude=-74.0060)
        assert result.destination == Coordinates(latitude=34.0522, longitude=-118.2437)
        assert result.polyline == "ayusdgfyuiasdfY`GsDeB"
        assert result.duration == 216.0  # 12960 seconds / 60
        assert result.distance == 3935745
        assert isinstance(result.transportation, Transportation)
        assert result.transportation.mode == TransportationMode.CAR
        assert result.transportation.fare == 50.99
        assert result.transportation.details == 150000

    def test_missing_fields(self):
        parser = RouteParser()

        response = (
            '{"routes": [{"legs": [{"endLocation": {"latLng": {"latitude": 34.0522, "longitude": -118.2437}}}],'
            + ' "polyline": {"encodedPolyline": "encodedPolyline"}}]}'
        )
        with pytest.raises(ValueError, match="Missing required fields: origin, destination, or polyline."):
            parser.parse(response, TransportationMode.CAR)

        response = (
            '{"routes": [{"legs": [{"startLocation": {"latLng": {"latitude": 40.7128, "longitude": -74.0060}}}],'
            + ' "polyline": {"encodedPolyline": "encodedPolyline"}}]}'
        )
        with pytest.raises(ValueError, match="Missing required fields: origin, destination, or polyline."):
            parser.parse(response, TransportationMode.CAR)

        response = (
            '{"routes": [{"legs": [{"startLocation": {"latLng": {"latitude": 40.7128, "longitude": -74.0060}},'
            + ' "endLocation": {"latLng": {"latitude": 34.0522, "longitude": -118.2437}}}]}]}'
        )
        with pytest.raises(ValueError, match="Missing required fields: origin, destination, or polyline."):
            parser.parse(response, TransportationMode.CAR)

    def test_invalid_json(self):
        parser = RouteParser()
        invalid_response = "{invalid json}}"

        with pytest.raises(JSONDecodeError):
            parser.parse(invalid_response, TransportationMode.CAR)

    @pytest.mark.parametrize("transport_mode", list(TransportationMode))
    def test_different_transport_modes(self, valid_response, transport_mode):
        parser = RouteParser()
        result = parser.parse(valid_response, transport_mode)

        assert isinstance(result, Route)
        assert result.transportation.mode == transport_mode

    def test_no_fare(self, valid_response):
        parser = RouteParser()
        response = valid_response.replace('"transitFare": {"units": 50, "nanos": 990000000},', "")
        result = parser.parse(response, TransportationMode.CAR)

        assert result.transportation.fare == 0.0

    def test_no_fuel_consumption(self, valid_response):
        parser = RouteParser()
        response = valid_response.replace(
            '"transitFare": {"units": 50, "nanos": 990000000},', '"transitFare": {"units": 50, "nanos": 990000000}'
        )
        response = response.replace('"fuelConsumptionMicroliters": 150000', "")
        result = parser.parse(response, TransportationMode.CAR)

        assert result.transportation.details is None
