export type SampleValidityName = "outside_coverage" | "valid" | "nodata" | "masked";
export type ClassificationStatusName = "classified" | "unknown" | "unclassified";

export interface LandCoverLegendEntryData {
  readonly sourceCode: number;
  /** Original value in the source classification (code or exact RGBA token). */
  readonly sourceValue: number | string;
  readonly sourceLabel: string;
  readonly sourceLabelKey: string | null;
  readonly colorRgba: [number, number, number, number];
  readonly sampleValidity: SampleValidityName | null;
  readonly classificationStatus: ClassificationStatusName | null;
  readonly categoryKey: string | null;
  readonly categoryLabelKey: string | null;
  readonly categoryLabel: string | null;
  readonly qualifiers: Readonly<Record<string, string>>;
  readonly mappingKind: "single" | "composite" | "observation_state";
  readonly resolvedPath: readonly string[];
  readonly semanticDepth: number | null;
  readonly unresolvedChildren: readonly string[];
}

export interface LandCoverLegendData {
  readonly type: "land_cover_legend";
  readonly schemeKey: string;
  readonly schemeVersion: string;
  readonly mappingRevision: string;
  readonly sourceName: string;
  readonly taxonomyKey: "TLST";
  readonly taxonomyVersion: string;
  readonly entries: readonly LandCoverLegendEntryData[];
}

export interface LandCoverTileMetadata {
  readonly role: "land_cover_tile";
  readonly resourceId: string;
  readonly tileKey?: string;
  readonly version: number;
  readonly bounds: [number, number, number, number];
  readonly width: number;
  readonly height: number;
  readonly resolution: number;
  readonly sourceId: string;
  readonly sourceName: string;
  readonly schemeKey: string;
  readonly schemeVersion: string;
  readonly mappingRevision: string;
  readonly taxonomyKey: "TLST";
  readonly taxonomyVersion: string;
  readonly sourceDtype: string;
  readonly dtype: "uint16";
  readonly sourceCodeOffset: number;
  readonly sourceCodeByteLength: number;
  readonly sampleValidityOffset: number;
  readonly sampleValidityByteLength: number;
  readonly validityEncoding: "tlst-sample-validity-2bit-v1";
  readonly validityRowBytes: number;
  readonly validPixels: number;
}

export interface LandCoverTileData extends LandCoverTileMetadata {
  readonly sourceCodes: Uint16Array;
  readonly sampleValidity: Uint8Array;
}

export interface LandCoverObservation {
  readonly sourceName: string;
  readonly schemeKey: string;
  readonly schemeVersion: string;
  readonly mappingRevision: string;
  readonly sourceCode: number;
  readonly sourceValue: number | string;
  readonly sourceLabel: string | null;
  readonly taxonomyKey: "TLST";
  readonly taxonomyVersion: string;
  readonly categoryKey: string | null;
  readonly categoryLabelKey: string | null;
  readonly categoryLabel: string | null;
  readonly qualifiers: Readonly<Record<string, string>>;
  readonly classificationStatus: ClassificationStatusName | null;
  readonly validity: SampleValidityName;
}

export function decodeLandCoverTile(
  metadata: LandCoverTileMetadata,
  payload: ArrayBuffer,
): LandCoverTileData {
  if (metadata.role !== "land_cover_tile") throw new Error("Not a land-cover tile");
  if (metadata.dtype !== "uint16") throw new Error(`Unsupported land-cover dtype: ${metadata.dtype}`);
  if (metadata.validityEncoding !== "tlst-sample-validity-2bit-v1") {
    throw new Error(`Unsupported SampleValidity encoding: ${metadata.validityEncoding}`);
  }
  if (!positiveInteger(metadata.width) || !positiveInteger(metadata.height)) {
    throw new Error("Land-cover dimensions must be positive integers");
  }

  const pixelCount = metadata.width * metadata.height;
  const expectedCodeBytes = pixelCount * Uint16Array.BYTES_PER_ELEMENT;
  const expectedRowBytes = Math.ceil(metadata.width / 4);
  const expectedValidityBytes = expectedRowBytes * metadata.height;
  if (
    metadata.sourceCodeOffset !== 0
    || metadata.sourceCodeByteLength !== expectedCodeBytes
    || metadata.sampleValidityOffset !== expectedCodeBytes
    || metadata.sampleValidityByteLength !== expectedValidityBytes
    || metadata.validityRowBytes !== expectedRowBytes
    || payload.byteLength !== expectedCodeBytes + expectedValidityBytes
  ) {
    throw new Error("Land-cover binary descriptor does not match its payload");
  }

  return {
    ...metadata,
    sourceCodes: new Uint16Array(
      payload,
      metadata.sourceCodeOffset,
      metadata.sourceCodeByteLength / Uint16Array.BYTES_PER_ELEMENT,
    ),
    sampleValidity: new Uint8Array(
      payload,
      metadata.sampleValidityOffset,
      metadata.sampleValidityByteLength,
    ),
  };
}

export function sampleValidityName(encoded: number): SampleValidityName {
  switch (encoded) {
    case 0: return "outside_coverage";
    case 1: return "valid";
    case 2: return "nodata";
    case 3: return "masked";
    default: throw new Error(`Invalid SampleValidity encoding: ${encoded}`);
  }
}

function positiveInteger(value: number): boolean {
  return Number.isSafeInteger(value) && value > 0;
}
