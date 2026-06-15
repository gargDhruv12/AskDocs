export type ProcessingStage = "queued" | "parsing" | "classifying" | "indexing" | "indexed" | "failed";

export interface Classification {
  document_type: string;
  topics: string[];
  content_characteristics: string[];
  sensitivity: "public" | "internal" | "confidential" | "restricted";
  language: string;
  summary: string;
  confidence: number;
}

export interface DocumentRecord {
  id: string;
  name: string;
  status: ProcessingStage;
  progress: number;
  page_count: number;
  created_at: string;
  origin: "sample" | "upload";
  error?: string | null;
  classification?: Classification | null;
}

export interface DocumentPage {
  page_number: number;
  image_url: string;
}

export interface DocumentPages {
  document_id: string;
  document_name: string;
  page_count: number;
  pages: DocumentPage[];
}

export interface Citation {
  id: string;
  document_id: string;
  document_name: string;
  page_number: number;
  excerpt: string;
  image_url: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
}
