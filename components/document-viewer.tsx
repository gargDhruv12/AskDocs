"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { getDocumentPages } from "@/lib/api";
import type { DocumentPages } from "@/lib/types";

export function DocumentViewer({ documentId, open, onOpenChange }: { documentId: string | null; open: boolean; onOpenChange: (open: boolean) => void }) {
  const [manifest, setManifest] = useState<DocumentPages | null>(null);
  const [pageIndex, setPageIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const pageScrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open || !documentId) return;
    let active = true;
    setManifest(null);
    setPageIndex(0);
    setError(null);
    getDocumentPages(documentId)
      .then((result) => { if (active) setManifest(result); })
      .catch((reason) => { if (active) setError(reason instanceof Error ? reason.message : "Could not load document pages."); });
    return () => { active = false; };
  }, [documentId, open]);

  useEffect(() => {
    pageScrollRef.current?.scrollTo({ top: 0, left: 0 });
  }, [pageIndex]);

  const page = manifest?.pages[pageIndex];
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="document-viewer-dialog">
          <div className="dialog-header">
            <div>
              <Dialog.Title>{manifest?.document_name ?? "Document viewer"}</Dialog.Title>
              <Dialog.Description>{manifest ? `${manifest.page_count} ${manifest.page_count === 1 ? "page" : "pages"}` : "Loading rendered pages..."}</Dialog.Description>
            </div>
            <Dialog.Close className="icon-button" aria-label="Close document viewer"><X size={20} /></Dialog.Close>
          </div>
          {error && <div className="viewer-error" role="alert">{error}</div>}
          {!error && !manifest && <div className="viewer-loading">Loading document...</div>}
          {!error && manifest && !page && <div className="viewer-error">No rendered pages are available for this document.</div>}
          {page && (
            <>
              <div className="document-page-stage">
                <button className="page-nav previous" aria-label="Previous page" disabled={pageIndex === 0} onClick={() => setPageIndex((current) => current - 1)}><ChevronLeft /></button>
                <div className="document-page-scroll" ref={pageScrollRef}>
                  <img src={page.image_url} alt={`Page ${page.page_number} of ${manifest?.document_name}`} />
                </div>
                <button className="page-nav next" aria-label="Next page" disabled={!manifest || pageIndex === manifest.pages.length - 1} onClick={() => setPageIndex((current) => current + 1)}><ChevronRight /></button>
              </div>
              <div className="viewer-footer">
                <span>Page {page.page_number} of {manifest?.page_count}</span>
                <div className="page-thumbnails" aria-label="Document pages">
                  {manifest?.pages.map((item, index) => (
                    <button className={index === pageIndex ? "page-thumbnail active" : "page-thumbnail"} key={item.page_number} onClick={() => setPageIndex(index)} aria-label={`View page ${item.page_number}`}>
                      <img src={item.image_url} alt="" /><span>{item.page_number}</span>
                    </button>
                  ))}
                </div>
              </div>
            </>
          )}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
