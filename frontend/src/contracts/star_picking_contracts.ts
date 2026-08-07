/**
 * Contractes tipats per al sistema de picking estel·lar (Pas 6).
 *
 * Identitat mínima obligatòria: resourceId + resourceVersion + catalogIndex.
 * source_id Gaia és int64 → sempre string al frontend.
 * catalogIndex és uint32 semàntic — mai float per identitat canònica.
 */

// ─── Picking purpose ─────────────────────────────────────────────────

export type StarPickPurpose = "select" | "hover";

// ─── Referència local d'estrella (frontend) ──────────────────────────

export interface StarPickRef {
  readonly resourceId: string;
  readonly resourceVersion: string;
  readonly catalogIndex: number; // uint32 semàntic — mai obtingut de Float32Array
}

// ─── Hit test result (frontend, local) ───────────────────────────────

export interface StarPickHit {
  readonly kind: "star";
  readonly ref: StarPickRef;
  readonly screenXCssPx: number;
  readonly screenYCssPx: number;
  readonly screenDistanceCssPx: number;
  readonly visualRadiusCssPx: number;
  readonly hitRadiusCssPx: number;
  readonly magnitude: number;
}

// ─── Estrella resolta (backend → frontend) ───────────────────────────

export interface ResolvedStar {
  readonly kind: "star";
  readonly resourceId: string;
  readonly resourceVersion: string;
  readonly catalogIndex: number;
  readonly sourceId: string; // int64 com string decimal — NEVER number
  readonly raDeg: number;
  readonly decDeg: number;
  readonly magnitude: number;
  readonly bpRp: number | null;
  readonly sourceRole: "general" | "fallback" | "supplement" | "deep_tile";
}

// ─── Metadata tipada del recurs binari ───────────────────────────────

export interface StarBufferLayoutEntry {
  readonly offset: number;
  readonly length: number;
  readonly dtype: string;
  readonly components: number;
}

export interface StarResourceMetadata {
  readonly type: "star_resource";
  readonly resourceId: string;
  readonly version: string;
  readonly role: string;
  readonly starCount: number;
  readonly byteLength: number;
  readonly contentHash: string;
  readonly bufferLayout: {
    readonly positions: StarBufferLayoutEntry;
    readonly magnitudes: StarBufferLayoutEntry;
    readonly colors: StarBufferLayoutEntry;
    readonly catalogIndices: StarBufferLayoutEntry;
  };
}

// ─── Bridge messages (picking) ───────────────────────────────────────

export interface ResolveStarPickMessage {
  readonly type: "resolve_star_pick";
  readonly requestId: string;
  readonly generation: number;
  readonly resourceId: string;
  readonly resourceVersion: string;
  readonly catalogIndex: number;
  readonly purpose: StarPickPurpose;
}

export type StarPickResolveStatus = "ok" | "stale" | "missing" | "invalid";

export interface StarPickResolvedMessage {
  readonly type: "star_pick_resolved";
  readonly requestId: string;
  readonly generation: number;
  readonly status: StarPickResolveStatus;
  readonly star?: ResolvedStar;
}
