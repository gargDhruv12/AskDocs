"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { ExternalLink, X } from "lucide-react";
import type { Citation } from "@/lib/types";

export function PageViewer({ citation, open, onOpenChange }: { citation: Citation | null; open: boolean; onOpenChange: (open: boolean) => void }) {
  if (!citation) return null;
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="dialog-content">
          <div className="dialog-header">
            <div>
              <Dialog.Title>{citation.document_name}</Dialog.Title>
              <Dialog.Description>Source page {citation.page_number}</Dialog.Description>
            </div>
            <Dialog.Close className="icon-button" aria-label="Close page viewer"><X size={20} /></Dialog.Close>
          </div>
          <div className="page-canvas">
            {/* Page images are generated from uploaded documents and served by the API. */}
            <img src={citation.image_url} alt={`Page ${citation.page_number} of ${citation.document_name}`} />
          </div>
          <a className="open-source" href={citation.image_url} target="_blank" rel="noreferrer">
            Open original size <ExternalLink size={14} />
          </a>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

