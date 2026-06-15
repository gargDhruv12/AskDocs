import type { ChatMessage, DocumentPages, DocumentRecord } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { ...init?.headers }
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(body.detail ?? "Request failed");
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function listDocuments() {
  return request<DocumentRecord[]>("/api/documents");
}

export function uploadDocuments(files: File[]) {
  const data = new FormData();
  files.forEach((file) => data.append("files", file));
  return request<DocumentRecord[]>("/api/documents/upload", { method: "POST", body: data });
}

export function getDocument(id: string) {
  return request<DocumentRecord>(`/api/documents/${id}`);
}

export function getDocumentPages(id: string) {
  return request<DocumentPages>(`/api/documents/${id}/pages`);
}

export function deleteDocument(id: string) {
  return request<void>(`/api/documents/${id}`, { method: "DELETE" });
}

export function askQuestion(messages: ChatMessage[]) {
  return request<ChatMessage>("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages: messages.map(({ role, content }) => ({ role, content })) })
  });
}
