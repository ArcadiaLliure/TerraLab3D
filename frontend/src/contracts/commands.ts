export interface SetObserverLocationCommand {
  readonly type: "set_observer_location";
  readonly latitudeDeg: number;
  readonly longitudeDeg: number;
  readonly heightOffsetM: number;
}

export interface SetSimulationTimeCommand {
  readonly type: "set_simulation_time";
  readonly instantIso: string;
}

export interface SetTimeRateCommand {
  readonly type: "set_time_rate";
  readonly rate: number;
}

export interface SetLayerVisibilityCommand {
  readonly type: "set_layer_visibility";
  readonly layerId: string;
  readonly visible: boolean;
}

export interface SearchTargetCommand {
  readonly type: "search_target";
  readonly query: string;
}

export interface LoadDatasetCommand {
  readonly type: "load_dataset";
  readonly datasetId: string;
}

export interface CancelOperationCommand {
  readonly type: "cancel_operation";
  readonly operationId: string;
}

export type ApplicationCommand =
  | SetObserverLocationCommand
  | SetSimulationTimeCommand
  | SetTimeRateCommand
  | SetLayerVisibilityCommand
  | SearchTargetCommand
  | LoadDatasetCommand
  | CancelOperationCommand;
