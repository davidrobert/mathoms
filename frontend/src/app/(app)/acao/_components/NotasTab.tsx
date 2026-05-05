"use client";

/** ADR-153 · Onda 1 — Notas livres por workspace em /acao.
 *
 * Substitui o placeholder ensinante da Onda 6. Lista pinned-first, edição
 * inline com autosave 500ms, criar/pinar/deletar inline. */

import { useCallback, useEffect, useRef, useState } from "react";
import { Pin, PinOff, Plus, StickyNote, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";

import { useWorkspaceNotes } from "@/hooks/useWorkspaceNotes";
import type { WorkspaceNote } from "@/lib/api";

interface NotasTabProps {
  workspaceId: string;
}

export function NotasTab({ workspaceId }: NotasTabProps) {
  const state = useWorkspaceNotes(workspaceId);

  if (state.loading) {
    return <Skeleton className="h-40" />;
  }

  return (
    <div className="flex flex-col gap-3">
      <NotasHeader onCreate={() => state.create()} />
      {state.error && (
        <Card>
          <CardContent className="py-4 text-sm text-destructive">{state.error}</CardContent>
        </Card>
      )}
      {state.notes.length === 0 ? (
        <Card>
          <CardContent className="py-0">
            <EmptyState
              icon={StickyNote}
              title="Nenhuma nota"
              description='Use "Nova nota" para registrar contexto livre — decisões em rascunho, agenda do casal, observações que ainda não viraram tarefa ou Decision.'
              layout="card"
            />
          </CardContent>
        </Card>
      ) : (
        <ul className="flex flex-col gap-3">
          {state.notes.map((note) => (
            <li key={note.id}>
              <NoteCard
                note={note}
                onChange={(payload) => state.update(note.id, payload)}
                onDelete={() => state.remove(note.id)}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function NotasHeader({ onCreate }: { onCreate: () => void | Promise<unknown> }) {
  return (
    <div className="flex items-center justify-between">
      <p className="text-sm text-muted-foreground">
        Anotações livres do workspace. Pinadas vêm primeiro; demais ordenadas por edição
        recente.
      </p>
      <Button size="sm" onClick={() => void onCreate()}>
        <Plus className="mr-1.5 h-4 w-4" /> Nova nota
      </Button>
    </div>
  );
}

interface NoteCardProps {
  note: WorkspaceNote;
  onChange: (payload: { title?: string | null; content?: string; pinned?: boolean }) => Promise<unknown>;
  onDelete: () => void | Promise<unknown>;
}

function NoteCardActions({ note, onChange, onDelete }: NoteCardProps) {
  return (
    <>
      <Button
        size="icon"
        variant="ghost"
        aria-label={note.pinned ? "Desafixar" : "Fixar"}
        onClick={() => void onChange({ pinned: !note.pinned })}
        title={note.pinned ? "Desafixar" : "Fixar"}
      >
        {note.pinned ? <Pin className="h-4 w-4 text-primary" /> : <PinOff className="h-4 w-4" />}
      </Button>
      <Button size="icon" variant="ghost" aria-label="Excluir nota" onClick={() => void onDelete()}>
        <Trash2 className="h-4 w-4 text-destructive" />
      </Button>
    </>
  );
}

function useAutoSave(note: WorkspaceNote, onChange: NoteCardProps["onChange"]) {
  const [title, setTitle] = useState(note.title ?? "");
  const [content, setContent] = useState(note.content);
  const lastSaved = useRef({ title: note.title ?? "", content: note.content });
  useEffect(() => {
    setTitle(note.title ?? "");
    setContent(note.content);
    lastSaved.current = { title: note.title ?? "", content: note.content };
  }, [note.id, note.title, note.content]);
  const flush = useCallback(() => {
    const p: { title?: string | null; content?: string } = {};
    if (title !== lastSaved.current.title) p.title = title || null;
    if (content !== lastSaved.current.content) p.content = content;
    if (Object.keys(p).length === 0) return;
    lastSaved.current = { title, content };
    void onChange(p);
  }, [title, content, onChange]);
  useEffect(() => {
    const h = window.setTimeout(flush, 500);
    return () => window.clearTimeout(h);
  }, [flush]);
  return { title, setTitle, content, setContent, flush };
}

function NoteCardBody({ title, setTitle, content, setContent, flush, props }: {
  title: string;
  setTitle: (v: string) => void;
  content: string;
  setContent: (v: string) => void;
  flush: () => void;
  props: NoteCardProps;
}) {
  return (
    <CardContent className="flex flex-col gap-2 py-3">
      <div className="flex items-center gap-2">
        <Input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={flush}
          placeholder="Título (opcional)"
          className="border-0 bg-transparent p-0 text-base font-semibold focus-visible:ring-0"
        />
        <NoteCardActions {...props} />
      </div>
      <Textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        onBlur={flush}
        placeholder="Anotação livre…"
        rows={4}
        className="resize-y border-0 bg-transparent p-0 text-sm focus-visible:ring-0"
      />
    </CardContent>
  );
}

function NoteCard(props: NoteCardProps) {
  const auto = useAutoSave(props.note, props.onChange);
  return (
    <Card>
      <NoteCardBody {...auto} props={props} />
    </Card>
  );
}
