import { buildRefinementTree, RefinementSession } from "../application/RefinementSession";
import {
  buildBasemapLandFeatures,
  extractRefinementGeometry,
  splitAntimeridianGeometry,
} from "../view/ui/modals/RefinementMapView";
import { refinementRenderImpact } from "../view/ui/modals/RefinementManagerView";
import type {
  RefinementCandidatesMessage,
  RefinementDownloadProgressMessage,
  RefinementGeometry,
  RefinementPlanSummaryMessage,
  RefinementProductCandidate,
  RefinementWorkspace,
} from "../contracts/refinement_contracts";

function assert(condition: boolean, message: string): void {
  if (!condition) throw new Error(message);
}

const aoi: RefinementGeometry = {
  type: "Polygon",
  coordinates: [[[1, 41], [2, 41], [2, 42], [1, 42], [1, 41]]],
};

const workspace: RefinementWorkspace = {
  taxonomyKey: "TLST",
  taxonomyVersion: "1.0",
  virtualRoot: "surface",
  aoi,
  nodes: [
    { categoryKey: "agriculture", parentKey: "surface", label: "Agricultura", depth: 1, state: "partial", verifiedPercent: 40, plannedPercent: 40, installations: [], applicable: true },
    { categoryKey: "agriculture.arable", parentKey: "agriculture", label: "Conreus herbacis", depth: 2, state: "complete", verifiedPercent: 100, plannedPercent: 100, installations: [{ installationId: "installed-1", provider: "Test", product: "Test", version: "1.0" }], applicable: true },
  ],
};

const candidate: RefinementProductCandidate = {
  candidateId: "crop-2022",
  providerId: "clms",
  provider: "Copernicus Land Monitoring Service",
  product: "Crop Types 2022",
  version: "2022",
  datasetIdentifier: "crop-types-2022",
  compatibleTlstNodes: ["agriculture.arable"],
  footprint: aoi,
  resolutionM: 10,
  temporalStart: "2022-01-01",
  temporalEnd: "2022-12-31",
  format: "GeoTIFF",
  estimatedBytes: 1024,
  availablePercent: 100,
  newEffectivePercent: 60,
  qualifierKey: null,
  endpointVerified: true,
  license: {
    licenseId: "Copernicus data policy",
    officialUrl: "https://land.copernicus.eu/en/faq/data-use-terms-and-conditions",
    attribution: "European Union, Copernicus Land Monitoring Service",
    commercialUse: true,
    checkedAt: "2026-08-25",
  },
  assets: [],
  installationId: null,
};

const session = new RefinementSession();
const withAoi = session.setAoi(aoi);
const selected = session.selectCategory("agriculture.arable");
assert(selected.revision === withAoi.revision + 1, "Changing category advances the revision");

const stale: RefinementCandidatesMessage = {
  type: "refinement_candidates",
  requestId: withAoi.requestId,
  revision: withAoi.revision,
  categoryKey: "agriculture.arable",
  candidates: [candidate],
  failures: [],
};
assert(!session.accept(stale), "A late response from an older AOI is discarded");

const current = session.snapshot();
const candidates: RefinementCandidatesMessage = {
  ...stale,
  requestId: current.requestId,
  revision: current.revision,
};
assert(session.accept(candidates), "The current provider response is accepted");
assert(session.snapshot().selectedProductIds.has(candidate.candidateId), "Effective products are initially selected");

session.setProductSelected(candidate.candidateId, false);
assert(session.snapshot().selectedProductIds.size === 0, "Product multi-selection can be cleared");
session.setProductSelected(candidate.candidateId, true);

const plan: RefinementPlanSummaryMessage = {
  type: "refinement_plan_summary",
  requestId: current.requestId,
  revision: current.revision,
  categoryKey: "agriculture.arable",
  productIds: [candidate.candidateId],
  coverage: {
    existingPercent: 40,
    newEffectivePercent: 60,
    plannedPercent: 100,
    remainingPercent: 0,
    existing: aoi,
    planned: aoi,
    remaining: null,
    recommendedProductIds: [candidate.candidateId],
  },
  plan: {
    schemaVersion: 4,
    planId: "plan-1",
    requestId: current.requestId,
    revision: current.revision,
    categoryKeys: ["agriculture.arable"],
    aoi,
    productIds: [candidate.candidateId],
    assets: [],
    processingOptions: {},
    estimatedBytes: 1024,
    requiresLargeDownloadConfirmation: false,
  },
};
assert(session.accept(plan), "A plan for the current selection is accepted");
assert(session.snapshot().planSummary?.coverage.plannedPercent === 100, "Plan coverage is retained");

const beforeConfirm = session.snapshot();
const confirming = session.begin("confirm");
const busyImpact = refinementRenderImpact(beforeConfirm, confirming);
assert(!busyImpact.tree && !busyImpact.products, "Starting a background operation preserves stable panels");

const queuedProgress: RefinementDownloadProgressMessage = {
  type: "refinement_download_progress",
  requestId: confirming.requestId,
  revision: confirming.revision,
  planId: "plan-1",
  jobId: "job-1",
  state: "QUEUED",
  downloadedBytes: 0,
  totalBytes: 1024,
  progress: 0,
  currentFile: null,
  assetProgress: [],
  outputs: { manifest: null, mosaic: null, source: null, quality: null, conflict: null },
  error: null,
};
assert(session.accept(queuedProgress), "Queued download progress is accepted");
const queued = session.snapshot();
const queuedImpact = refinementRenderImpact(confirming, queued);
assert(
  !queuedImpact.tree && !queuedImpact.products && !queuedImpact.mapAoi && !queuedImpact.mapCandidates,
  "Download progress updates only live feedback and does not remount interactive regions",
);
const downloadingProgress: RefinementDownloadProgressMessage = {
  ...queuedProgress,
  state: "DOWNLOADING",
  downloadedBytes: 512,
  progress: 0.5,
  currentFile: "crop-2022.tif",
};
assert(session.accept(downloadingProgress), "Quantitative download progress is accepted");
const downloadImpact = refinementRenderImpact(queued, session.snapshot());
assert(!downloadImpact.tree && !downloadImpact.products, "Progress ticks preserve tree and product scroll state");

const tree = buildRefinementTree(workspace.nodes);
assert(tree.length === 1 && tree[0]?.children.length === 1, "The flat TLST workspace becomes a hierarchy");
assert(tree[0]?.children[0]?.installations[0]?.installationId === "installed-1", "Installation state remains attached to the leaf");

const featureGeometry = extractRefinementGeometry({ type: "Feature", properties: {}, geometry: aoi });
assert(featureGeometry.type === "Polygon", "GeoJSON Feature geometry is accepted");
let rejected = false;
try {
  extractRefinementGeometry({ type: "Point", coordinates: [181, 0] });
} catch {
  rejected = true;
}
assert(rejected, "Unsupported or invalid GeoJSON is rejected");

const datelineLand = splitAntimeridianGeometry({
  type: "Polygon",
  coordinates: [[[170, 60], [-175, 62], [-170, 50], [170, 50], [170, 60]]],
});
assert(datelineLand.type === "MultiPolygon", "Land crossing the antimeridian is split into visible fragments");
if (datelineLand.type === "MultiPolygon") {
  const rings = datelineLand.coordinates.flatMap((polygon) => polygon);
  assert(rings.length === 2, "The dateline cut creates one fragment on either side");
  assert(rings.every((ring) => ring.every((position, index) => (
    index === 0 || Math.abs(position[0]! - ring[index - 1]![0]!) <= 180
  ))), "No projected land edge crosses the world horizontally");
}

const basemapLand = buildBasemapLandFeatures();
const visibleDatelineJumps: number[] = [];
for (const feature of basemapLand.features) {
  if (feature.geometry.type !== "Polygon" && feature.geometry.type !== "MultiPolygon") continue;
  const polygons = feature.geometry.type === "Polygon"
    ? [feature.geometry.coordinates]
    : feature.geometry.coordinates;
  for (const polygon of polygons) {
    for (const ring of polygon) {
      ring.forEach((position, index) => {
        const previous = ring[index - 1];
        if (previous && Math.abs(position[0]! - previous[0]!) > 180 && Math.max(position[1]!, previous[1]!) > -85) {
          visibleDatelineJumps.push(index);
        }
      });
    }
  }
}
assert(visibleDatelineJumps.length === 0, "The bundled basemap has no visible antimeridian fill strip");

console.log("refinement_manager.test.ts: all tests passed");
