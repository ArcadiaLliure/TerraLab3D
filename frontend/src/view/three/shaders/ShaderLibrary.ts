export interface ShaderProgramDescriptor {
  readonly shaderId: string;
  readonly vertexSourceKey: string;
  readonly fragmentSourceKey: string;
  readonly uniformNames: readonly string[];
}

export interface ShaderLibrary {
  /** Retorna descriptors de shaders; no compila ni inventa codi shader en aquesta fase. */
  descriptor(shaderId: string): ShaderProgramDescriptor;
}
