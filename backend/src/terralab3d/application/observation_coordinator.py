"""Orquestració autoritativa dels modes i instruments d'observació."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, replace
from enum import Enum
from typing import Any, Awaitable, Callable

from terralab3d.application.ports.persistence import PreferencesPort
from terralab3d.domain.imaging.calculations import PhotographicLimitingMagnitudeModelV1
from terralab3d.domain.imaging.models import PhotographicLimitingMagnitudeInputs
from terralab3d.domain.optics.calculations import (
    OpticalValidationError,
    camera_field,
    camera_metrics,
    telescope_field,
    telescope_metrics,
)
from terralab3d.domain.optics.models import (
    CameraCaptureSettings,
    CameraProfile,
    DeepCatalogStatus,
    ObservationMode,
    ObservationSnapshot,
    OpticalMetrics,
    SensorFormat,
    TelescopeSettings,
)

log = logging.getLogger("terralab3d.observation")
SnapshotPublisher = Callable[[dict[str, Any]], Awaitable[None]]

APS_C_ID = "camera:aps-c"
FULL_FRAME_ID = "camera:full-frame"
PREFERENCES_KEY = "camera_profiles"


class ObservationCoordinator:
    """Valida mutacions, persisteix preferències i publica snapshots complets."""

    def __init__(self, preferences: PreferencesPort, publish: SnapshotPublisher) -> None:
        self._preferences = preferences
        self._publish = publish
        self._revision = 0
        self._mode = ObservationMode.EYE
        self._camera = CameraCaptureSettings(selected_profile_id=APS_C_ID)
        self._telescope = TelescopeSettings()
        self._profiles: dict[str, CameraProfile] = {
            APS_C_ID: CameraProfile(APS_C_ID, "APS-C", SensorFormat("aps_c", 23.6, 15.7), True),
            FULL_FRAME_ID: CameraProfile(FULL_FRAME_ID, "Full Frame", SensorFormat("full_frame", 36.0, 24.0), True),
        }
        self._warning: str | None = None
        self._deep_status = DeepCatalogStatus()
        self._photometry = PhotographicLimitingMagnitudeModelV1()
        self._atmospheric_loss_mag = 0.20
        self._eye_limit_mag = 6.1
        self._load_preferences()

    @property
    def snapshot(self) -> ObservationSnapshot:
        field = None
        metrics = OpticalMetrics()
        preview = None
        if self._mode is ObservationMode.CAMERA:
            profile = self._profiles[self._camera.selected_profile_id]
            field = camera_field(profile, self._camera)
            metrics = camera_metrics(profile, field, self._camera.focal_length_mm)
            preview = self._photometry.compute(PhotographicLimitingMagnitudeInputs(
                focal_length_mm=self._camera.focal_length_mm,
                f_number=self._camera.f_number,
                iso=self._camera.iso,
                exposure_seconds=self._camera.exposure_seconds,
                atmospheric_loss_magnitude=self._atmospheric_loss_mag,
                eye_limit_magnitude=self._eye_limit_mag,
                optical_transmission=self._camera.optical_transmission,
            ))
        elif self._mode is ObservationMode.TELESCOPE:
            field = telescope_field(self._telescope)
            metrics = telescope_metrics(self._telescope)
        return ObservationSnapshot(
            schema_version=1,
            observation_revision=self._revision,
            mode=self._mode,
            camera_profiles=tuple(self._profiles.values()),
            camera=self._camera,
            telescope=self._telescope,
            field=field,
            metrics=metrics,
            photographic_preview=preview,
            deep_catalog=self._deep_status,
            warning=self._warning,
        )

    @property
    def observation_revision(self) -> int:
        return self._revision

    async def publish_current(self) -> None:
        await self._publish(self.to_payload(self.snapshot))

    async def set_mode(self, mode: str) -> None:
        candidate = ObservationMode(mode)
        if candidate is not self._mode:
            self._mode = candidate
            self._revision += 1
        await self.publish_current()

    async def configure_camera(self, data: dict[str, Any]) -> None:
        profile_id = str(data.get("selectedProfileId", self._camera.selected_profile_id))
        if profile_id not in self._profiles:
            raise OpticalValidationError("selectedProfileId", "perfil de càmera desconegut")
        candidate = CameraCaptureSettings(
            selected_profile_id=profile_id,
            focal_length_mm=float(data.get("focalLengthMm", self._camera.focal_length_mm)),
            f_number=float(data.get("fNumber", self._camera.f_number)),
            iso=float(data.get("iso", self._camera.iso)),
            exposure_seconds=float(data.get("exposureSeconds", self._camera.exposure_seconds)),
            tracking_enabled=bool(data.get("trackingEnabled", self._camera.tracking_enabled)),
            frame_rotation_deg=float(data.get("frameRotationDeg", self._camera.frame_rotation_deg)),
            optical_transmission=self._optional_float(data.get("opticalTransmission", self._camera.optical_transmission)),
        )
        if not -180.0 <= candidate.frame_rotation_deg <= 180.0:
            raise OpticalValidationError("frameRotationDeg", "la rotació del marc ha d'estar entre -180° i 180°")
        profile = self._profiles[profile_id]
        field = camera_field(profile, candidate)
        camera_metrics(profile, field, candidate.focal_length_mm)
        self._photometry.compute(PhotographicLimitingMagnitudeInputs(
            candidate.focal_length_mm, candidate.f_number, candidate.iso,
            candidate.exposure_seconds, self._atmospheric_loss_mag,
            self._eye_limit_mag, candidate.optical_transmission,
        ))
        previous_profile = self._camera.selected_profile_id
        self._camera = candidate
        self._revision += 1
        if profile_id != previous_profile:
            self._save_preferences()
        await self.publish_current()

    async def configure_telescope(self, data: dict[str, Any]) -> None:
        candidate = TelescopeSettings(
            focal_length_mm=float(data.get("focalLengthMm", self._telescope.focal_length_mm)),
            aperture_diameter_mm=float(data.get("apertureDiameterMm", self._telescope.aperture_diameter_mm)),
            eyepiece_focal_length_mm=float(data.get("eyepieceFocalLengthMm", self._telescope.eyepiece_focal_length_mm)),
            eyepiece_afov_deg=float(data.get("eyepieceAfovDeg", self._telescope.eyepiece_afov_deg)),
        )
        telescope_field(candidate)
        telescope_metrics(candidate)
        self._telescope = candidate
        self._revision += 1
        await self.publish_current()

    async def create_profile(self, data: dict[str, Any]) -> None:
        profile_id = f"camera:user:{uuid.uuid4()}"
        profile = self._profile_from_payload(data, profile_id)
        field = camera_field(profile, replace(self._camera, selected_profile_id=profile_id))
        camera_metrics(profile, field, self._camera.focal_length_mm)
        self._profiles[profile_id] = profile
        self._camera = replace(self._camera, selected_profile_id=profile_id)
        self._save_preferences()
        self._revision += 1
        await self.publish_current()

    async def update_profile(self, profile_id: str, data: dict[str, Any]) -> None:
        current = self._profiles.get(profile_id)
        if current is None or current.built_in:
            raise OpticalValidationError("profileId", "només es poden editar perfils personals")
        profile = self._profile_from_payload(data, profile_id)
        field = camera_field(profile, replace(self._camera, selected_profile_id=profile_id))
        camera_metrics(profile, field, self._camera.focal_length_mm)
        self._profiles[profile_id] = profile
        self._save_preferences()
        self._revision += 1
        await self.publish_current()

    async def delete_profile(self, profile_id: str) -> None:
        profile = self._profiles.get(profile_id)
        if profile is None or profile.built_in:
            raise OpticalValidationError("profileId", "només es poden eliminar perfils personals")
        del self._profiles[profile_id]
        if self._camera.selected_profile_id == profile_id:
            self._camera = replace(self._camera, selected_profile_id=APS_C_ID)
        self._save_preferences()
        self._revision += 1
        await self.publish_current()

    async def set_deep_status(self, status: DeepCatalogStatus) -> None:
        self._deep_status = status
        await self.publish_current()

    async def update_environment(self, atmospheric_loss_mag: float, eye_limit_mag: float) -> bool:
        atmosphere = max(0.0, float(atmospheric_loss_mag))
        eye_limit = float(eye_limit_mag)
        if abs(atmosphere - self._atmospheric_loss_mag) < 1e-9 and abs(eye_limit - self._eye_limit_mag) < 1e-9:
            return False
        self._atmospheric_loss_mag = atmosphere
        self._eye_limit_mag = eye_limit
        self._revision += 1
        await self.publish_current()
        return True

    def _profile_from_payload(self, data: dict[str, Any], profile_id: str) -> CameraProfile:
        name = str(data.get("name", "")).strip()
        if not name:
            raise OpticalValidationError("name", "el nom del perfil és obligatori")
        sensor = SensorFormat(
            key="custom",
            width_mm=float(data["widthMm"]),
            height_mm=float(data["heightMm"]),
            resolution_width_px=self._optional_int(data.get("resolutionWidthPx")),
            resolution_height_px=self._optional_int(data.get("resolutionHeightPx")),
            square_pixels=bool(data.get("squarePixels", True)),
            pixel_pitch_um=self._optional_float(data.get("pixelPitchUm")),
            pixel_pitch_x_um=self._optional_float(data.get("pixelPitchXUm")),
            pixel_pitch_y_um=self._optional_float(data.get("pixelPitchYUm")),
        )
        return CameraProfile(profile_id, name, sensor, False)

    def _load_preferences(self) -> None:
        try:
            raw = self._preferences.load_text(PREFERENCES_KEY)
            if raw is None:
                return
            payload = json.loads(raw)
            if payload.get("schemaVersion") != 1:
                raise ValueError("versió no compatible")
            for item in payload.get("profiles", []):
                profile_id = str(item["profileId"])
                if profile_id.startswith("camera:user:"):
                    self._profiles[profile_id] = self._profile_from_payload(item, profile_id)
            selected = str(payload.get("selectedCameraProfileId", APS_C_ID))
            if selected in self._profiles:
                self._camera = replace(self._camera, selected_profile_id=selected)
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            self._warning = "No s'han pogut carregar els perfils de càmera; s'utilitzen els presets integrats."
            log.warning("MGP: [ObservationCoordinator] [load_preferences] [%s]", exc)

    def _save_preferences(self) -> None:
        profiles = []
        for profile in self._profiles.values():
            if profile.built_in:
                continue
            sensor = profile.sensor
            profiles.append({
                "profileId": profile.profile_id, "name": profile.name,
                "widthMm": sensor.width_mm, "heightMm": sensor.height_mm,
                "resolutionWidthPx": sensor.resolution_width_px,
                "resolutionHeightPx": sensor.resolution_height_px,
                "squarePixels": sensor.square_pixels,
                "pixelPitchUm": sensor.pixel_pitch_um,
                "pixelPitchXUm": sensor.pixel_pitch_x_um,
                "pixelPitchYUm": sensor.pixel_pitch_y_um,
            })
        self._preferences.save_text(PREFERENCES_KEY, json.dumps({
            "schemaVersion": 1,
            "selectedCameraProfileId": self._camera.selected_profile_id,
            "profiles": profiles,
        }, ensure_ascii=False, indent=2))

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        return None if value is None or value == "" else float(value)

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        return None if value is None or value == "" else int(value)

    @staticmethod
    def to_payload(snapshot: ObservationSnapshot) -> dict[str, Any]:
        payload = _camelize(asdict(snapshot))
        payload["type"] = "observation_snapshot"
        return payload


def _camelize(value: Any) -> Any:
    if isinstance(value, dict):
        return {_camel_key(key): _camelize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_camelize(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    return value


def _camel_key(key: str) -> str:
    head, *tail = key.split("_")
    return head + "".join(part.capitalize() for part in tail)
