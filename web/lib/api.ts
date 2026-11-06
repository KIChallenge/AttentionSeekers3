"use client";

/** Thin client for the StatAgent API (proxied same-origin via next.config rewrites). */

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
  /** 404 = endpoint not built yet (backend in progress) */
  get notAvailable() {
    return this.status === 404;
  }
}

function detailOf(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const d = (body as { detail: unknown }).detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d))
      return d
        .map((x) => (x && typeof x === "object" && "msg" in x ? String((x as { msg: unknown }).msg) : String(x)))
        .join("; ");
  }
  if (body && typeof body === "object" && "message" in body) return String((body as { message: unknown }).message);
  return fallback;
}

async function handle<T>(res: Response): Promise<T> {
  const text = await res.text();
  let body: unknown = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  if (!res.ok) {
    const fallback =
      res.status === 404
        ? "noch nicht verfügbar"
        : res.status >= 500
          ? `Serverfehler (${res.status}) – das Backend ist nicht erreichbar oder meldet einen Fehler.`
          : `Fehler ${res.status}`;
    throw new ApiError(res.status, detailOf(body, fallback));
  }
  return body as T;
}

export async function apiGet<T>(path: string, signal?: AbortSignal): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, { signal, cache: "no-store" });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ApiError(0, "Backend nicht erreichbar (http://127.0.0.1:8000).");
  }
  return handle<T>(res);
}

export async function apiPost<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ApiError(0, "Backend nicht erreichbar (http://127.0.0.1:8000).");
  }
  return handle<T>(res);
}

export type SseEvent = { event: string; data: unknown };

/**
 * POST and consume a Server-Sent-Events response incrementally.
 * Calls onEvent for every complete event; resolves when the stream ends.
 */
export async function streamSse(
  path: string,
  body: unknown,
  onEvent: (ev: SseEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(path, {
      method: "POST",
      headers: { "content-type": "application/json", accept: "text/event-stream" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal,
    });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ApiError(0, "Backend nicht erreichbar (http://127.0.0.1:8000).");
  }
  if (!res.ok || !res.body) await handle(res);
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const flush = (block: string) => {
    let event = "message";
    const data: string[] = [];
    for (const line of block.split("\n")) {
      if (line.startsWith(":")) continue;
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
    }
    if (!data.length) return;
    const raw = data.join("\n");
    let parsed: unknown = raw;
    try {
      parsed = JSON.parse(raw);
    } catch {
      /* keep raw text */
    }
    onEvent({ event, data: parsed });
  };
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
    let idx = buffer.indexOf("\n\n");
    while (idx >= 0) {
      flush(buffer.slice(0, idx));
      buffer = buffer.slice(idx + 2);
      idx = buffer.indexOf("\n\n");
    }
  }
  if (buffer.trim()) flush(buffer);
}
