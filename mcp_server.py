#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ExpForge MCP Server

A lightweight MCP (Model Context Protocol) server compatible with Python 3.7+.
No external dependencies required. Uses stdio transport with JSON-RPC 2.0.

Exposes ExpForge experiences, workflows, and knowledge as MCP tools and resources.
"""

import json
import logging
import os
import re
import sys
import traceback
from pathlib import Path

# Ensure we can import expforge.py utilities
BASE_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(BASE_DIR))
from expforge import (
    EXP_DIR, FLOW_DIR, KNOW_DIR,
    read_template, render_template, now_str, now_date, slugify, save_file
)

# ---------------------------------------------------------------------------
# Logging to stderr so it doesn't interfere with stdio JSON-RPC
# ---------------------------------------------------------------------------
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("expforge_mcp")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_title(text: str) -> str:
    m = re.search(r'^title:\s*"([^"]+)"', text, re.M)
    return m.group(1) if m else "Untitled"


def _search_directory(keyword: str, directory: Path, item_type: str):
    keyword_lower = keyword.lower()
    results = []
    for f in sorted(directory.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        if keyword_lower in text.lower():
            title = _extract_title(text)
            # build a short snippet around first match
            idx = text.lower().find(keyword_lower)
            start = max(0, idx - 80)
            end = min(len(text), idx + len(keyword) + 80)
            snippet = text[start:end].replace("\n", " ").strip()
            results.append({
                "type": item_type,
                "filename": f.name,
                "title": title,
                "snippet": "..." + snippet + "..."
            })
    return results


def _resolve_path(item_type: str, filename: str) -> Path:
    mapping = {
        "experience": EXP_DIR,
        "workflow": FLOW_DIR,
        "knowledge": KNOW_DIR,
        "experiences": EXP_DIR,
        "workflows": FLOW_DIR,
    }
    d = mapping.get(item_type)
    if not d:
        raise ValueError(f"Unknown type: {item_type}")
    return d / filename


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

def tool_search_items(arguments):
    keyword = arguments.get("keyword", "")
    item_type = arguments.get("type", "all")
    if not keyword:
        return {"error": "keyword is required"}

    results = []
    if item_type in ("all", "experience", "experiences"):
        results.extend(_search_directory(keyword, EXP_DIR, "experience"))
    if item_type in ("all", "workflow", "workflows"):
        results.extend(_search_directory(keyword, FLOW_DIR, "workflow"))
    if item_type in ("all", "knowledge"):
        results.extend(_search_directory(keyword, KNOW_DIR, "knowledge"))

    return {"results": results, "count": len(results)}


def tool_get_item(arguments):
    filename = arguments.get("filename")
    item_type = arguments.get("type")
    if not filename or not item_type:
        return {"error": "filename and type are required"}

    path = _resolve_path(item_type, filename)
    if not path.exists():
        return {"error": f"File not found: {path}"}

    content = path.read_text(encoding="utf-8")
    return {
        "filename": filename,
        "type": item_type,
        "title": _extract_title(content),
        "content": content
    }


def tool_list_items(arguments):
    item_type = arguments.get("type", "all")
    results = {}

    def list_dir(d: Path, name: str):
        items = []
        for f in sorted(d.glob("*.md")):
            text = f.read_text(encoding="utf-8")
            items.append({"filename": f.name, "title": _extract_title(text)})
        results[name] = items

    if item_type in ("all", "experience", "experiences"):
        list_dir(EXP_DIR, "experiences")
    if item_type in ("all", "workflow", "workflows"):
        list_dir(FLOW_DIR, "workflows")
    if item_type in ("all", "knowledge"):
        list_dir(KNOW_DIR, "knowledge")

    return results


def tool_capture_experience(arguments):
    title = arguments.get("title", "")
    if not title:
        return {"error": "title is required"}

    tags = arguments.get("tags", [])
    tags_str = "[" + ", ".join('"' + t + '"' for t in tags) + "]" if tags else "[]"

    ctx = {
        "title": title,
        "date": now_str(),
        "tags": tags_str,
        "category": arguments.get("category", "general"),
        "context": arguments.get("context", "待补充"),
        "process": arguments.get("process", "待补充"),
        "result": arguments.get("result", "待补充"),
        "reflection": arguments.get("reflection", "待补充"),
    }
    content = render_template("experience", ctx)
    filename = f"{now_date()}-{slugify(title)}.md"
    path = EXP_DIR / filename
    save_file(path, content)
    return {"success": True, "filename": filename, "type": "experience"}


def tool_add_knowledge(arguments):
    title = arguments.get("title", "")
    if not title:
        return {"error": "title is required"}

    tags = arguments.get("tags", [])
    tags_str = "[" + ", ".join('"' + t + '"' for t in tags) + "]" if tags else "[]"

    ctx = {
        "title": title,
        "date": now_str(),
        "tags": tags_str,
        "category": arguments.get("category", "general"),
        "concept": arguments.get("concept", "待补充"),
        "detail": arguments.get("detail", "待补充"),
        "examples": arguments.get("examples", "待补充"),
        "references": arguments.get("references", "待补充"),
    }
    content = render_template("knowledge", ctx)
    filename = f"{now_date()}-{slugify(title)}.md"
    path = KNOW_DIR / filename
    save_file(path, content)
    return {"success": True, "filename": filename, "type": "knowledge"}


def tool_distill_workflow(arguments):
    source = arguments.get("source_experience", "")
    title = arguments.get("title", "")
    if not source or not title:
        return {"error": "source_experience and title are required"}

    src_path = EXP_DIR / source
    if not src_path.exists():
        return {"error": f"Experience file not found: {source}"}

    tags = arguments.get("tags", [])
    tags_str = "[" + ", ".join('"' + t + '"' for t in tags) + "]" if tags else "[]"
    steps_raw = arguments.get("steps", "")
    step_lines = "\n".join(f"1. {s.strip()}" for s in steps_raw.split(";") if s.strip()) or "1. "

    ctx = {
        "title": title,
        "date": now_str(),
        "tags": tags_str,
        "source": source,
        "scenario": arguments.get("scenario", "待补充"),
        "prerequisites": arguments.get("prerequisites", "待补充"),
        "steps": step_lines,
        "faq": arguments.get("faq", "待补充"),
    }
    content = render_template("workflow", ctx)
    filename = f"{now_date()}-{slugify(title)}.md"
    path = FLOW_DIR / filename
    save_file(path, content)

    # Update experience file with back-link
    exp_text = src_path.read_text(encoding="utf-8")
    if "workflows:" in exp_text:
        exp_text = exp_text.replace("- workflows:", f"- workflows: {filename}", 1)
        save_file(src_path, exp_text)

    return {"success": True, "filename": filename, "type": "workflow"}


def tool_link_items(arguments):
    exp_file = arguments.get("experience_filename", "")
    flow_file = arguments.get("workflow_filename")
    know_file = arguments.get("knowledge_filename")

    exp_path = EXP_DIR / exp_file
    if not exp_path.exists():
        return {"error": f"Experience file not found: {exp_file}"}

    text = exp_path.read_text(encoding="utf-8")
    if flow_file and "workflows:" in text:
        text = text.replace("- workflows:", f"- workflows: {flow_file}", 1)
    if know_file and "knowledge:" in text:
        text = text.replace("- knowledge:", f"- knowledge: {know_file}", 1)

    save_file(exp_path, text)
    return {"success": True, "message": "Links updated"}


# ---------------------------------------------------------------------------
# Tool schema registry
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "search_items",
        "description": "Search across experiences, workflows, and knowledge base by keyword. Returns matching items with title, type, filename, and a text snippet.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "Search keyword"},
                "type": {"type": "string", "enum": ["all", "experience", "workflow", "knowledge"], "default": "all", "description": "Which category to search"}
            },
            "required": ["keyword"]
        }
    },
    {
        "name": "get_item",
        "description": "Get the full Markdown content of a specific experience, workflow, or knowledge entry by filename.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "Markdown filename (e.g. 20260417-api-timeout.md)"},
                "type": {"type": "string", "enum": ["experience", "workflow", "knowledge"], "description": "Item category"}
            },
            "required": ["filename", "type"]
        }
    },
    {
        "name": "list_items",
        "description": "List all items in experiences, workflows, and/or knowledge. Returns filenames and titles.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["all", "experience", "workflow", "knowledge"], "default": "all", "description": "Which category to list"}
            }
        }
    },
    {
        "name": "capture_experience",
        "description": "Create a new experience record in the experiences folder.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "category": {"type": "string", "default": "general"},
                "tags": {"type": "array", "items": {"type": "string"}, "default": []},
                "context": {"type": "string"},
                "process": {"type": "string"},
                "result": {"type": "string"},
                "reflection": {"type": "string"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "add_knowledge",
        "description": "Add a new knowledge entry to the knowledge base.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "category": {"type": "string", "default": "general"},
                "tags": {"type": "array", "items": {"type": "string"}, "default": []},
                "concept": {"type": "string"},
                "detail": {"type": "string"},
                "examples": {"type": "string"},
                "references": {"type": "string"}
            },
            "required": ["title"]
        }
    },
    {
        "name": "distill_workflow",
        "description": "Distill a standardized workflow (SOP) from an existing experience record.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_experience": {"type": "string", "description": "Filename of the source experience markdown"},
                "title": {"type": "string", "description": "Title for the new workflow"},
                "scenario": {"type": "string"},
                "prerequisites": {"type": "string"},
                "steps": {"type": "string", "description": "Step descriptions separated by semicolons"},
                "faq": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}, "default": []}
            },
            "required": ["source_experience", "title"]
        }
    },
    {
        "name": "link_items",
        "description": "Link an experience to a workflow and/or knowledge entry by updating the experience's frontmatter/links section.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "experience_filename": {"type": "string"},
                "workflow_filename": {"type": ["string", "null"]},
                "knowledge_filename": {"type": ["string", "null"]}
            },
            "required": ["experience_filename"]
        }
    }
]

TOOL_HANDLERS = {
    "search_items": tool_search_items,
    "get_item": tool_get_item,
    "list_items": tool_list_items,
    "capture_experience": tool_capture_experience,
    "add_knowledge": tool_add_knowledge,
    "distill_workflow": tool_distill_workflow,
    "link_items": tool_link_items,
}

# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

RESOURCES = [
    {
        "uri": "expforge://experiences/",
        "name": "Experiences Directory",
        "mimeType": "text/plain",
        "description": "All experience markdown files"
    },
    {
        "uri": "expforge://workflows/",
        "name": "Workflows Directory",
        "mimeType": "text/plain",
        "description": "All workflow markdown files"
    },
    {
        "uri": "expforge://knowledge/",
        "name": "Knowledge Directory",
        "mimeType": "text/plain",
        "description": "All knowledge markdown files"
    }
]


def resource_read(uri: str):
    prefix_map = {
        "expforge://experiences/": EXP_DIR,
        "expforge://workflows/": FLOW_DIR,
        "expforge://knowledge/": KNOW_DIR,
    }
    for prefix, directory in prefix_map.items():
        if uri.startswith(prefix):
            filename = uri[len(prefix):]
            if not filename:
                # directory listing
                items = []
                for f in sorted(directory.glob("*.md")):
                    items.append(f"{f.name}: {_extract_title(f.read_text(encoding='utf-8'))}")
                return "\n".join(items)
            path = directory / filename
            if path.exists():
                return path.read_text(encoding="utf-8")
            return None
    return None


# ---------------------------------------------------------------------------
# MCP Protocol over stdio
# ---------------------------------------------------------------------------

class MCPServer:
    def __init__(self):
        self.initialized = False

    def _send(self, msg: dict):
        data = json.dumps(msg, ensure_ascii=False)
        payload = data.encode("utf-8")
        header = f"Content-Length: {len(payload)}\r\n\r\n"
        sys.stdout.buffer.write(header.encode("utf-8") + payload)
        sys.stdout.buffer.flush()

    def _read_message(self):
        headers = {}
        while True:
            line = sys.stdin.readline()
            if not line:
                return None
            line = line.strip()
            if line == "":
                break
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()

        length = int(headers.get("content-length", 0))
        if length == 0:
            return None
        raw = sys.stdin.read(length)
        return json.loads(raw)

    def _handle_request(self, msg: dict):
        msg_id = msg.get("id")
        method = msg.get("method", "")
        params = msg.get("params", {})

        if method == "initialize":
            self._send({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {},
                        "resources": {}
                    },
                    "serverInfo": {
                        "name": "expforge-mcp-server",
                        "version": "0.1.0"
                    }
                }
            })
            self.initialized = True
            return

        if method == "notifications/initialized":
            return

        if not self.initialized:
            self._send({
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32002, "message": "Server not initialized"}
            })
            return

        if method == "tools/list":
            self._send({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": TOOLS}
            })
            return

        if method == "tools/call":
            name = params.get("name", "")
            arguments = params.get("arguments", {})
            handler = TOOL_HANDLERS.get(name)
            if handler is None:
                self._send({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {name}"}
                })
                return

            try:
                result = handler(arguments)
                self._send({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}
                        ]
                    }
                })
            except Exception as e:
                logger.error(traceback.format_exc())
                self._send({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": f"Error: {str(e)}"}
                        ],
                        "isError": True
                    }
                })
            return

        if method == "resources/list":
            self._send({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"resources": RESOURCES}
            })
            return

        if method == "resources/read":
            uri = params.get("uri", "")
            content = resource_read(uri)
            if content is None:
                self._send({
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32002, "message": f"Resource not found: {uri}"}
                })
                return

            self._send({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "contents": [
                        {"uri": uri, "mimeType": "text/markdown", "text": content}
                    ]
                }
            })
            return

        # unknown method
        self._send({
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"}
        })

    def run(self):
        logger.info("ExpForge MCP Server started")
        while True:
            try:
                msg = self._read_message()
                if msg is None:
                    break
                logger.debug("Received: %s", json.dumps(msg, ensure_ascii=False))
                self._handle_request(msg)
            except Exception:
                logger.error(traceback.format_exc())
                break
        logger.info("ExpForge MCP Server stopped")


if __name__ == "__main__":
    server = MCPServer()
    server.run()
