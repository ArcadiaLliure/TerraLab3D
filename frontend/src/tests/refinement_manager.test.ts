import { buildRefinementTree, RefinementSession } from "../application/RefinementSession";
import { extractRefinementGeometry } from "../view/ui/modals/RefinementMapView";
import type {
  RefinementCandidatesMessage,
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
    { categoryKey: "agriculture", parentKey: "surface", label: "Agricultura", depth: 1, state: "partial", verifiedPercent: 40, plannedPercent: 40, installationIds: [], applicable: true },
    { categoryKey: "agriculture.arable", parentKey: "agriculture", label: "Conreus herbacis", depth: 2, state: "complete", verifiedPercent: 100, plannedPercent: 100, installationIds: ["installed-1"], applicable: true },
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
    schemaVersion: 3,
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

const tree = buildRefinementTree(workspace.nodes);
assert(tree.length === 1 && tree[0]?.children.length === 1, "The flat TLST workspace becomes a hierarchy");
assert(tree[0]?.children[0]?.installationIds[0] === "installed-1", "Installation state remains attached to the leaf");

const featureGeometry = extractRefinementGeometry({ type: "Feature", properties: {}, geometry: aoi });
assert(featureGeometry.type === "Polygon", "GeoJSON Feature geometry is accepted");
let rejected = false;
try {
  extractRefinementGeometry({ type: "Point", coordinates: [181, 0] });
} catch {
  rejected = true;
}
assert(rejected, "Unsupported or invalid GeoJSON is rejected");

console.log("refinement_manager.test.ts: all tests passed");
