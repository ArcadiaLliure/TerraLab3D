import "./styles/TerrainGotoMenu.css";

export interface TerrainGotoDestination {
  readonly eastM: number;
  readonly northM: number;
  readonly terrainUpM: number;
  readonly latitudeDeg: number;
  readonly longitudeDeg: number;
}

/** A one-action context menu for a real point on the resident DEM mesh. */
export class TerrainGotoMenu {
  private readonly root: HTMLDivElement;
  private readonly gotoButton: HTMLButtonElement;
  private destination: TerrainGotoDestination | null = null;

  constructor(
    private readonly parent: HTMLElement,
    private readonly onGoto: (destination: TerrainGotoDestination) => void,
  ) {
    this.root = document.createElement("div");
    this.root.className = "terrain-goto-menu";
    this.root.hidden = true;
    this.root.setAttribute("role", "menu");
    this.gotoButton = document.createElement("button");
    this.gotoButton.type = "button";
    this.gotoButton.className = "terrain-goto-menu__action";
    this.gotoButton.setAttribute("role", "menuitem");
    this.gotoButton.addEventListener("click", () => {
      if (this.destination) this.onGoto(this.destination);
      this.hide();
    });
    this.root.appendChild(this.gotoButton);
    this.parent.appendChild(this.root);
  }

  show(clientX: number, clientY: number, destination: TerrainGotoDestination): void {
    this.destination = destination;
    this.gotoButton.textContent = `Goto: ${formatCoordinate(destination.latitudeDeg)}, ${formatCoordinate(destination.longitudeDeg)}`;
    const bounds = this.parent.getBoundingClientRect();
    this.root.hidden = false;
    const left = clamp(clientX - bounds.left, 8, Math.max(8, bounds.width - 286));
    const top = clamp(clientY - bounds.top, 8, Math.max(8, bounds.height - 42));
    this.root.style.left = `${left}px`;
    this.root.style.top = `${top}px`;
  }

  hide(): void {
    this.destination = null;
    this.root.hidden = true;
  }

  dispose(): void {
    this.root.remove();
  }
}

function formatCoordinate(value: number): string {
  return `${value.toFixed(6)}°`;
}

function clamp(value: number, minimum: number, maximum: number): number {
  return Math.max(minimum, Math.min(maximum, value));
}
