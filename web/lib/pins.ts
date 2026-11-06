"use client";

import { useEffect, useState } from "react";
import type { AnswerCardData } from "@/components/chat/answer-card";

const KEY = "statagent-pins";
const EVENT = "statagent:pins";

export type Pin = { id: string; pinnedAt: string; question: string; card: AnswerCardData };

function read(): Pin[] {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Pin[]) : [];
  } catch {
    return [];
  }
}

function write(pins: Pin[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify(pins));
  } catch {
    /* storage blocked or full */
  }
  window.dispatchEvent(new Event(EVENT));
}

export function addPin(pin: Pin) {
  write([pin, ...read().filter((p) => p.id !== pin.id)].slice(0, 12));
}

/** W-07: replace the snapshot of a pinned card with a freshly computed one (same question, same reading). */
export function updatePin(id: string, card: AnswerCardData) {
  write(read().map((p) => (p.id === id ? { ...p, card, pinnedAt: new Date().toISOString() } : p)));
}

export function removePin(id: string) {
  write(read().filter((p) => p.id !== id));
}

/** Cards pinned from the chat to the dashboard – stored only in this browser. */
export function usePins(): Pin[] {
  const [pins, setPins] = useState<Pin[]>([]);
  useEffect(() => {
    const update = () => setPins(read());
    update();
    window.addEventListener(EVENT, update);
    window.addEventListener("storage", update);
    return () => {
      window.removeEventListener(EVENT, update);
      window.removeEventListener("storage", update);
    };
  }, []);
  return pins;
}
