"""
Gemini-backed chat runner behind a thin, provider-agnostic surface.

`run_chat` takes the conversation history, the new user message and a
`ToolContext`, then runs the tool-calling loop: send -> if the model asks for
tools, execute them against our data and send the results back -> repeat until
the model produces a final answer (or we hit `max_steps`).

The `google-genai` import is deliberately lazy (inside `run_chat`) so the rest
of the app — and the test suite, which mocks `run_chat` — imports cleanly even
where the SDK isn't installed. Swapping providers later means writing another
`run_chat` with the same signature; nothing else changes.
"""
from django.conf import settings

from assistant.tools import FUNCTION_DECLARATIONS, execute_tool

SYSTEM_INSTRUCTION = (
    "You are the in-app assistant for 'GlavBox', helping a car owner understand "
    "and maintain their vehicle. You are talking about ONE specific car in their "
    "garage.\n\n"
    "Ground every factual answer in tool results — call the tools to fetch the "
    "vehicle's details, service history, maintenance status, expenses, decode its "
    "VIN, or explain a trouble code. Never invent part numbers, trouble-code "
    "meanings, service intervals or specs; if a tool can't provide the data, say "
    "so plainly rather than guessing.\n\n"
    "Be concise and practical. For anything safety-critical (brakes, steering, "
    "airbags, fuel), advise seeing a qualified mechanic.\n\n"
    "Format replies in plain text with light markdown only: headings, bullet "
    "lists, **bold**, `code`. Never use LaTeX or raw math notation (no $$...$$ "
    "or \\text{}/\\frac{}/\\mathbf{} commands) — the chat UI can't render it. "
    "For calculations, just show the numbers and result in plain words, e.g. "
    "'75 litres multiplied by 6,695 equals 502,125'."
)


class ChatResult:
    """Final assistant text plus a record of every tool call made along the way."""

    def __init__(self, text, tool_calls):
        self.text = text
        self.tool_calls = tool_calls


def _history_to_contents(history, types):
    """Map persisted user/model messages onto Gemini `contents`. Tool rows are skipped."""
    contents = []
    for role, content in history:
        if role not in ("user", "model") or not content:
            continue
        contents.append(types.Content(role=role, parts=[types.Part(text=content)]))
    return contents


def run_chat(history, user_text, context, max_steps=5):
    """
    Run one assistant turn.

    :param history: iterable of (role, content) tuples for prior turns.
    :param user_text: the new user message.
    :param context: assistant.tools.ToolContext (pinned car + owner).
    :returns: ChatResult
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=[types.Tool(function_declarations=FUNCTION_DECLARATIONS)],
        temperature=0.2,
    )

    contents = _history_to_contents(history, types)
    contents.append(types.Content(role="user", parts=[types.Part(text=user_text)]))

    tool_calls = []
    response = None
    for _ in range(max_steps):
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL, contents=contents, config=config
        )
        if not response.candidates:
            # Can happen when the prompt is blocked by safety filters.
            return ChatResult(text="I couldn't produce an answer for that. Try rephrasing?", tool_calls=tool_calls)
        candidate = response.candidates[0]
        contents.append(candidate.content)

        function_calls = [p.function_call for p in candidate.content.parts if getattr(p, "function_call", None)]
        if not function_calls:
            break

        response_parts = []
        for call in function_calls:
            args = dict(call.args) if call.args else {}
            result = execute_tool(call.name, args, context)
            tool_calls.append({"name": call.name, "args": args, "result": result})
            response_parts.append(types.Part.from_function_response(name=call.name, response={"result": result}))
        contents.append(types.Content(role="user", parts=response_parts))

    text = (getattr(response, "text", None) or "").strip() or (
        "I couldn't produce an answer for that. Try rephrasing?"
    )
    return ChatResult(text=text, tool_calls=tool_calls)
