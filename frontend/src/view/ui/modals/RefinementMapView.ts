import "ol/ol.css";
import Map from "ol/Map.js";
import View from "ol/View.js";
import GeoJSON from "ol/format/GeoJSON.js";
import Graticule from "ol/layer/Graticule.js";
import VectorLayer from "ol/layer/Vector.js";
import VectorSource from "ol/source/Vector.js";
import Draw, { createBox } from "ol/interaction/Draw.js";
import Modify from "ol/interaction/Modify.js";
import Snap from "ol/interaction/Snap.js";
import { defaults as defaultControls, MousePosition, ScaleLine, ZoomToExtent } from "ol/control.js";
import { circular } from "ol/geom/Polygon.js";
import CircleGeometry from "ol/geom/Circle.js";
import type Geometry from "ol/geom/Geometry.js";
import type Polygon from "ol/geom/Polygon.js";
import Feature from "ol/Feature.js";
import { Fill, Stroke, Style } from "ol/style.js";
import { fromLonLat, toLonLat } from "ol/proj.js";
import { getDistance } from "ol/sphere.js";
import { createStringXY } from "ol/coordinate.js";
import { feature as topologyFeature } from "topojson-client";
import landTopology from "world-atlas/land-110m.json";
import type {
  FeatureCollection as GeoJsonFeatureCollection,
  Geometry as GeoJsonGeometry,
  MultiPolygon as GeoJsonMultiPolygon,
  Polygon as GeoJsonPolygon,
  Position,
} from "geojson";
import type { RefinementGeometry, RefinementProductCandidate, RefinementWorkspace } from "../../../contracts/refinement_contracts";

type DrawMode = "rectangle" | "polygon" | "circle";

const geoJson = new GeoJSON();
const WORLD_EXTENT: [number, number, number, number] = [-20037508, -15538711, 20037508, 15538711];

const style = (fill: string, stroke: string, width = 2): Style => new Style({
  fill: new Fill({ color: fill }),
  stroke: new Stroke({ color: stroke, width }),
});

/** Self-contained OpenLayers AOI editor. The basemap is bundled Natural Earth 110m data. */
export class RefinementMapView {
  public readonly element = document.createElement("section");
  private readonly mapTarget = document.createElement("div");
  private readonly coordinateLabel = document.createElement("output");
  private readonly aoiSource = new VectorSource();
  private readonly selectedSource = new VectorSource();
  private readonly localSource = new VectorSource();
  private readonly plannedSource = new VectorSource();
  private readonly gapSource = new VectorSource();
  private readonly map: Map;
  private draw: Draw | null = null;
  private readonly modify: Modify;
  private readonly snap: Snap;
  private disposed = false;

  constructor(private readonly onAoiChanged: (aoi: RefinementGeometry | null) => void) {
    this.element.className = "refinement-map-panel";
    this.element.style.cssText = "display:grid;grid-template-rows:auto minmax(220px,34vh) auto;gap:8px";
    this.mapTarget.style.cssText = "position:relative;min-height:220px;border:1px solid var(--color-border,#3a4350);border-radius:6px;overflow:hidden;background:#07111d";
    this.mapTarget.setAttribute("aria-label", "Mapa per definir l'àrea d'interès");

    const land = buildBasemapLandFeatures();
    const landSource = new VectorSource({
      features: geoJson.readFeatures(land, { featureProjection: "EPSG:3857" }),
      wrapX: true,
    });
    const layers = [
      new VectorLayer({ source: landSource, style: style("#142334", "#334b60", 1), zIndex: 0 }),
      new VectorLayer({ source: this.selectedSource, style: style("rgba(34,211,238,.18)", "#22d3ee"), zIndex: 10 }),
      new VectorLayer({ source: this.localSource, style: style("rgba(74,222,128,.20)", "#4ade80"), zIndex: 20 }),
      new VectorLayer({ source: this.plannedSource, style: style("rgba(250,204,21,.22)", "#facc15"), zIndex: 30 }),
      new VectorLayer({ source: this.gapSource, style: style("rgba(248,113,113,.12)", "#f87171"), zIndex: 40 }),
      new VectorLayer({ source: this.aoiSource, style: style("rgba(250,204,21,.08)", "#fbbf24", 3), zIndex: 50 }),
    ];
    this.map = new Map({
      target: this.mapTarget,
      layers,
      controls: defaultControls({ attribution: false }).extend([
        new ScaleLine({ units: "metric", bar: true, steps: 2, text: true }),
        new MousePosition({ coordinateFormat: createStringXY(4), projection: "EPSG:4326", target: this.coordinateLabel }),
        new ZoomToExtent({ extent: WORLD_EXTENT, label: "⌂", tipLabel: "Veure tot el món" }),
      ]),
      view: new View({ center: fromLonLat([8, 40]), zoom: 2.5, minZoom: 1.5, maxZoom: 19, extent: WORLD_EXTENT }),
    });
    this.map.addLayer(new Graticule({
      strokeStyle: new Stroke({ color: "rgba(148,163,184,.22)", width: 1 }),
      showLabels: true,
      wrapX: true,
      zIndex: 5,
    }));
    this.modify = new Modify({ source: this.aoiSource });
    this.snap = new Snap({ source: this.aoiSource });
    this.map.addInteraction(this.modify);
    this.map.addInteraction(this.snap);
    this.modify.on("modifyend", () => this.emitAoi());

    this.element.append(this.toolbar(), this.mapTarget, this.footer());
  }

  public setAoi(aoi: RefinementGeometry | null): void {
    this.aoiSource.clear();
    if (aoi) this.aoiSource.addFeatures(geoJson.readFeatures(aoi, { featureProjection: "EPSG:3857" }));
  }

  public setWorkspace(workspace: RefinementWorkspace | null): void {
    this.localSource.clear();
    if (workspace?.aoi) this.addGeometry(this.localSource, workspace.aoi);
  }

  public setCandidates(candidates: readonly RefinementProductCandidate[], selectedIds: ReadonlySet<string>): void {
    this.selectedSource.clear();
    for (const candidate of candidates) {
      if (selectedIds.has(candidate.candidateId)) this.addGeometry(this.selectedSource, candidate.footprint);
    }
  }

  public setCoverage(existing: RefinementGeometry | null, planned: RefinementGeometry | null, remaining: RefinementGeometry | null): void {
    this.localSource.clear();
    this.plannedSource.clear();
    this.gapSource.clear();
    if (existing) this.addGeometry(this.localSource, existing);
    if (planned) this.addGeometry(this.plannedSource, planned);
    if (remaining) this.addGeometry(this.gapSource, remaining);
  }

  public setInstalled(installations: readonly { footprint?: RefinementGeometry | null }[]): void {
    const features: Feature[] = [];
    for (const inst of installations) {
      if (inst.footprint) {
        try {
          features.push(new Feature({
            geometry: geoJson.readGeometry(inst.footprint, { featureProjection: 'EPSG:3857' })
          }));
        } catch (e) {
          console.error("Invalid footprint GeoJSON", e);
        }
      }
    }
    this.localSource.addFeatures(features);
  }

  public updateSize(): void {
    this.map.updateSize();
  }

  public setManualBbox(text: string): void {
    const values = text.split(",").map((value) => Number(value.trim()));
    if (values.length !== 4 || values.some((value) => !Number.isFinite(value))) {
      throw new Error("El bbox ha de ser oest,sud,est,nord.");
    }
    const [west, south, east, north] = values as [number, number, number, number];
    if (west < -180 || east > 180 || south < -90 || north > 90 || west >= east || south >= north) {
      throw new Error("El bbox és fora d'EPSG:4326 o té extensió nul·la.");
    }
    const polygon: RefinementGeometry = {
      type: "Polygon",
      coordinates: [[[west, south], [east, south], [east, north], [west, north], [west, south]]],
    };
    this.setAoi(polygon);
    this.fitAoi();
    this.onAoiChanged(polygon);
  }

  public importGeoJson(text: string): void {
    const parsed: unknown = JSON.parse(text);
    const geometry = extractRefinementGeometry(parsed);
    this.setAoi(geometry);
    this.fitAoi();
    this.onAoiChanged(geometry);
  }

  public dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    if (this.draw) this.map.removeInteraction(this.draw);
    this.map.removeInteraction(this.modify);
    this.map.removeInteraction(this.snap);
    this.map.setTarget(undefined);
  }

  private toolbar(): HTMLElement {
    const bar = document.createElement("div");
    bar.style.cssText = "display:flex;flex-wrap:wrap;gap:6px;align-items:center";
    for (const [mode, label] of [["rectangle", "Rectangle"], ["polygon", "Polígon"], ["circle", "Cercle"]] as const) {
      const button = mapButton(label);
      button.onclick = () => this.startDraw(mode);
      bar.appendChild(button);
    }
    const clear = mapButton("Esborrar AOI");
    clear.onclick = () => { this.aoiSource.clear(); this.onAoiChanged(null); };
    const fit = mapButton("Enquadrar AOI");
    fit.onclick = () => this.fitAoi();
    bar.append(clear, fit);
    return bar;
  }

  private footer(): HTMLElement {
    const wrapper = document.createElement("div");
    wrapper.style.cssText = "display:grid;grid-template-columns:minmax(220px,1fr) auto;gap:8px;align-items:start";
    const inputs = document.createElement("div");
    inputs.style.cssText = "display:flex;gap:6px;min-width:0";
    const bbox = document.createElement("input");
    bbox.placeholder = "bbox: 1.5,41.0,3.4,42.9";
    bbox.ariaLabel = "Bbox manual en EPSG:4326";
    bbox.style.cssText = mapInputStyle();
    const applyBbox = mapButton("Aplicar bbox");
    applyBbox.onclick = () => {
      try { this.setManualBbox(bbox.value); } catch (error) { window.alert(errorMessage(error)); }
    };
    const importButton = mapButton("Importar GeoJSON");
    importButton.onclick = () => {
      const value = window.prompt("Enganxa una geometria Polygon o MultiPolygon en EPSG:4326:");
      if (!value) return;
      try { this.importGeoJson(value); } catch (error) { window.alert(errorMessage(error)); }
    };
    inputs.append(bbox, applyBbox, importButton);
    this.coordinateLabel.style.cssText = "font:11px var(--font-family-mono,monospace);color:var(--color-text-dim,#b6c0ca);padding:6px 0;white-space:nowrap";
    wrapper.append(inputs, this.coordinateLabel);
    return wrapper;
  }

  private startDraw(mode: DrawMode): void {
    if (this.draw) this.map.removeInteraction(this.draw);
    this.aoiSource.clear();
    this.draw = new Draw({
      source: this.aoiSource,
      type: mode === "polygon" ? "Polygon" : "Circle",
      ...(mode === "rectangle" ? { geometryFunction: createBox() } : {}),
    });
    this.map.addInteraction(this.draw);
    this.draw.once("drawend", (event) => {
      if (mode === "circle") this.replaceCircle(event.feature);
      queueMicrotask(() => this.emitAoi());
      if (this.draw) this.map.removeInteraction(this.draw);
      this.draw = null;
    });
  }

  private replaceCircle(feature: Feature<Geometry>): void {
    const geometry = feature.getGeometry();
    if (!(geometry instanceof CircleGeometry)) return;
    const center = geometry.getCenter();
    const edge: [number, number] = [center[0]! + geometry.getRadius(), center[1]!];
    const centerLonLat = toLonLat(center);
    const radiusM = getDistance(centerLonLat, toLonLat(edge));
    feature.setGeometry(circular(centerLonLat, radiusM, 96).transform("EPSG:4326", "EPSG:3857"));
  }

  private emitAoi(): void {
    const features = this.aoiSource.getFeatures();
    if (!features.length) {
      this.onAoiChanged(null);
      return;
    }
    const geometry = geoJson.writeGeometryObject(features[0]!.getGeometry()!, {
      featureProjection: "EPSG:3857",
      dataProjection: "EPSG:4326",
      decimals: 7,
    });
    this.onAoiChanged(extractRefinementGeometry(geometry));
  }

  private addGeometry(source: VectorSource, geometry: RefinementGeometry): void {
    source.addFeatures(geoJson.readFeatures(geometry, { featureProjection: "EPSG:3857" }));
  }

  private fitAoi(): void {
    if (this.aoiSource.isEmpty()) return;
    const extent = this.aoiSource.getExtent();
    if (extent) this.map.getView().fit(extent, { padding: [32, 32, 32, 32], maxZoom: 12, duration: 250 });
  }
}

export function buildBasemapLandFeatures(): GeoJsonFeatureCollection<GeoJsonGeometry> {
  const rawLand = topologyFeature(
    landTopology,
    landTopology.objects["land"]!,
  ) as unknown as GeoJsonFeatureCollection<GeoJsonGeometry>;
  return {
    ...rawLand,
    features: rawLand.features.map((feature) => ({
      ...feature,
      geometry: splitAntimeridianGeometry(feature.geometry),
    })),
  };
}

/**
 * Cut polygons at +/-180 before Web Mercator projection.
 *
 * OpenLayers projects each longitude independently. A ring such as the
 * Eurasian landmass therefore turns a short 180E -> 180W edge into a line
 * across the whole map, painting a false horizontal strip of land. Keeping
 * each output ring inside one longitude world removes that projection
 * ambiguity while preserving the wrapped vector layer.
 */
export function splitAntimeridianGeometry(geometry: GeoJsonGeometry): GeoJsonGeometry {
  if (geometry.type === "Polygon") {
    return polygonsToGeometry(splitPolygonAtAntimeridian(geometry.coordinates));
  }
  if (geometry.type === "MultiPolygon") {
    return polygonsToGeometry(
      geometry.coordinates.flatMap((polygon) => splitPolygonAtAntimeridian(polygon)),
    );
  }
  return geometry;
}

function polygonsToGeometry(
  polygons: Position[][][],
): GeoJsonPolygon | GeoJsonMultiPolygon {
  return polygons.length === 1
    ? { type: "Polygon", coordinates: polygons[0]! }
    : { type: "MultiPolygon", coordinates: polygons };
}

function splitPolygonAtAntimeridian(polygon: Position[][]): Position[][][] {
  const outer = polygon[0];
  if (!outer || !ringCrossesAntimeridian(outer)) return [polygon];

  const unwrappedOuter = closePolarRing(unwrapRing(outer));
  const [minimumLongitude, maximumLongitude] = longitudeBounds(unwrappedOuter);
  const firstWorld = Math.ceil((-180 - maximumLongitude) / 360);
  const lastWorld = Math.floor((180 - minimumLongitude) / 360);
  const fragments: Position[][][] = [];

  for (let world = firstWorld; world <= lastWorld; world += 1) {
    const longitudeOffset = world * 360;
    const shiftedOuter = unwrappedOuter.map((position) => shiftLongitude(position, longitudeOffset));
    const clippedOuter = clipRingToWorld(shiftedOuter);
    if (clippedOuter.length < 4) continue;

    const fragment: Position[][] = [clippedOuter];
    for (const hole of polygon.slice(1)) {
      const shiftedHole = unwrapRing(hole).map((position) => shiftLongitude(position, longitudeOffset));
      const clippedHole = clipRingToWorld(shiftedHole);
      if (clippedHole.length >= 4 && pointInRing(clippedHole[0]!, clippedOuter)) fragment.push(clippedHole);
    }
    fragments.push(fragment);
  }
  return fragments.length ? fragments : [polygon];
}

function ringCrossesAntimeridian(ring: Position[]): boolean {
  return ring.some((position, index) => (
    index > 0 && Math.abs(position[0]! - ring[index - 1]![0]!) > 180
  ));
}

function unwrapRing(ring: Position[]): Position[] {
  const result: Position[] = [];
  for (const position of ring) {
    let longitude = position[0]!;
    const previous = result.at(-1)?.[0];
    if (previous !== undefined) {
      while (longitude - previous > 180) longitude -= 360;
      while (longitude - previous < -180) longitude += 360;
    }
    result.push([longitude, ...position.slice(1)]);
  }
  return result;
}

function closePolarRing(ring: Position[]): Position[] {
  const first = ring[0];
  const last = ring.at(-1);
  if (!first || !last || Math.abs(last[0]! - first[0]!) < 359.999) return ring;
  const averageLatitude = ring.reduce((sum, position) => sum + position[1]!, 0) / ring.length;
  const pole = averageLatitude < 0 ? -90 : 90;
  return [...ring, [last[0]!, pole], [first[0]!, pole], [...first]];
}

function longitudeBounds(ring: Position[]): [number, number] {
  const longitudes = ring.map((position) => position[0]!);
  return [Math.min(...longitudes), Math.max(...longitudes)];
}

function shiftLongitude(position: Position, offset: number): Position {
  return [position[0]! + offset, ...position.slice(1)];
}

function clipRingToWorld(ring: Position[]): Position[] {
  return clipRingAtLongitude(
    clipRingAtLongitude(ring, -180, true),
    180,
    false,
  );
}

function clipRingAtLongitude(ring: Position[], boundary: number, keepGreater: boolean): Position[] {
  if (ring.length < 3) return [];
  const vertices = positionsEqual(ring[0]!, ring.at(-1)!) ? ring.slice(0, -1) : [...ring];
  if (!vertices.length) return [];
  const output: Position[] = [];
  let previous = vertices.at(-1)!;
  let previousInside = longitudeInside(previous[0]!, boundary, keepGreater);

  for (const current of vertices) {
    const currentInside = longitudeInside(current[0]!, boundary, keepGreater);
    if (currentInside !== previousInside) output.push(intersectionAtLongitude(previous, current, boundary));
    if (currentInside) output.push(current);
    previous = current;
    previousInside = currentInside;
  }
  if (output.length >= 3 && !positionsEqual(output[0]!, output.at(-1)!)) output.push([...output[0]!]);
  return output;
}

function longitudeInside(longitude: number, boundary: number, keepGreater: boolean): boolean {
  return keepGreater ? longitude >= boundary : longitude <= boundary;
}

function intersectionAtLongitude(start: Position, end: Position, longitude: number): Position {
  const denominator = end[0]! - start[0]!;
  const ratio = denominator === 0 ? 0 : (longitude - start[0]!) / denominator;
  return [longitude, start[1]! + ((end[1]! - start[1]!) * ratio)];
}

function positionsEqual(left: Position, right: Position): boolean {
  return left[0] === right[0] && left[1] === right[1];
}

function pointInRing(point: Position, ring: Position[]): boolean {
  let inside = false;
  for (let index = 0, previous = ring.length - 1; index < ring.length; previous = index, index += 1) {
    const currentPosition = ring[index]!;
    const previousPosition = ring[previous]!;
    const crosses = (currentPosition[1]! > point[1]!) !== (previousPosition[1]! > point[1]!);
    const edgeLongitude = ((previousPosition[0]! - currentPosition[0]!) * (point[1]! - currentPosition[1]!))
      / (previousPosition[1]! - currentPosition[1]!) + currentPosition[0]!;
    if (crosses && point[0]! < edgeLongitude) inside = !inside;
  }
  return inside;
}

export function extractRefinementGeometry(value: unknown): RefinementGeometry {
  if (!value || typeof value !== "object") throw new Error("GeoJSON buit o invàlid.");
  const object = value as Record<string, unknown>;
  const candidate = object["type"] === "Feature" ? (object["geometry"] as unknown) : value;
  if (!candidate || typeof candidate !== "object") throw new Error("La Feature no conté geometria.");
  const geometry = candidate as Record<string, unknown>;
  if (geometry["type"] !== "Polygon" && geometry["type"] !== "MultiPolygon") {
    throw new Error("Només s'admeten Polygon i MultiPolygon.");
  }
  validateCoordinates(geometry["coordinates"]);
  return geometry as unknown as RefinementGeometry;
}

function validateCoordinates(value: unknown): void {
  if (!Array.isArray(value) || value.length === 0) throw new Error("La geometria no té coordenades.");
  const visit = (item: unknown): void => {
    if (!Array.isArray(item) || item.length === 0) throw new Error("Coordenades GeoJSON incompletes.");
    if (typeof item[0] === "number") {
      const lon = Number(item[0]);
      const lat = Number(item[1]);
      if (!Number.isFinite(lon) || !Number.isFinite(lat) || lon < -180 || lon > 180 || lat < -90 || lat > 90) {
        throw new Error("Les coordenades han d'estar en EPSG:4326.");
      }
      return;
    }
    for (const child of item) visit(child);
  };
  visit(value);
}

function mapButton(label: string): HTMLButtonElement {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.style.cssText = "padding:6px 10px;border:1px solid var(--color-border,#3a4350);border-radius:4px;background:var(--color-surface-raised,#202833);color:var(--color-text,#e5e7eb);font-size:11px;cursor:pointer";
  return button;
}

function mapInputStyle(): string {
  return "min-width:0;flex:1;padding:6px 8px;border:1px solid var(--color-border,#3a4350);border-radius:4px;background:var(--color-surface,#141a22);color:var(--color-text,#e5e7eb);font-size:11px";
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
