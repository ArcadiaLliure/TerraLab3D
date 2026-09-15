import type { AngularCoordinate, MeasurementGeometrySnapshot, MeasurementKind } from "../contracts/measurement_contracts";

type Vector3 = readonly [number, number, number];

export function angularDistanceDeg(a: AngularCoordinate, b: AngularCoordinate): number {
  const first = unit(a); const second = unit(b);
  return toDeg(Math.atan2(norm(cross(first, second)), dot(first, second)));
}

export function rotateCoordinatePair(start: AngularCoordinate, end: AngularCoordinate, from: AngularCoordinate, to: AngularCoordinate): readonly [AngularCoordinate, AngularCoordinate] {
  const source = unit(from); const destination = unit(to); const rawAxis = cross(source, destination); const sine = norm(rawAxis);
  if (sine < 1e-12) return [start, end];
  const axis = scale(rawAxis, 1 / sine); const angle = Math.atan2(sine, clamp(dot(source, destination), -1, 1));
  return [coordinate(rodrigues(unit(start), axis, angle)), coordinate(rodrigues(unit(end), axis, angle))];
}

export function previewGeometry(kind: MeasurementKind, start: AngularCoordinate, end: AngularCoordinate, rotationDeg = 0, segments = 48): MeasurementGeometrySnapshot | null {
  const distance = angularDistanceDeg(start, end);
  if (!Number.isFinite(distance) || distance <= 1e-9) return null;
  if (kind === "ruler") {
    const path = Array.from({ length: segments + 1 }, (_, index) => slerp(start, end, index / segments));
    return { paths: [path], label: formatAngle(distance), anchor: slerp(start, end, 0.5) };
  }
  if (kind === "circle") {
    const center = slerp(start, end, 0.5);
    const radius = distance / 2;
    const path = Array.from({ length: segments + 1 }, (_, index) => destination(center, radius, 360 * index / segments));
    return { paths: [path], label: `r ${formatAngle(radius)} · Ø ${formatAngle(distance)}`, anchor: destination(center, radius, 90) };
  }
  const bearingFromStart = toRad(initialBearingDeg(start, end));
  const distanceRad = toRad(distance);
  let dx = distanceRad * Math.sin(bearingFromStart);
  let dy = distanceRad * Math.cos(bearingFromStart);
  
  if (kind === "square") {
    const s = Math.max(Math.abs(dx), Math.abs(dy));
    dx = (Math.sign(dx) || 1) * s;
    dy = (Math.sign(dy) || 1) * s;
  }
  
  if (Math.abs(dx) <= 1e-9 || Math.abs(dy) <= 1e-9) return null;
  const rotation = toRad(rotationDeg);
  const localCorners: [number, number][] = [
    [0, 0],
    [dx, 0],
    [dx, dy],
    [0, dy],
  ].map(([x, y]) => rotateXY(x, y, rotation));
  const edgeSegments = Math.max(2, Math.floor(segments / 4));
  const path: AngularCoordinate[] = [];
  for (let edge = 0; edge < 4; edge++) {
    const a = localCorners[edge]!;
    const b = localCorners[(edge + 1) % 4]!;
    for (let index = 0; index < edgeSegments; index++) {
      const t = index / edgeSegments;
      path.push(gnomonicOffset(start, a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t));
    }
  }
  path.push(path[0]!);
  const widthDeg = toDeg(Math.abs(dx));
  const heightDeg = toDeg(Math.abs(dy));
  return {
    paths: [path],
    label: `${formatAngle(widthDeg)} × ${formatAngle(heightDeg)}`,
    anchor: gnomonicOffset(start, ...rotateXY(dx / 2, dy + (dy >= 0 ? 0.01 : -0.01), rotation)),
  };
}

function unit(value: AngularCoordinate): Vector3 { const alt = toRad(value.altitudeDeg), az = toRad(value.azimuthDeg), horizontal = Math.cos(alt); return [Math.sin(az) * horizontal, Math.cos(az) * horizontal, Math.sin(alt)]; }
function coordinate(value: Vector3): AngularCoordinate { const length = norm(value); return { altitudeDeg: toDeg(Math.asin(clamp(value[2] / length, -1, 1))), azimuthDeg: (toDeg(Math.atan2(value[0], value[1])) + 360) % 360 }; }
function slerp(a: AngularCoordinate, b: AngularCoordinate, t: number): AngularCoordinate {
  const first = unit(a), second = unit(b), cosine = clamp(dot(first, second), -1, 1), angle = Math.acos(cosine);
  if (angle < 1e-12) return a;
  let vector: Vector3;
  if (Math.PI - angle < 1e-8) { let axis = normalize(cross(first, [0, 0, 1])); if (norm(axis) < 1e-8) axis = [1, 0, 0]; vector = rodrigues(first, axis, Math.PI * t); }
  else { const sine = Math.sin(angle); vector = [0, 1, 2].map(i => (Math.sin((1 - t) * angle) * first[i]! + Math.sin(t * angle) * second[i]!) / sine) as unknown as Vector3; }
  return coordinate(vector);
}
function initialBearingDeg(a: AngularCoordinate, b: AngularCoordinate): number { const lat1 = toRad(a.altitudeDeg), lat2 = toRad(b.altitudeDeg), delta = toRad(((b.azimuthDeg - a.azimuthDeg + 180) % 360) - 180); return (toDeg(Math.atan2(Math.sin(delta) * Math.cos(lat2), Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(delta))) + 360) % 360; }
function destination(center: AngularCoordinate, distanceDeg: number, bearingDeg: number): AngularCoordinate { const lat = toRad(center.altitudeDeg), lon = toRad(center.azimuthDeg), distance = toRad(distanceDeg), bearing = toRad(bearingDeg); const lat2 = Math.asin(Math.sin(lat) * Math.cos(distance) + Math.cos(lat) * Math.sin(distance) * Math.cos(bearing)); const lon2 = lon + Math.atan2(Math.sin(bearing) * Math.sin(distance) * Math.cos(lat), Math.cos(distance) - Math.sin(lat) * Math.sin(lat2)); return { altitudeDeg: toDeg(lat2), azimuthDeg: (toDeg(lon2) + 360) % 360 }; }
function gnomonicOffset(center: AngularCoordinate, x: number, y: number): AngularCoordinate { const c = unit(center), az = toRad(center.azimuthDeg), alt = toRad(center.altitudeDeg); const east: Vector3 = [Math.cos(az), -Math.sin(az), 0], north: Vector3 = [-Math.sin(az) * Math.sin(alt), -Math.cos(az) * Math.sin(alt), Math.cos(alt)]; return coordinate(normalize([c[0] + Math.tan(x) * east[0] + Math.tan(y) * north[0], c[1] + Math.tan(x) * east[1] + Math.tan(y) * north[1], c[2] + Math.tan(x) * east[2] + Math.tan(y) * north[2]])); }
function formatAngle(valueDeg: number): string { const value = Math.abs(valueDeg); return value < 1 / 60 ? `${(value * 3600).toFixed(2)}″` : value < 1 ? `${(value * 60).toFixed(2)}′` : `${value.toFixed(3)}°`; }
function rotateXY(x: number, y: number, angle: number): [number, number] { return [x * Math.cos(angle) - y * Math.sin(angle), x * Math.sin(angle) + y * Math.cos(angle)]; }
function rodrigues(v: Vector3, axis: Vector3, angle: number): Vector3 { const c = Math.cos(angle), s = Math.sin(angle), crossed = cross(axis, v), d = dot(axis, v); return [v[0] * c + crossed[0] * s + axis[0] * d * (1 - c), v[1] * c + crossed[1] * s + axis[1] * d * (1 - c), v[2] * c + crossed[2] * s + axis[2] * d * (1 - c)]; }
function dot(a: Vector3, b: Vector3): number { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
function cross(a: Vector3, b: Vector3): Vector3 { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
function norm(value: Vector3): number { return Math.hypot(...value); }
function normalize(value: Vector3): Vector3 { const length = norm(value); return length <= 1e-15 ? value : scale(value, 1 / length); }
function scale(value: Vector3, scalar: number): Vector3 { return [value[0] * scalar, value[1] * scalar, value[2] * scalar]; }
function clamp(value: number, minimum: number, maximum: number): number { return Math.max(minimum, Math.min(maximum, value)); }
function toRad(value: number): number { return value * Math.PI / 180; }
function toDeg(value: number): number { return value * 180 / Math.PI; }
