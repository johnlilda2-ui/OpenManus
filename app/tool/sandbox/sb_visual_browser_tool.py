from __future__ import annotations

import json
from typing import Optional

from app.tool.base import ToolResult
from app.tool.sandbox.sb_browser_tool import SandboxBrowserTool
from platform_core.visual_diff import average_hash, hash_similarity, image_sha256


class SandboxVisualBrowserTool(SandboxBrowserTool):
    """Sandbox browser tool with deterministic screenshot hashing for visual diffs."""

    name: str = "sandbox_browser"
    description: str = (
        "Browser automation in an isolated sandbox. Includes navigation, interaction, "
        "and a snapshot action that returns a deterministic visual hash and optional "
        "similarity score against a reference screenshot hash."
    )

    parameters: dict = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "navigate_to",
                    "go_back",
                    "wait",
                    "click_element",
                    "input_text",
                    "send_keys",
                    "switch_tab",
                    "close_tab",
                    "scroll_down",
                    "scroll_up",
                    "scroll_to_text",
                    "get_dropdown_options",
                    "select_dropdown_option",
                    "click_coordinates",
                    "drag_drop",
                    "snapshot",
                ],
            },
            "url": {"type": "string"},
            "index": {"type": "integer"},
            "text": {"type": "string"},
            "amount": {"type": "integer"},
            "page_id": {"type": "integer"},
            "keys": {"type": "string"},
            "seconds": {"type": "integer"},
            "x": {"type": "integer"},
            "y": {"type": "integer"},
            "element_source": {"type": "string"},
            "element_target": {"type": "string"},
            "reference_hash": {
                "type": "string",
                "description": "Optional average-hash returned by an earlier snapshot for visual comparison",
            },
        },
        "required": ["action"],
    }

    async def execute(
        self,
        action: str,
        url: Optional[str] = None,
        index: Optional[int] = None,
        text: Optional[str] = None,
        amount: Optional[int] = None,
        page_id: Optional[int] = None,
        keys: Optional[str] = None,
        seconds: Optional[int] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
        element_source: Optional[str] = None,
        element_target: Optional[str] = None,
        reference_hash: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        if action != "snapshot":
            return await super().execute(
                action=action,
                url=url,
                index=index,
                text=text,
                amount=amount,
                page_id=page_id,
                keys=keys,
                seconds=seconds,
                x=x,
                y=y,
                element_source=element_source,
                element_target=element_target,
                **kwargs,
            )

        state = await self.get_current_state()
        if state.error:
            return state
        if not state.base64_image:
            return self.fail_response("Browser did not return a screenshot for snapshot")
        try:
            current_hash = average_hash(state.base64_image)
            payload = {
                "visual_hash": current_hash,
                "sha256": image_sha256(state.base64_image),
                "visual_diff_score": hash_similarity(reference_hash, current_hash)
                if reference_hash
                else 100.0,
                "reference_hash": reference_hash,
                "url": "",
            }
            try:
                state_info = json.loads(state.output or "{}")
                payload["url"] = state_info.get("url", "")
                payload["title"] = state_info.get("title", "")
            except json.JSONDecodeError:
                pass
            return ToolResult(
                output=json.dumps(payload, indent=2),
                base64_image=state.base64_image,
            )
        except Exception as exc:
            return self.fail_response(f"Visual snapshot scoring failed: {exc}")

    @classmethod
    def create_with_sandbox(cls, sandbox):
        return cls(sandbox=sandbox)
