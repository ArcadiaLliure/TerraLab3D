import type { TemporalSceneState } from "../contracts/temporal_scene_contracts";
import { TemporalSceneCoordinator } from "../application/TemporalSceneCoordinator";

let passed = 0;
let failed = 0;

function assert(condition: boolean, message: string): void {
  if (condition) passed++;
  else {
    failed++;
    console.error(`FAIL: ${message}`);
  }
}

function state(
  generationId: number,
  authority: "preview" | "authoritative",
  observerGeneration = 1,
): TemporalSceneState {
  return {
    generationId,
    simulationTime: "2026-09-02T12:00:00Z",
    observerGeneration,
    authority,
    solarSystem: {} as never,
    skyEnvironment: {} as never,
    lightingEnvironment: {} as never,
    astronomicalEvent: {} as never,
  } as TemporalSceneState;
}

const coordinator = new TemporalSceneCoordinator();
assert(coordinator.accept(state(5, "preview")), "a newer preview is accepted");
assert(!coordinator.accept(state(4, "authoritative")), "older science never rolls back a preview");
assert(
  coordinator.accept(state(5, "authoritative")),
  "science promotes the preview of the same generation",
);
assert(!coordinator.accept(state(5, "preview")), "preview cannot demote authoritative state");
assert(coordinator.accept(state(6, "preview")), "the next interactive generation advances");
assert(!coordinator.accept(state(5, "authoritative")), "late prior science remains stale");
assert(
  !coordinator.accept(state(6, "authoritative", 2)),
  "observer identity cannot change inside one temporal generation",
);

console.log(`Temporal scene tests: ${passed} passed, ${failed} failed`);
if (failed > 0) throw new Error(`${failed} temporal scene test(s) failed`);
