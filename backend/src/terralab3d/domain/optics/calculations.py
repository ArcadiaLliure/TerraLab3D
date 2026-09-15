"""Càlcul òptic pur, determinista i independent del render."""

from __future__ import annotations

import math

from terralab3d.domain.optics.models import (
    CameraCaptureSettings,
    CameraProfile,
    FieldOfView,
    FramingShape,
    OpticalInstrument,
    OpticalMetrics,
    SensorFormat,
    TelescopeSettings,
)

PIXEL_PITCH_TOLERANCE = 0.02
_TOLERANCE_EPSILON = 1e-12


class OpticalValidationError(ValueError):
    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field


def _positive(field: str, value: float) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise OpticalValidationError(field, f"{field} ha de ser finit i estrictament positiu")
    return number


def angular_field_deg(dimension_mm: float, focal_length_mm: float) -> float:
    dimension = _positive("sensorDimensionMm", dimension_mm)
    focal = _positive("focalLengthMm", focal_length_mm)
    return math.degrees(2.0 * math.atan(dimension / (2.0 * focal)))


def rectangular_solid_angle_sr(width_deg: float, height_deg: float) -> float:
    a = math.radians(_positive("fieldWidthDeg", width_deg)) / 2.0
    b = math.radians(_positive("fieldHeightDeg", height_deg)) / 2.0
    tan_a = math.tan(a)
    tan_b = math.tan(b)
    return 4.0 * math.atan((tan_a * tan_b) / math.sqrt(1.0 + tan_a**2 + tan_b**2))


def circular_solid_angle_sr(true_fov_deg: float) -> float:
    radius = math.radians(_positive("trueFovDeg", true_fov_deg)) / 2.0
    return 2.0 * math.pi * (1.0 - math.cos(radius))


def camera_field(profile: CameraProfile, settings: CameraCaptureSettings) -> FieldOfView:
    sensor = profile.sensor
    width = angular_field_deg(sensor.width_mm, settings.focal_length_mm)
    height = angular_field_deg(sensor.height_mm, settings.focal_length_mm)
    diagonal = angular_field_deg(math.hypot(sensor.width_mm, sensor.height_mm), settings.focal_length_mm)
    return FieldOfView(
        width_deg=width,
        height_deg=height,
        diagonal_deg=diagonal,
        aspect_ratio=sensor.width_mm / sensor.height_mm,
        solid_angle_sr=rectangular_solid_angle_sr(width, height),
        shape=FramingShape.RECTANGLE,
    )


def telescope_magnification(settings: TelescopeSettings) -> float:
    return _positive("focalLengthMm", settings.focal_length_mm) / _positive(
        "eyepieceFocalLengthMm", settings.eyepiece_focal_length_mm
    )


def telescope_field(settings: TelescopeSettings) -> FieldOfView:
    magnification = telescope_magnification(settings)
    true_fov = _positive("eyepieceAfovDeg", settings.eyepiece_afov_deg) / magnification
    return FieldOfView(
        width_deg=true_fov,
        height_deg=true_fov,
        diagonal_deg=true_fov,
        aspect_ratio=1.0,
        solid_angle_sr=circular_solid_angle_sr(true_fov),
        shape=FramingShape.CIRCLE,
    )


def telescope_metrics(settings: TelescopeSettings) -> OpticalMetrics:
    magnification = telescope_magnification(settings)
    aperture = _positive("apertureDiameterMm", settings.aperture_diameter_mm)
    true_fov = _positive("eyepieceAfovDeg", settings.eyepiece_afov_deg) / magnification
    return OpticalMetrics(
        magnification=magnification,
        exit_pupil_mm=aperture / magnification,
        true_fov_deg=true_fov,
    )


def camera_metrics(profile: CameraProfile, field: FieldOfView, focal_length_mm: float) -> OpticalMetrics:
    sensor = profile.sensor
    width_px = sensor.resolution_width_px
    height_px = sensor.resolution_height_px
    if (width_px is None) != (height_px is None):
        raise OpticalValidationError("resolution", "cal declarar resolució horitzontal i vertical")
    if width_px is not None and height_px is not None:
        width = _positive("resolutionWidthPx", width_px)
        height = _positive("resolutionHeightPx", height_px)
        pitch_x = 1000.0 * sensor.width_mm / width
        pitch_y = 1000.0 * sensor.height_mm / height
        _validate_declared_pitch(sensor, pitch_x, pitch_y)
        return OpticalMetrics(
            pixel_scale_x_arcsec=field.width_deg * 3600.0 / width,
            pixel_scale_y_arcsec=field.height_deg * 3600.0 / height,
        )
    focal = _positive("focalLengthMm", focal_length_mm)
    if sensor.square_pixels and sensor.pixel_pitch_um is not None:
        scale = 206.265 * _positive("pixelPitchUm", sensor.pixel_pitch_um) / focal
        return OpticalMetrics(pixel_scale_x_arcsec=scale, pixel_scale_y_arcsec=scale)
    if not sensor.square_pixels:
        if sensor.pixel_pitch_um is not None:
            raise OpticalValidationError("pixelPitchUm", "un pitch escalar no representa píxels no quadrats")
        if sensor.pixel_pitch_x_um is not None and sensor.pixel_pitch_y_um is not None:
            return OpticalMetrics(
                pixel_scale_x_arcsec=206.265 * _positive("pixelPitchXUm", sensor.pixel_pitch_x_um) / focal,
                pixel_scale_y_arcsec=206.265 * _positive("pixelPitchYUm", sensor.pixel_pitch_y_um) / focal,
            )
    return OpticalMetrics()


def _validate_declared_pitch(sensor: SensorFormat, pitch_x: float, pitch_y: float) -> None:
    if sensor.square_pixels:
        declared = sensor.pixel_pitch_um
        if declared is None:
            if abs(pitch_x - pitch_y) / max(pitch_x, pitch_y) > PIXEL_PITCH_TOLERANCE + _TOLERANCE_EPSILON:
                raise OpticalValidationError("squarePixels", "les dimensions declaren píxels no quadrats")
            return
        expected = _positive("pixelPitchUm", declared)
        if any(abs(actual - expected) / expected > PIXEL_PITCH_TOLERANCE + _TOLERANCE_EPSILON for actual in (pitch_x, pitch_y)):
            raise OpticalValidationError("pixelPitchUm", "pitch incompatible amb sensor i resolució")
        return
    if sensor.pixel_pitch_um is not None:
        raise OpticalValidationError("pixelPitchUm", "cal declarar pitch X/Y per a píxels no quadrats")
    if (sensor.pixel_pitch_x_um is None) != (sensor.pixel_pitch_y_um is None):
        raise OpticalValidationError("pixelPitch", "cal declarar pitch X i Y")
    if sensor.pixel_pitch_x_um is not None and sensor.pixel_pitch_y_um is not None:
        expected_x = _positive("pixelPitchXUm", sensor.pixel_pitch_x_um)
        expected_y = _positive("pixelPitchYUm", sensor.pixel_pitch_y_um)
        if abs(pitch_x - expected_x) / expected_x > PIXEL_PITCH_TOLERANCE + _TOLERANCE_EPSILON:
            raise OpticalValidationError("pixelPitchXUm", "pitch X incompatible")
        if abs(pitch_y - expected_y) / expected_y > PIXEL_PITCH_TOLERANCE + _TOLERANCE_EPSILON:
            raise OpticalValidationError("pixelPitchYUm", "pitch Y incompatible")


class OpticalGeometryCalculator:
    """Compatibilitat concreta amb el contracte provisional anterior."""

    def field_of_view(self, instrument: OpticalInstrument) -> FieldOfView:
        if instrument.kind.value == "camera" and instrument.sensor is not None:
            profile = CameraProfile("legacy", "Legacy", instrument.sensor)
            settings = CameraCaptureSettings("legacy", instrument.focal_length_mm, instrument.f_number or 1.0)
            return camera_field(profile, settings)
        return telescope_field(TelescopeSettings(
            instrument.focal_length_mm,
            instrument.aperture_diameter_mm or 1.0,
            instrument.eyepiece_focal_length_mm or 1.0,
        ))

    def magnification(self, instrument: OpticalInstrument) -> float | None:
        if instrument.kind.value != "telescope":
            return None
        return instrument.focal_length_mm / _positive("eyepieceFocalLengthMm", instrument.eyepiece_focal_length_mm or 0.0)

    def exit_pupil_mm(self, instrument: OpticalInstrument) -> float | None:
        magnification = self.magnification(instrument)
        if magnification is None or instrument.aperture_diameter_mm is None:
            return None
        return _positive("apertureDiameterMm", instrument.aperture_diameter_mm) / magnification
