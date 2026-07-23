"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

const LAST_CAR_KEY = "mycar_assistant_car";

// Inline markup Gemini's replies actually use: **bold**, *italic*, `code`.
function renderInline(text) {
  const nodes = [];
  const pattern = /\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`/g;
  let lastIndex = 0;
  let match;
  let key = 0;
  while ((match = pattern.exec(text))) {
    if (match.index > lastIndex) nodes.push(text.slice(lastIndex, match.index));
    if (match[1] !== undefined) nodes.push(<strong key={key++}>{match[1]}</strong>);
    else if (match[2] !== undefined) nodes.push(<em key={key++}>{match[2]}</em>);
    else {
      nodes.push(
        <code key={key++} className="rounded bg-black/10 px-1 py-0.5 text-[13px] dark:bg-white/10">
          {match[3]}
        </code>
      );
    }
    lastIndex = pattern.lastIndex;
  }
  if (lastIndex < text.length) nodes.push(text.slice(lastIndex));
  return nodes;
}

// Assistant replies come back as light markdown (headings, bullets, bold,
// "---" dividers). Rendered as a small, dependency-free subset instead of a
// full markdown parser, since a mobile chat bubble only ever sees this shape.
function AssistantMessageContent({ text }) {
  const blocks = [];
  let list = [];

  const flushList = () => {
    if (list.length) {
      blocks.push(
        <ul key={`ul-${blocks.length}`} className="list-disc space-y-0.5 pl-4">
          {list}
        </ul>
      );
      list = [];
    }
  };

  text.split("\n").forEach((rawLine, i) => {
    const line = rawLine.trim();
    if (!line) return flushList();
    if (/^-{3,}$/.test(line)) {
      flushList();
      return blocks.push(<hr key={i} className="my-2 border-gray-300 dark:border-gray-700" />);
    }
    const heading = line.match(/^#{1,6}\s+(.*)/);
    if (heading) {
      flushList();
      return blocks.push(
        <p key={i} className="mt-2 font-semibold first:mt-0">
          {renderInline(heading[1])}
        </p>
      );
    }
    const bullet = line.match(/^[*-]\s+(.*)/);
    if (bullet) return list.push(<li key={i}>{renderInline(bullet[1])}</li>);
    flushList();
    blocks.push(
      <p key={i} className="mt-1 first:mt-0">
        {renderInline(line)}
      </p>
    );
  });
  flushList();

  return blocks;
}

export default function AssistantChat() {
  const [open, setOpen] = useState(false);
  const [cars, setCars] = useState(null); // null = not loaded yet
  const [carId, setCarId] = useState(null);
  const [conversation, setConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [input, setInput] = useState("");
  const [error, setError] = useState("");
  const bottomRef = useRef(null);
  const dialogRef = useRef(null);

  useEffect(() => {
    if (open) dialogRef.current?.focus();
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(event) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);

  const loadCars = useCallback(async () => {
    try {
      const data = await api("/cars/");
      const list = data.results || data;
      setCars(list);
      if (list.length === 1) {
        setCarId(list[0].id);
      } else if (list.length > 1) {
        const remembered = localStorage.getItem(LAST_CAR_KEY);
        if (remembered && list.some((car) => car.id === remembered)) setCarId(remembered);
      }
    } catch {
      setCars([]);
    }
  }, []);

  useEffect(() => {
    if (open && cars === null) loadCars();
  }, [open, cars, loadCars]);

  const loadConversation = useCallback(async (id) => {
    setLoading(true);
    setError("");
    setConversation(null);
    setMessages([]);
    try {
      const list = await api(`/assistant/conversations/?car=${id}`);
      const existing = (list.results || list)[0];
      // The list endpoint's serializer omits `messages`; only the detail
      // endpoint (and a fresh POST) includes full history.
      const convo = existing
        ? await api(`/assistant/conversations/${existing.id}/`)
        : await api("/assistant/conversations/", { method: "POST", body: { car: id } });
      setConversation(convo);
      setMessages(convo.messages || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (open && carId) loadConversation(carId);
  }, [open, carId, loadConversation]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending, carId]);

  function chooseCar(id) {
    setCarId(id);
    localStorage.setItem(LAST_CAR_KEY, id);
  }

  function changeCar() {
    setCarId(null);
    setConversation(null);
    setMessages([]);
  }

  async function send(event) {
    event.preventDefault();
    const content = input.trim();
    if (!content || sending || !conversation) return;

    setInput("");
    setError("");
    const localId = `local-${Date.now()}`;
    setMessages((prev) => [...prev, { id: localId, role: "user", content }]);
    setSending(true);
    try {
      const reply = await api(`/assistant/conversations/${conversation.id}/messages/`, {
        method: "POST",
        body: { content },
      });
      setMessages((prev) => [...prev, reply]);
    } catch (err) {
      setError(err.message);
      setMessages((prev) => prev.filter((m) => m.id !== localId));
      setInput(content);
    } finally {
      setSending(false);
    }
  }

  const car = cars?.find((c) => c.id === carId);
  const needsCarChoice = cars && cars.length > 1 && !carId;

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="card flex w-full items-center gap-3 text-left active:scale-[0.99]"
      >
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gray-100 text-xl dark:bg-gray-800">
          💬
        </span>
        <span className="min-w-0">
          <span className="block font-semibold">Ask the car assistant</span>
          <span className="block truncate text-[13px] text-gray-500 dark:text-gray-400">
            Service history, what&apos;s due, expenses, trouble codes…
          </span>
        </span>
      </button>

      {open && (
        <div
          className="fixed inset-0 z-40 flex items-end justify-center bg-black/40"
          onClick={() => setOpen(false)}
        >
          <div
            ref={dialogRef}
            role="dialog"
            aria-modal="true"
            aria-label="Car assistant"
            tabIndex={-1}
            className="flex h-[85vh] w-full max-w-lg flex-col rounded-t-2xl bg-white outline-none dark:bg-gray-900"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3 dark:border-gray-800">
              <div className="min-w-0">
                <p className="font-semibold">Car assistant</p>
                {car && (
                  <button onClick={changeCar} className="text-[13px] text-gray-500 dark:text-gray-400">
                    {car.make} {car.model} · switch
                  </button>
                )}
              </div>
              <button
                onClick={() => setOpen(false)}
                aria-label="Close"
                className="text-xl text-gray-400 dark:text-gray-500"
              >
                ✕
              </button>
            </div>

            <div className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
              {needsCarChoice && (
                <div className="flex justify-start">
                  <div className="max-w-[85%] rounded-2xl bg-gray-100 px-3.5 py-3 text-[14px] dark:bg-gray-800">
                    <p className="mb-2">Which car do you want to talk about?</p>
                    <div className="flex flex-wrap gap-2">
                      {cars.map((c) => (
                        <button
                          key={c.id}
                          onClick={() => chooseCar(c.id)}
                          className="rounded-full border border-gray-300 bg-white px-3 py-1.5 text-[13px] font-medium active:scale-95 dark:border-gray-700 dark:bg-gray-900"
                        >
                          {c.make} {c.model}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {loading && <p className="text-center text-sm text-gray-400 dark:text-gray-500">Loading…</p>}

              {!loading && carId && messages.length === 0 && !error && (
                <p className="text-center text-sm text-gray-400 dark:text-gray-500">
                  Ask about service history, what&apos;s due, expenses, or decode a trouble code.
                </p>
              )}

              {messages.map((message) => (
                <div key={message.id} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`max-w-[80%] rounded-2xl px-3.5 py-2.5 text-[14px] ${
                      message.role === "user"
                        ? "whitespace-pre-wrap bg-gray-900 text-white dark:bg-white dark:text-gray-900"
                        : "bg-gray-100 text-gray-900 dark:bg-gray-800 dark:text-gray-100"
                    }`}
                  >
                    {message.role === "user" ? message.content : <AssistantMessageContent text={message.content} />}
                    {message.tool_calls?.length > 0 && (
                      <p className="mt-1.5 text-[11px] font-medium opacity-60">
                        Checked: {message.tool_calls.map((call) => call.name).join(", ")}
                      </p>
                    )}
                  </div>
                </div>
              ))}

              {sending && (
                <div className="flex justify-start">
                  <div className="rounded-2xl bg-gray-100 px-3.5 py-2.5 text-[14px] text-gray-400 dark:bg-gray-800 dark:text-gray-500">
                    Thinking…
                  </div>
                </div>
              )}

              <div ref={bottomRef} />
            </div>

            {error && (
              <p className="mx-4 mb-2 rounded-xl bg-red-50 p-2 text-[13px] text-red-700 dark:bg-red-500/10 dark:text-red-400">
                {error}
              </p>
            )}

            <form onSubmit={send} className="flex items-center gap-2 border-t border-gray-200 p-3 dark:border-gray-800">
              <div className="flex-1">
                <input
                  className="input"
                  placeholder="Ask about this car…"
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  disabled={loading || sending || !conversation}
                />
              </div>
              <button
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gray-900 text-white disabled:opacity-50 dark:bg-white dark:text-gray-900"
                disabled={loading || sending || !input.trim() || !conversation}
                aria-label="Send"
              >
                ➤
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
