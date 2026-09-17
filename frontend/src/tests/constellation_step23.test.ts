// @ts-expect-error El runner de Node aporta aquest mòdul; el bundle web no l'inclou.
import assert from "node:assert/strict";
import * as THREE from "three";

import type {
  ConstellationCatalogSnapshot,
  ConstellationDocumentSnapshot,
} from "../contracts/constellation_contracts";
import { ConstellationLayerRendererImpl } from "../view/three/layers/ConstellationLayerRenderer";


const catalog: ConstellationCatalogSnapshot = {
  type: "constellation_catalog",
  schemaVersion: 1,
  catalogVersion: "fixture-v1",
  source: { sourceFrame: "FK5_J2000", frame: "ICRS", maxArcStepDeg: 1 },
  constellations: [
    {
      id: "Ori", name: "Orion", frame: "ICRS", center: [83, -2], angularRadiusDeg: 15,
      visualComponents: [{ componentId: "main", sourceName: "Orion", rank: 1, strokes: [[[80, -5], [85, 0]]] }],
    },
    {
      id: "Ser", name: "Serpens", frame: "ICRS", center: [250, 2], angularRadiusDeg: 25,
      visualComponents: [
        { componentId: "caput", sourceName: "Serpens Caput", rank: 3, strokes: [[[235, 3], [240, 8]]] },
        { componentId: "cauda", sourceName: "Serpens Cauda", rank: 3, strokes: [[[275, -3], [280, 2]]] },
      ],
    },
  ],
};

function document(version: number, strokes: readonly (readonly { raDeg: number; decDeg: number }[])[]): ConstellationDocumentSnapshot {
  return {
    type: "constellation_document",
    schemaVersion: 1,
    documentRevision: version,
    constellations: [{
      constellationId: "user:test",
      name: "Prova",
      entityVersion: version,
      nodes: [],
      strokes,
    }],
    selectedConstellationId: "user:test",
    editing: false,
    canUndo: version > 1,
    canRedo: false,
    warning: null,
  };
}

const parent = new THREE.Group();
const renderer = new ConstellationLayerRendererImpl(parent);
renderer.presentCatalog(catalog);
assert.equal(renderer.metrics().catalogBuildCount, 2);
assert.equal(renderer.metrics().catalogEntities, 2);
renderer.presentCatalog(catalog);
assert.equal(renderer.metrics().catalogBuildCount, 2, "el mateix catàleg no es reconstrueix");

const orion = renderer.root.getObjectByName("constellation:catalog:Ori")!;
const serpens = renderer.root.getObjectByName("constellation:catalog:Ser")!;
assert.equal(orion.visible, false);
assert.equal(serpens.visible, false);
renderer.setSelectedCatalog("Ser");
assert.equal(orion.visible, false);
assert.equal(serpens.visible, true);
const beforeVisibility = renderer.metrics();
renderer.setShowAll(true);
assert.equal(orion.visible, true);
assert.equal(renderer.metrics().catalogBuildCount, beforeVisibility.catalogBuildCount);
assert.equal(serpens.children.length, 2, "Caput i Cauda són línies independents");

const camera = new THREE.PerspectiveCamera(60, 4 / 3, 0.1, 2_000_000);
camera.up.set(0, 0, 1);
const targetRa = THREE.MathUtils.degToRad(82.5);
const targetDec = THREE.MathUtils.degToRad(-2.5);
camera.lookAt(new THREE.Vector3(
  Math.cos(targetDec) * Math.cos(targetRa),
  Math.cos(targetDec) * Math.sin(targetRa),
  Math.sin(targetDec),
));
camera.updateMatrixWorld(true);
const viewport = { left: 0, top: 0, width: 800, height: 600 } as DOMRect;
const catalogHit = renderer.pickCatalog(400, 300, camera, viewport);
assert.equal(catalogHit?.entry.id, "Ori", "el picking consulta la geometria retinguda visible");
assert.ok(renderer.reprojectCatalog("Ori", camera, viewport));

renderer.presentDocument(document(1, [[{ raDeg: 10, decDeg: 10 }, { raDeg: 11, decDeg: 11 }]]));
const first = renderer.root.getObjectByName("constellation:user:user:test");
assert.ok(first);
assert.equal(renderer.metrics().userBuildCount, 1);
renderer.presentDocument(document(1, [[{ raDeg: 10, decDeg: 10 }, { raDeg: 11, decDeg: 11 }]]));
assert.equal(renderer.metrics().userBuildCount, 1, "entityVersion estable conserva la geometria");
renderer.presentDocument(document(2, [[{ raDeg: 20, decDeg: 20 }, { raDeg: 21, decDeg: 21 }]]));
assert.notEqual(renderer.root.getObjectByName("constellation:user:user:test"), first);
assert.equal(renderer.metrics().userBuildCount, 2);
assert.ok(renderer.metrics().disposeCount >= 1);

renderer.dispose();
assert.equal(parent.children.length, 0);

// Test ConstellationController with PointerGestureRouter without camera locking
import { ConstellationController } from "../application/ConstellationController";
import { PointerGestureRouter } from "../view/three/picking/PointerGestureRouter";
import type { StarPickProvider } from "../view/three/picking/StarPickProvider";
import type { StarPickHit } from "../contracts/star_picking_contracts";
import type { ToolsPage } from "../view/ui/drawer_pages/ToolsPage";
import type { WebSocketBridge } from "../bridge/WebSocketBridge";

const gestureRouter = new PointerGestureRouter();
const sentCommands: any[] = [];
const mockBridge = {
  sendConstellationCommand: (cmd: any) => { sentCommands.push(cmd); },
} as unknown as WebSocketBridge;

let starHit: StarPickHit | null = null;
const mockStarPicker = {
  pickNearest: (_x: number, _y: number, _maxPx: number) => starHit,
} as unknown as StarPickProvider;

let lastError: string | null = null;
let presentedSnapshot: ConstellationDocumentSnapshot | null = null;
const mockToolsPage = {
  presentConstellations: (s: ConstellationDocumentSnapshot) => { presentedSnapshot = s; },
  presentConstellationPending: () => {},
  presentConstellationError: (err: string) => { lastError = err; },
} as unknown as ToolsPage;

const controllerRenderer = new ConstellationLayerRendererImpl(new THREE.Group());
const controller = new ConstellationController({
  bridge: mockBridge,
  gestureRouter,
  starPicker: mockStarPicker,
  renderer: controllerRenderer,
  toolsPage: mockToolsPage,
});

// Normal picking handler registered after controller
let standardPickCalled = false;
gestureRouter.onTap(() => { standardPickCalled = true; });

// When editing is false, tap should pass through to standard pick
controller.present({
  ...document(1, []),
  editing: false,
});
let handled = (gestureRouter as any).tapCallbacks[0](100, 100);
assert.equal(handled, false, "Tap should not be consumed when editing is false");

// When editing is true with star hit, tap should send append_node and consume the tap
controller.present({
  ...document(2, []),
  editing: true,
  selectedConstellationId: "user:test",
});
starHit = {
  kind: "star",
  screenXCssPx: 100,
  screenYCssPx: 100,
  screenDistanceCssPx: 2,
  visualRadiusCssPx: 4,
  hitRadiusCssPx: 16,
  magnitude: 1.5,
  ref: { resourceId: "gaia_stars", resourceVersion: "v1", catalogIndex: 42 },
};
handled = (gestureRouter as any).tapCallbacks[0](100, 100);
assert.equal(handled, true, "Tap should be consumed when editing is true");
assert.equal(sentCommands.length, 1);
assert.equal(sentCommands[0].action, "append_node");
assert.equal(sentCommands[0].catalogIndex, 42);

// When editing is true without star hit, tap should present error and consume tap
controller.present({
  ...document(3, []),
  editing: true,
  selectedConstellationId: "user:test",
});
starHit = null;
handled = (gestureRouter as any).tapCallbacks[0](200, 200);
assert.equal(handled, true);
assert.equal(lastError, "No hi ha cap estrella visible a menys de 16 px.");

// Cleanup
controller.dispose();
controllerRenderer.dispose();
gestureRouter.dispose();

console.log("constellation_step23.test.ts: OK");
