/**
 * Converts the persistent terrain ENU world into WGS84 coordinates.
 *
 * The backend builds the terrain with a WGS84 azimuthal-equidistant projector
 * centred on the observer selected by the user. Vincenty's direct solution
 * is the matching ellipsoidal geodesic operation for a point in that world.
 */

const WGS84_SEMI_MAJOR_AXIS_M = 6_378_137.0;
const WGS84_FLATTENING = 1 / 298.257_223_563;
const WGS84_SEMI_MINOR_AXIS_M = WGS84_SEMI_MAJOR_AXIS_M * (1 - WGS84_FLATTENING);
const MAX_ITERATIONS = 100;
const CONVERGENCE = 1e-12;

export interface TerrainWorldAnchor {
  readonly latitudeDeg: number;
  readonly longitudeDeg: number;
}

export interface TerrainCoordinate {
  readonly latitudeDeg: number;
  readonly longitudeDeg: number;
}

export interface TerrainWorldPoint {
  readonly eastM: number;
  readonly northM: number;
}

/**
 * Projects an ENU point (east/north metres) from the current terrain anchor.
 * Returns null for invalid input rather than fabricating a geographic point.
 */
export function projectTerrainCoordinate(
  anchor: TerrainWorldAnchor,
  eastM: number,
  northM: number,
): TerrainCoordinate | null {
  if (!isValidAnchor(anchor) || !Number.isFinite(eastM) || !Number.isFinite(northM)) return null;
  const distanceM = Math.hypot(eastM, northM);
  if (distanceM < 1e-9) {
    return { latitudeDeg: anchor.latitudeDeg, longitudeDeg: normalizeLongitude(anchor.longitudeDeg) };
  }

  const azimuthRad = Math.atan2(eastM, northM);
  const latitude1 = degreesToRadians(anchor.latitudeDeg);
  const longitude1 = degreesToRadians(anchor.longitudeDeg);
  const reducedLatitude1 = Math.atan((1 - WGS84_FLATTENING) * Math.tan(latitude1));
  const sinReducedLatitude1 = Math.sin(reducedLatitude1);
  const cosReducedLatitude1 = Math.cos(reducedLatitude1);
  const sinAzimuth = Math.sin(azimuthRad);
  const cosAzimuth = Math.cos(azimuthRad);
  const sigma1 = Math.atan2(Math.tan(reducedLatitude1), cosAzimuth);
  const sinAlpha = cosReducedLatitude1 * sinAzimuth;
  const cosSquaredAlpha = 1 - sinAlpha * sinAlpha;
  const uSquared = cosSquaredAlpha
    * (WGS84_SEMI_MAJOR_AXIS_M * WGS84_SEMI_MAJOR_AXIS_M - WGS84_SEMI_MINOR_AXIS_M * WGS84_SEMI_MINOR_AXIS_M)
    / (WGS84_SEMI_MINOR_AXIS_M * WGS84_SEMI_MINOR_AXIS_M);
  const coefficientA = 1 + uSquared / 16_384 * (4_096 + uSquared * (-768 + uSquared * (320 - 175 * uSquared)));
  const coefficientB = uSquared / 1_024 * (256 + uSquared * (-128 + uSquared * (74 - 47 * uSquared)));

  let sigma = distanceM / (WGS84_SEMI_MINOR_AXIS_M * coefficientA);
  let previousSigma = Number.NaN;
  let cosineDoubleSigmaMidpoint = 0;
  let sineSigma = 0;
  let cosineSigma = 0;
  let deltaSigma = 0;
  for (let iteration = 0; iteration < MAX_ITERATIONS; iteration++) {
    cosineDoubleSigmaMidpoint = Math.cos(2 * sigma1 + sigma);
    sineSigma = Math.sin(sigma);
    cosineSigma = Math.cos(sigma);
    deltaSigma = coefficientB * sineSigma * (
      cosineDoubleSigmaMidpoint + coefficientB / 4 * (
        cosineSigma * (-1 + 2 * cosineDoubleSigmaMidpoint * cosineDoubleSigmaMidpoint)
        - coefficientB / 6 * cosineDoubleSigmaMidpoint * (-3 + 4 * sineSigma * sineSigma)
          * (-3 + 4 * cosineDoubleSigmaMidpoint * cosineDoubleSigmaMidpoint)
      )
    );
    previousSigma = sigma;
    sigma = distanceM / (WGS84_SEMI_MINOR_AXIS_M * coefficientA) + deltaSigma;
    if (Math.abs(sigma - previousSigma) <= CONVERGENCE) break;
    if (iteration === MAX_ITERATIONS - 1) return null;
  }

  const temporary = sinReducedLatitude1 * sineSigma - cosReducedLatitude1 * cosineSigma * cosAzimuth;
  const latitude2 = Math.atan2(
    sinReducedLatitude1 * cosineSigma + cosReducedLatitude1 * sineSigma * cosAzimuth,
    (1 - WGS84_FLATTENING) * Math.hypot(sinAlpha, temporary),
  );
  const lambda = Math.atan2(
    sineSigma * sinAzimuth,
    cosReducedLatitude1 * cosineSigma - sinReducedLatitude1 * sineSigma * cosAzimuth,
  );
  const correction = WGS84_FLATTENING / 16 * cosSquaredAlpha
    * (4 + WGS84_FLATTENING * (4 - 3 * cosSquaredAlpha));
  const longitude = lambda - (1 - correction) * WGS84_FLATTENING * sinAlpha * (
    sigma + correction * sineSigma * (
      cosineDoubleSigmaMidpoint + correction * cosineSigma * (-1 + 2 * cosineDoubleSigmaMidpoint * cosineDoubleSigmaMidpoint)
    )
  );

  return {
    latitudeDeg: radiansToDegrees(latitude2),
    longitudeDeg: normalizeLongitude(radiansToDegrees(longitude1 + longitude)),
  };
}

/**
 * Projects a WGS84 coordinate back into the persistent terrain ENU world.
 *
 * This is Vincenty's inverse solution, paired with projectTerrainCoordinate.
 * It is used for an explicit UI relocation only when the destination is
 * already inside the resident DEM world; it never changes the world anchor.
 */
export function projectCoordinateToTerrainWorld(
  anchor: TerrainWorldAnchor,
  coordinate: TerrainCoordinate,
): TerrainWorldPoint | null {
  if (!isValidAnchor(anchor) || !isValidAnchor(coordinate)) return null;

  const latitude1 = degreesToRadians(anchor.latitudeDeg);
  const latitude2 = degreesToRadians(coordinate.latitudeDeg);
  const longitudeDifference = degreesToRadians(
    normalizeLongitude(coordinate.longitudeDeg - anchor.longitudeDeg),
  );
  if (Math.abs(latitude1 - latitude2) < 1e-15 && Math.abs(longitudeDifference) < 1e-15) {
    return { eastM: 0, northM: 0 };
  }

  const reducedLatitude1 = Math.atan((1 - WGS84_FLATTENING) * Math.tan(latitude1));
  const reducedLatitude2 = Math.atan((1 - WGS84_FLATTENING) * Math.tan(latitude2));
  const sinReducedLatitude1 = Math.sin(reducedLatitude1);
  const cosReducedLatitude1 = Math.cos(reducedLatitude1);
  const sinReducedLatitude2 = Math.sin(reducedLatitude2);
  const cosReducedLatitude2 = Math.cos(reducedLatitude2);

  let lambda = longitudeDifference;
  let sineSigma = 0;
  let cosineSigma = 0;
  let sigma = 0;
  let sineAlpha = 0;
  let cosineSquaredAlpha = 0;
  let cosineDoubleSigmaMidpoint = 0;
  for (let iteration = 0; iteration < MAX_ITERATIONS; iteration++) {
    const sineLambda = Math.sin(lambda);
    const cosineLambda = Math.cos(lambda);
    sineSigma = Math.hypot(
      cosReducedLatitude2 * sineLambda,
      cosReducedLatitude1 * sinReducedLatitude2
        - sinReducedLatitude1 * cosReducedLatitude2 * cosineLambda,
    );
    if (sineSigma < 1e-15) return { eastM: 0, northM: 0 };
    cosineSigma = sinReducedLatitude1 * sinReducedLatitude2
      + cosReducedLatitude1 * cosReducedLatitude2 * cosineLambda;
    sigma = Math.atan2(sineSigma, cosineSigma);
    sineAlpha = cosReducedLatitude1 * cosReducedLatitude2 * sineLambda / sineSigma;
    cosineSquaredAlpha = 1 - sineAlpha * sineAlpha;
    cosineDoubleSigmaMidpoint = cosineSquaredAlpha <= 1e-15
      ? 0
      : cosineSigma - 2 * sinReducedLatitude1 * sinReducedLatitude2 / cosineSquaredAlpha;
    const correction = WGS84_FLATTENING / 16 * cosineSquaredAlpha
      * (4 + WGS84_FLATTENING * (4 - 3 * cosineSquaredAlpha));
    const nextLambda = longitudeDifference + (1 - correction) * WGS84_FLATTENING * sineAlpha * (
      sigma + correction * sineSigma * (
        cosineDoubleSigmaMidpoint + correction * cosineSigma * (
          -1 + 2 * cosineDoubleSigmaMidpoint * cosineDoubleSigmaMidpoint
        )
      )
    );
    if (Math.abs(nextLambda - lambda) <= CONVERGENCE) {
      lambda = nextLambda;
      break;
    }
    lambda = nextLambda;
    if (iteration === MAX_ITERATIONS - 1) return null;
  }

  const uSquared = cosineSquaredAlpha
    * (WGS84_SEMI_MAJOR_AXIS_M * WGS84_SEMI_MAJOR_AXIS_M - WGS84_SEMI_MINOR_AXIS_M * WGS84_SEMI_MINOR_AXIS_M)
    / (WGS84_SEMI_MINOR_AXIS_M * WGS84_SEMI_MINOR_AXIS_M);
  const coefficientA = 1 + uSquared / 16_384 * (4_096 + uSquared * (-768 + uSquared * (320 - 175 * uSquared)));
  const coefficientB = uSquared / 1_024 * (256 + uSquared * (-128 + uSquared * (74 - 47 * uSquared)));
  const deltaSigma = coefficientB * sineSigma * (
    cosineDoubleSigmaMidpoint + coefficientB / 4 * (
      cosineSigma * (-1 + 2 * cosineDoubleSigmaMidpoint * cosineDoubleSigmaMidpoint)
      - coefficientB / 6 * cosineDoubleSigmaMidpoint * (-3 + 4 * sineSigma * sineSigma)
        * (-3 + 4 * cosineDoubleSigmaMidpoint * cosineDoubleSigmaMidpoint)
    )
  );
  const distanceM = WGS84_SEMI_MINOR_AXIS_M * coefficientA * (sigma - deltaSigma);
  const forwardAzimuthRad = Math.atan2(
    cosReducedLatitude2 * Math.sin(lambda),
    cosReducedLatitude1 * sinReducedLatitude2
      - sinReducedLatitude1 * cosReducedLatitude2 * Math.cos(lambda),
  );
  return {
    eastM: distanceM * Math.sin(forwardAzimuthRad),
    northM: distanceM * Math.cos(forwardAzimuthRad),
  };
}

function isValidAnchor(anchor: TerrainWorldAnchor): boolean {
  return Number.isFinite(anchor.latitudeDeg)
    && Number.isFinite(anchor.longitudeDeg)
    && Math.abs(anchor.latitudeDeg) <= 90
    && Math.abs(anchor.longitudeDeg) <= 180;
}

function degreesToRadians(value: number): number {
  return value * Math.PI / 180;
}

function radiansToDegrees(value: number): number {
  return value * 180 / Math.PI;
}

function normalizeLongitude(value: number): number {
  return ((value + 540) % 360) - 180;
}
