export interface BinaryResourceReference {
  readonly resourceId: string;
  readonly version: number;
  readonly transportHandle: string;
  readonly byteLength: number;
}

export interface BinaryResourceClient {
  /** Obté un recurs binari transferible sense Base64. */
  fetch(reference: BinaryResourceReference): Promise<ArrayBuffer>;
  /** Revoca handles locals i permet alliberar memòria. */
  release(reference: BinaryResourceReference): Promise<void>;
}
