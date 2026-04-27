export type AnalysisStatus = "pending" | "running" | "done" | "failed";

export interface UserPublic {
  id: string;
  email: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  user: UserPublic;
}

export interface AnalysisSummary {
  id: string;
  filename: string;
  status: AnalysisStatus;
  codigo_curso: string | null;
  modelo: string;
  dispatcher: string;
  enriquecer: boolean;
  generar_resumen: boolean;
  created_at: string;
  completed_at: string | null;
  duration_s: number | null;
  error: string | null;
}

export interface Hallazgo {
  regla_id: string;
  regla: string;
  estado: "CUMPLE" | "NO CUMPLE";
  evidencia: string;
  correccion?: string | null;
  correccion_enriquecida?: string | null;
}

export interface ResultadoSeccion {
  seccion: string;
  hallazgos: Hallazgo[];
  error?: string;
}

export interface Reporte {
  archivo: string;
  modelo: string;
  codigo_curso: string | null;
  dispatcher: string;
  total_secciones: number;
  resultados: ResultadoSeccion[];
  resumenes?: { oficina: string; docente: string };
}

export interface AnalysisDetail extends AnalysisSummary {
  report: Reporte | null;
}

export interface ProgressEvent {
  event: string;
  data: Record<string, unknown>;
}
