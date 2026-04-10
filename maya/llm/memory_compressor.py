from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class MemoryCompressor:
    threshold_ratio: float = 0.7

    def maybe_compress(
        self,
        messages: list[dict[str, str]],
        max_context_tokens: int = 128_000,
    ) -> list[dict[str, str]]:
        # Heuristic token estimate (4 chars per token average)
        total_chars = sum(len(m.get("content", "")) for m in messages)
        est_tokens = total_chars // 4
        if est_tokens <= int(max_context_tokens * self.threshold_ratio):
            return messages

        if len(messages) <= 20:
            return messages

        head = messages[:5]
        tail = messages[-10:]
        middle = messages[5:-10]

        summary_lines = ["<compressed_history>"]
        for msg in middle[:40]:
            summary_lines.append(f"[{msg.get('role', 'user')}] {msg.get('content', '')[:240]}")
        summary_lines.append("</compressed_history>")

        preserved = {
            "role": "user",
            "content": "\n".join(summary_lines),
        }
        return head + [preserved] + tail
