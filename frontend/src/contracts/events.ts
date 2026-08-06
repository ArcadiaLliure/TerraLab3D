export interface SessionChangedEvent {
  readonly type: "session_changed";
  readonly revision: number;
}

export interface OperationProgressedEvent {
  readonly type: "operation_progressed";
  readonly operationId: string;
  readonly progressFraction?: number;
  readonly messageKey: string;
}

export interface OperationFailedEvent {
  readonly type: "operation_failed";
  readonly operationId: string;
  readonly errorCode: string;
  readonly messageKey: string;
  readonly recoverable: boolean;
}

export type ApplicationEvent =
  | SessionChangedEvent
  | OperationProgressedEvent
  | OperationFailedEvent;
