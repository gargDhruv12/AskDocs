"use client";

import { ChangeEvent, DragEvent, useEffect, useRef, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { AlertCircle, Check, ChevronDown, Eye, FileText, LoaderCircle, ShieldCheck, Trash2, UploadCloud, X, XCircle } from "lucide-react";
import { deleteDocument, getDocument, listDocuments, uploadDocuments } from "@/lib/api";
import type { DocumentRecord, ProcessingStage } from "@/lib/types";
import { DocumentViewer } from "./document-viewer";

const stages: { key: ProcessingStage; label: string }[] = [
  { key: "parsing", label: "Parsing" }, { key: "classifying", label: "Classifying" }, { key: "indexing", label: "Indexing" }, { key: "indexed", label: "Ready" }
];

export function UploadWorkspace() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewingId, setViewingId] = useState<string | null>(null);
  const [removing, setRemoving] = useState<DocumentRecord | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [removalError, setRemovalError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let active = true;
    async function refresh() {
      try { const latest = await listDocuments(); if (active) setDocuments(latest); } catch { if (active) setDocuments([]); }
    }
    void refresh();
    const timer = window.setInterval(refresh, 2000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  async function processFiles(files: File[]) {
    if (!files.length) return;
    setError(null);
    if (files.length > 10) { setError("Choose no more than 10 files at once."); return; }
    const invalid = files.find((file) => file.size > 20 * 1024 * 1024 || !["application/pdf", "image/png", "image/jpeg", "text/plain"].includes(file.type));
    if (invalid) { setError(`${invalid.name} is unsupported or larger than 20 MB.`); return; }
    setUploading(true);
    try {
      const created = await uploadDocuments(files);
      setDocuments((current) => [...created, ...current]);
      created.forEach((document) => pollDocument(document.id));
    } catch (error) { setError(error instanceof Error ? error.message : "Upload failed"); }
    finally { setUploading(false); }
  }

  function pollDocument(id: string) {
    const timer = window.setInterval(async () => {
      try {
        const latest = await getDocument(id);
        setDocuments((current) => current.map((doc) => doc.id === id ? latest : doc));
        if (latest.status === "indexed" || latest.status === "failed") window.clearInterval(timer);
      } catch { window.clearInterval(timer); }
    }, 1200);
  }

  function onDrop(event: DragEvent) { event.preventDefault(); setDragging(false); void processFiles(Array.from(event.dataTransfer.files)); }
  function onChange(event: ChangeEvent<HTMLInputElement>) { void processFiles(Array.from(event.target.files ?? [])); event.target.value = ""; }

  async function confirmRemoval() {
    if (!removing || deleting) return;
    setDeleting(true);
    setRemovalError(null);
    try {
      await deleteDocument(removing.id);
      setDocuments((current) => current.filter((document) => document.id !== removing.id));
      setRemoving(null);
    } catch (reason) {
      setRemovalError(reason instanceof Error ? reason.message : "Could not remove the document.");
    } finally { setDeleting(false); }
  }

  return (
    <div className="upload-page">
      <section className="upload-hero">
        <div>
          <p className="eyebrow">Document library</p>
          <h1>Turn difficult documents<br />into <em>reliable evidence.</em></h1>
          <p>Upload PDFs, scans, images, or text files. Every page is extracted, rendered, classified, and indexed.</p>
        </div>
        <div className="privacy-card"><ShieldCheck size={22} /><div><strong>Private by design</strong><span>Validated uploads, isolated storage, workspace-scoped retrieval.</span></div></div>
      </section>

      <section className={dragging ? "dropzone dragging" : "dropzone"} onDragOver={(e) => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={onDrop}>
        <input ref={inputRef} id="document-upload" type="file" multiple accept=".pdf,.png,.jpg,.jpeg,.txt" onChange={onChange} hidden />
        <div className="drop-icon">{uploading ? <LoaderCircle className="spin" /> : <UploadCloud />}</div>
        <h2>{uploading ? "Securing your uploads..." : "Drop documents here"}</h2>
        <p>PDF, PNG, JPG, or TXT | up to 20 MB each</p>
        <button className="primary-button" onClick={() => inputRef.current?.click()} disabled={uploading}>Choose files</button>
      </section>
      {error && <div className="upload-error" role="alert"><AlertCircle size={17} /> {error}</div>}

      <section className="library-section">
        <div className="section-heading"><div><p className="eyebrow">Processing activity</p><h2>Your documents</h2></div><span>{documents.length} total</span></div>
        <div className="document-table">
          {documents.length === 0 && <div className="empty-library">Your processed documents will appear here.</div>}
          {documents.map((document) => <DocumentRow key={document.id} document={document} onView={() => setViewingId(document.id)} onRemove={() => { setRemovalError(null); setRemoving(document); }} />)}
        </div>
      </section>
      <DocumentViewer documentId={viewingId} open={Boolean(viewingId)} onOpenChange={(open) => !open && setViewingId(null)} />
      <Dialog.Root open={Boolean(removing)} onOpenChange={(open) => { if (!open && !deleting) setRemoving(null); }}>
        <Dialog.Portal>
          <Dialog.Overlay className="dialog-overlay" />
          <Dialog.Content className="confirm-dialog">
            <div className="confirm-icon"><Trash2 size={20} /></div>
            <Dialog.Title>Remove document?</Dialog.Title>
            <Dialog.Description><strong>{removing?.name}</strong> and all of its extracted pages will be permanently deleted from this workspace.</Dialog.Description>
            {removalError && <div className="confirm-error" role="alert"><AlertCircle size={15} /> {removalError}</div>}
            <div className="confirm-actions">
              <Dialog.Close className="cancel-button" disabled={deleting}>Cancel</Dialog.Close>
              <button className="danger-button" disabled={deleting} onClick={() => void confirmRemoval()}>{deleting ? <LoaderCircle className="spin" size={15} /> : <Trash2 size={15} />} Remove permanently</button>
            </div>
            <Dialog.Close className="icon-button confirm-close" aria-label="Close removal confirmation" disabled={deleting}><X size={18} /></Dialog.Close>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}

function DocumentRow({ document, onView, onRemove }: { document: DocumentRecord; onView: () => void; onRemove: () => void }) {
  const currentIndex = stages.findIndex((stage) => stage.key === document.status);
  return (
    <details className="document-record">
      <summary className="document-row">
        <div className="file-icon"><FileText size={21} /></div>
        <div className="file-details">
          <div className="file-title"><strong>{document.name}</strong>{document.origin === "sample" && <span className="sample-badge">Sample</span>}</div>
          <span>{document.page_count ? `${document.page_count} ${document.page_count === 1 ? "page" : "pages"}` : "Preparing pages"}{document.classification ? ` | ${document.classification.document_type}` : ""}</span>
        </div>
        {document.status === "failed" ? <div className="failed-state"><XCircle size={16} /> {document.error ?? "Processing failed"}</div> : (
          <div className="stage-track">
            {stages.map((stage, index) => (
              <div className={index <= currentIndex ? "stage complete" : "stage"} key={stage.key}>
                <span>{index < currentIndex || document.status === "indexed" ? <Check size={11} /> : index === currentIndex ? <LoaderCircle className="spin" size={11} /> : null}</span>
                <small>{stage.label}</small>
              </div>
            ))}
          </div>
        )}
        <ChevronDown className="row-chevron" size={17} />
      </summary>
      <div className="document-details-panel">
        {document.classification && (
          <div className="classification-panel">
            <div><small>Sensitivity</small><strong className={`sensitivity ${document.classification.sensitivity}`}>{document.classification.sensitivity}</strong></div>
            <div><small>Language</small><strong>{document.classification.language}</strong></div>
            <div><small>Confidence</small><strong>{Math.round(document.classification.confidence * 100)}%</strong></div>
            <p>{document.classification.summary}</p>
            <div className="topic-list">{document.classification.topics.map((topic) => <span key={topic}>{topic}</span>)}</div>
          </div>
        )}
        <div className="document-actions">
          <button className="document-action" disabled={document.page_count === 0} onClick={onView}><Eye size={15} /> View document</button>
          {document.origin === "upload" && <button className="document-action danger" disabled={!(["indexed", "failed"] as ProcessingStage[]).includes(document.status)} onClick={onRemove}><Trash2 size={15} /> Remove</button>}
        </div>
      </div>
    </details>
  );
}
