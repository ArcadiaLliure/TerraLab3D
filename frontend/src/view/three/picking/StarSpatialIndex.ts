/**
 * StarSpatialIndex — índex espacial per a picking estel·lar eficient.
 *
 * Implementació: Cube-sphere hash (6 cares × bins per cara).
 * Per catàlegs petits (< 5000 estrelles), linear scan directe.
 *
 * Construït UNA VEGADA per resource version. NO per frame, click, hover, temps o càmera.
 *
 * Lifecycle:
 *   resource register → index build
 *   resource dispose → index dispose
 */

const LOG_PREFIX = "MGP: [StarSpatialIndex]";

/** Nombre de bins per eix per cara del cub (total = 6 * N * N). */
const BINS_PER_AXIS = 32;
const TOTAL_BINS = 6 * BINS_PER_AXIS * BINS_PER_AXIS;

/** Llindar per a linear scan directe (sense index). */
const LINEAR_SCAN_THRESHOLD = 5000;

export interface SpatialIndexMetrics {
  buildMs: number;
  bytes: number;
  starCount: number;
  binCount: number;
  usesLinearScan: boolean;
}

export class StarSpatialIndex {
  private bins: Int32Array[] | null = null;
  private positions: Float32Array | null = null;
  private starCount = 0;
  private usesLinearScan = false;
  private _metrics: SpatialIndexMetrics | null = null;

  get metrics(): SpatialIndexMetrics | null {
    return this._metrics;
  }

  /**
   * Construeix l'índex a partir de posicions equatorials unitàries [N×3].
   */
  build(equatorialPositions: Float32Array): void {
    if (equatorialPositions.length % 3 !== 0) {
      throw new Error("equatorialPositions length must be a multiple of 3");
    }
    const t0 = performance.now();
    this.positions = equatorialPositions;
    this.starCount = equatorialPositions.length / 3;

    if (this.starCount <= LINEAR_SCAN_THRESHOLD) {
      // Linear scan per catàlegs petits
      this.usesLinearScan = true;
      this.bins = null;
      const buildMs = performance.now() - t0;
      this._metrics = {
        buildMs,
        bytes: 0,
        starCount: this.starCount,
        binCount: 0,
        usesLinearScan: true,
      };
      console.log(
        `${LOG_PREFIX} [build] [Linear scan: ${this.starCount} estrelles, ${buildMs.toFixed(1)} ms]`,
      );
      return;
    }

    // Cube-sphere hash: projectar cada estrella a una cara del cub
    this.usesLinearScan = false;
    const binLists: number[][] = new Array(TOTAL_BINS);
    for (let i = 0; i < TOTAL_BINS; i++) {
      binLists[i] = [];
    }

    for (let i = 0; i < this.starCount; i++) {
      const x = equatorialPositions[i * 3]!;
      const y = equatorialPositions[i * 3 + 1]!;
      const z = equatorialPositions[i * 3 + 2]!;

      const binIdx = this.vectorToBin(x, y, z);
      binLists[binIdx]!.push(i);
    }

    // Convertir a TypedArrays compactes
    this.bins = new Array(TOTAL_BINS);
    let totalBytes = 0;
    for (let i = 0; i < TOTAL_BINS; i++) {
      const bin = new Int32Array(binLists[i]!);
      this.bins[i] = bin;
      totalBytes += bin.byteLength;
    }

    const buildMs = performance.now() - t0;
    this._metrics = {
      buildMs,
      bytes: totalBytes,
      starCount: this.starCount,
      binCount: TOTAL_BINS,
      usesLinearScan: false,
    };

    console.log(
      `${LOG_PREFIX} [build] [Cube-sphere: ${this.starCount} estrelles, ${TOTAL_BINS} bins, ${totalBytes} bytes, ${buildMs.toFixed(1)} ms]`,
    );
  }

  /**
   * Consulta totes les estrelles dins d'un con esportiu.
   *
   * @param dirX, dirY, dirZ — direcció equatorial unitària del centre del con
   * @param angularRadiusRad — radi angular del con en radians
   * @returns array d'índexs dins del con
   */
  queryCone(
    dirX: number,
    dirY: number,
    dirZ: number,
    angularRadiusRad: number,
  ): number[] {
    if (!this.positions || this.starCount === 0) return [];

    const cosThreshold = Math.cos(angularRadiusRad);
    const positions = this.positions;
    const result: number[] = [];

    if (this.usesLinearScan) {
      // Linear scan directe
      for (let i = 0; i < this.starCount; i++) {
        const px = positions[i * 3]!;
        const py = positions[i * 3 + 1]!;
        const pz = positions[i * 3 + 2]!;
        const dot = px * dirX + py * dirY + pz * dirZ;
        if (dot >= cosThreshold) {
          result.push(i);
        }
      }
      return result;
    }

    if (!this.bins) return [];

    // Determinar quins bins es superposen amb el con
    // Estratègia: calcular el bin central i expandir per la mida angular
    const binsToCheck = this.getBinsInCone(dirX, dirY, dirZ, angularRadiusRad);

    for (const binIdx of binsToCheck) {
      const bin = this.bins[binIdx];
      if (bin === undefined) continue;
      for (let j = 0; j < bin.length; j++) {
        const i = bin[j]!;
        const px = positions[i * 3]!;
        const py = positions[i * 3 + 1]!;
        const pz = positions[i * 3 + 2]!;
        const dot = px * dirX + py * dirY + pz * dirZ;
        if (dot >= cosThreshold) {
          result.push(i);
        }
      }
    }

    return result;
  }

  dispose(): void {
    this.bins = null;
    this.positions = null;
    this.starCount = 0;
    this._metrics = null;
    console.log(`${LOG_PREFIX} [dispose] [Índex alliberat]`);
  }

  // ─── Private ──────────────────────────────────────────────────────

  /**
   * Mapeja un vector unitari al bin corresponent del cub.
   */
  private vectorToBin(x: number, y: number, z: number): number {
    const ax = Math.abs(x);
    const ay = Math.abs(y);
    const az = Math.abs(z);

    let face: number;
    let u: number;
    let v: number;

    if (ax >= ay && ax >= az) {
      face = x > 0 ? 0 : 1;
      u = y / ax;
      v = z / ax;
    } else if (ay >= ax && ay >= az) {
      face = y > 0 ? 2 : 3;
      u = x / ay;
      v = z / ay;
    } else {
      face = z > 0 ? 4 : 5;
      u = x / az;
      v = y / az;
    }

    // u, v ∈ [-1, 1] → bin coords [0, BINS_PER_AXIS)
    const bu = Math.min(
      BINS_PER_AXIS - 1,
      Math.max(0, Math.floor((u + 1) * 0.5 * BINS_PER_AXIS)),
    );
    const bv = Math.min(
      BINS_PER_AXIS - 1,
      Math.max(0, Math.floor((v + 1) * 0.5 * BINS_PER_AXIS)),
    );

    return face * BINS_PER_AXIS * BINS_PER_AXIS + bv * BINS_PER_AXIS + bu;
  }

  /**
   * Retorna els índexs de bins que es superposen amb un con.
   */
  private getBinsInCone(
    dirX: number,
    dirY: number,
    dirZ: number,
    angularRadiusRad: number,
  ): number[] {
    // Marge de seguretat: expandir el radi angular per cobrir bins parcialment superposats
    const expandedRadius = angularRadiusRad + (Math.PI / BINS_PER_AXIS);

    // Per eficiència, calcular quines cares del cub són rellevants
    const cosExpanded = Math.cos(Math.min(expandedRadius, Math.PI));
    const result: number[] = [];

    // Per cada cara del cub, verificar si és possible que contingui candidats
    for (let face = 0; face < 6; face++) {
      // Normal de la cara
      let nx = 0, ny = 0, nz = 0;
      switch (face) {
        case 0: nx = 1; break;
        case 1: nx = -1; break;
        case 2: ny = 1; break;
        case 3: ny = -1; break;
        case 4: nz = 1; break;
        case 5: nz = -1; break;
      }

      // Angle entre la direcció i la normal de la cara
      const dotFace = nx * dirX + ny * dirY + nz * dirZ;

      // Si l'angle entre la direcció i la cara és massa gran, saltar
      // La cara cobreix fins a ~±45° de la seva normal
      if (dotFace < -0.5) continue;

      // Escanem tots els bins de la cara si la cara és rellevant
      // Optimització: per cones petits, podríem restringir bins
      if (expandedRadius > 0.3) {
        // Con gran: incloure tots els bins de la cara
        const baseIdx = face * BINS_PER_AXIS * BINS_PER_AXIS;
        for (let i = 0; i < BINS_PER_AXIS * BINS_PER_AXIS; i++) {
          result.push(baseIdx + i);
        }
      } else {
        // Con petit: restringir als bins propers
        this.addNearbyBinsForFace(face, dirX, dirY, dirZ, expandedRadius, result);
      }
    }

    return result;
  }

  /**
   * Per a un con petit, afegeix només els bins propers dins d'una cara.
   */
  private addNearbyBinsForFace(
    face: number,
    dirX: number,
    dirY: number,
    dirZ: number,
    radius: number,
    result: number[],
  ): void {
    // Projectar la direcció a la cara
    let ax: number, u: number, v: number;
    switch (face) {
      case 0: ax = dirX; u = dirY / Math.max(0.001, Math.abs(dirX)); v = dirZ / Math.max(0.001, Math.abs(dirX)); break;
      case 1: ax = -dirX; u = dirY / Math.max(0.001, Math.abs(dirX)); v = dirZ / Math.max(0.001, Math.abs(dirX)); break;
      case 2: ax = dirY; u = dirX / Math.max(0.001, Math.abs(dirY)); v = dirZ / Math.max(0.001, Math.abs(dirY)); break;
      case 3: ax = -dirY; u = dirX / Math.max(0.001, Math.abs(dirY)); v = dirZ / Math.max(0.001, Math.abs(dirY)); break;
      case 4: ax = dirZ; u = dirX / Math.max(0.001, Math.abs(dirZ)); v = dirY / Math.max(0.001, Math.abs(dirZ)); break;
      case 5: default: ax = -dirZ; u = dirX / Math.max(0.001, Math.abs(dirZ)); v = dirY / Math.max(0.001, Math.abs(dirZ)); break;
    }

    if (ax <= 0) return;

    // Centre del con en coordenades de la cara [0, BINS_PER_AXIS)
    const cu = (u + 1) * 0.5 * BINS_PER_AXIS;
    const cv = (v + 1) * 0.5 * BINS_PER_AXIS;

    // Radi en bins (aproximació)
    const binRadius = Math.ceil(radius * BINS_PER_AXIS / Math.PI) + 1;

    const bu0 = Math.max(0, Math.floor(cu) - binRadius);
    const bu1 = Math.min(BINS_PER_AXIS - 1, Math.floor(cu) + binRadius);
    const bv0 = Math.max(0, Math.floor(cv) - binRadius);
    const bv1 = Math.min(BINS_PER_AXIS - 1, Math.floor(cv) + binRadius);

    const baseIdx = face * BINS_PER_AXIS * BINS_PER_AXIS;
    for (let bv = bv0; bv <= bv1; bv++) {
      for (let bu = bu0; bu <= bu1; bu++) {
        result.push(baseIdx + bv * BINS_PER_AXIS + bu);
      }
    }
  }
}
