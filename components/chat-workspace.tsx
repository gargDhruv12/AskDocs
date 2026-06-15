"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowUp, FileSearch, LoaderCircle, Mic, MicOff, Plus, Sparkles } from "lucide-react";
import { askQuestion, listDocuments } from "@/lib/api";
import type { ChatMessage, Citation, DocumentRecord } from "@/lib/types";
import { PageViewer } from "./page-viewer";

const starterQuestions = [
  "What are the most important findings across these documents?",
  "Which documents contain confidential or restricted information?",
  "Summarize the key numbers and cite their source pages."
];

export function ChatWorkspace() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef<{ start: () => void; stop: () => void } | null>(null);

  useEffect(() => {
    let active = true;
    async function refresh() {
      try { const latest = await listDocuments(); if (active) setDocuments(latest); } catch { if (active) setDocuments([]); }
    }
    void refresh();
    const timer = window.setInterval(refresh, 2000);
    return () => { active = false; window.clearInterval(timer); };
  }, []);

  async function submit(question = input) {
    const clean = question.trim();
    if (!clean || loading) return;
    const userMessage: ChatMessage = { id: crypto.randomUUID(), role: "user", content: clean };
    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);
    setInput("");
    setLoading(true);
    try {
      const answer = await askQuestion(nextMessages);
      setMessages((current) => [...current, answer]);
    } catch (error) {
      setMessages((current) => [...current, {
        id: crypto.randomUUID(), role: "assistant",
        content: error instanceof Error ? error.message : "I could not complete that request."
      }]);
    } finally { setLoading(false); }
  }

  function onSubmit(event: FormEvent) { event.preventDefault(); void submit(); }

  function toggleVoice() {
    const SpeechRecognition = (window as unknown as { SpeechRecognition?: new () => any; webkitSpeechRecognition?: new () => any }).SpeechRecognition
      ?? (window as unknown as { webkitSpeechRecognition?: new () => any }).webkitSpeechRecognition;
    if (!SpeechRecognition) { setInput("Voice input is not supported in this browser."); return; }
    if (listening) { recognitionRef.current?.stop(); setListening(false); return; }
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.onresult = (event: any) => {
      const transcript = Array.from(event.results).map((result: any) => result[0].transcript).join("");
      setInput(transcript);
    };
    recognition.onend = () => setListening(false);
    recognitionRef.current = recognition;
    recognition.start();
    setListening(true);
  }

  const indexedCount = documents.filter((document) => document.status === "indexed").length;

  return (
    <div className="chat-layout">
      <aside className="context-rail">
        <div className="eyebrow">Knowledge base</div>
        <div className="library-count"><strong>{indexedCount}</strong><span>documents ready</span></div>
        <div className="document-mini-list">
          {documents.filter((doc) => doc.status === "indexed").slice(0, 5).map((doc) => (
            <div className="document-mini" key={doc.id}>
              <FileSearch size={16} />
              <div><span>{doc.name}</span><small>{doc.page_count} pages</small></div>
            </div>
          ))}
        </div>
        <Link href="/upload" className="secondary-button"><Plus size={16} /> Add documents</Link>
        <div className="rail-note">Answers are generated only from indexed pages. Every claim can be traced back to its source.</div>
      </aside>

      <section className="conversation">
        {messages.length === 0 ? (
          <div className="empty-state">
            <div className="signal-mark"><span /><span /><span /></div>
            <p className="eyebrow">Evidence-first intelligence</p>
            <h1>Ask your documents.<br /><em>Verify every answer.</em></h1>
            <p className="lead">Search reports, scans, handwriting, and tables with exact page-level evidence.</p>
            <div className="starter-grid">
              {starterQuestions.map((question) => <button key={question} onClick={() => void submit(question)}>{question}<ArrowUp size={15} /></button>)}
            </div>
          </div>
        ) : (
          <div className="message-list">
            {messages.map((message) => (
              <article key={message.id} className={`message ${message.role}`}>
                <div className="message-role">{message.role === "user" ? "You" : "AskDocs"}</div>
                <div className="message-body">{message.content}</div>
                {message.citations && message.citations.length > 0 && (
                  <div className="citation-grid">
                    {message.citations.map((citation) => (
                      <button className="citation-card" key={citation.id} onClick={() => setSelectedCitation(citation)}>
                        <img src={citation.image_url} alt="" />
                        <span><strong>{citation.document_name}</strong><small>Page {citation.page_number}</small></span>
                      </button>
                    ))}
                  </div>
                )}
              </article>
            ))}
            {loading && <div className="thinking"><LoaderCircle className="spin" size={18} /> Reviewing the evidence</div>}
          </div>
        )}

        <div className="composer-wrap">
          <form className="composer" onSubmit={onSubmit}>
            <textarea value={input} onChange={(event) => setInput(event.target.value)} placeholder="Ask a question about your documents..." rows={2}
              onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void submit(); } }} />
            <div className="composer-actions">
              <button type="button" className={listening ? "voice-button active" : "voice-button"} onClick={toggleVoice} aria-label="Toggle voice input">
                {listening ? <MicOff size={18} /> : <Mic size={18} />} {listening && <span>Listening...</span>}
              </button>
              <button className="send-button" type="submit" disabled={!input.trim() || loading}><ArrowUp size={19} /></button>
            </div>
          </form>
          <p><Sparkles size={12} /> Grounded answers can still contain errors. Check the cited pages.</p>
        </div>
      </section>
      <PageViewer citation={selectedCitation} open={Boolean(selectedCitation)} onOpenChange={(open) => !open && setSelectedCitation(null)} />
    </div>
  );
}
