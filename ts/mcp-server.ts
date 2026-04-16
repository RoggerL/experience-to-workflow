#!/usr/bin/env node
/**
 * ExpForge MCP Server (TypeScript)
 *
 * Uses the official MCP SDK with stdio transport.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListResourcesRequestSchema,
  ListToolsRequestSchema,
  ReadResourceRequestSchema,
  type Tool,
} from "@modelcontextprotocol/sdk/types.js";
import * as fs from "fs";
import * as path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const BASE_DIR = path.resolve(__dirname, "..");
const EXP_DIR = path.join(BASE_DIR, "experiences");
const FLOW_DIR = path.join(BASE_DIR, "workflows");
const KNOW_DIR = path.join(BASE_DIR, "knowledge");
const TMPL_DIR = path.join(BASE_DIR, "templates");

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

function nowStr(): string {
  const d = new Date();
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function nowDate(): string {
  const d = new Date();
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}`;
}

function slugify(text: string): string {
  return text
    .replace(/[^\w\s-]/g, "")
    .trim()
    .replace(/\s+/g, "-");
}

function readTemplate(name: string): string {
  return fs.readFileSync(path.join(TMPL_DIR, `${name}.md`), "utf-8");
}

function renderTemplate(name: string, ctx: Record<string, string>): string {
  let tmpl = readTemplate(name);
  for (const [k, v] of Object.entries(ctx)) {
    tmpl = tmpl.split(`{{${k}}}`).join(v);
  }
  return tmpl;
}

function saveFile(filePath: string, content: string): void {
  fs.writeFileSync(filePath, content, "utf-8");
  console.error(`[已保存] ${filePath}`);
}

function extractTitle(text: string): string {
  const m = text.match(/^title:\s*"([^"]+)"/m);
  return m ? m[1] : "Untitled";
}

function ensureDir(dir: string): void {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

function resolvePath(itemType: string, filename: string): string {
  const mapping: Record<string, string> = {
    experience: EXP_DIR,
    workflow: FLOW_DIR,
    knowledge: KNOW_DIR,
    experiences: EXP_DIR,
    workflows: FLOW_DIR,
  };
  const d = mapping[itemType];
  if (!d) throw new Error(`Unknown type: ${itemType}`);
  return path.join(d, filename);
}

function listMdFiles(dir: string): string[] {
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f: string) => f.endsWith(".md"))
    .sort();
}

function searchDirectory(keyword: string, directory: string, itemType: string) {
  const keywordLower = keyword.toLowerCase();
  const results: any[] = [];
  for (const f of listMdFiles(directory)) {
    const filePath = path.join(directory, f);
    const text = fs.readFileSync(filePath, "utf-8");
    if (text.toLowerCase().includes(keywordLower)) {
      const title = extractTitle(text);
      const idx = text.toLowerCase().indexOf(keywordLower);
      const start = Math.max(0, idx - 80);
      const end = Math.min(text.length, idx + keyword.length + 80);
      const snippet = text.slice(start, end).replace(/\n/g, " ").trim();
      results.push({
        type: itemType,
        filename: f,
        title,
        snippet: `...${snippet}...`,
      });
    }
  }
  return results;
}

// ---------------------------------------------------------------------------
// Tool handlers
// ---------------------------------------------------------------------------

function toolSearchItems(args: any) {
  const keyword = args.keyword ?? "";
  const itemType = args.type ?? "all";
  if (!keyword) return { error: "keyword is required" };

  const results: any[] = [];
  if (["all", "experience", "experiences"].includes(itemType)) {
    results.push(...searchDirectory(keyword, EXP_DIR, "experience"));
  }
  if (["all", "workflow", "workflows"].includes(itemType)) {
    results.push(...searchDirectory(keyword, FLOW_DIR, "workflow"));
  }
  if (["all", "knowledge"].includes(itemType)) {
    results.push(...searchDirectory(keyword, KNOW_DIR, "knowledge"));
  }

  return { results, count: results.length };
}

function toolGetItem(args: any) {
  const filename = args.filename;
  const itemType = args.type;
  if (!filename || !itemType) return { error: "filename and type are required" };

  const filePath = resolvePath(itemType, filename);
  if (!fs.existsSync(filePath)) return { error: `File not found: ${filePath}` };

  const content = fs.readFileSync(filePath, "utf-8");
  return { filename, type: itemType, title: extractTitle(content), content };
}

function toolListItems(args: any) {
  const itemType = args.type ?? "all";
  const results: Record<string, any[]> = {};

  const listDir = (dir: string, name: string) => {
    results[name] = listMdFiles(dir).map((f) => {
      const text = fs.readFileSync(path.join(dir, f), "utf-8");
      return { filename: f, title: extractTitle(text) };
    });
  };

  if (["all", "experience", "experiences"].includes(itemType)) listDir(EXP_DIR, "experiences");
  if (["all", "workflow", "workflows"].includes(itemType)) listDir(FLOW_DIR, "workflows");
  if (["all", "knowledge"].includes(itemType)) listDir(KNOW_DIR, "knowledge");

  return results;
}

function toolCaptureExperience(args: any) {
  const title = args.title ?? "";
  if (!title) return { error: "title is required" };

  const tags: string[] = args.tags ?? [];
  const tagsStr = tags.length ? `[${tags.map((t) => `"${t}"`).join(", ")}]` : "[]";

  const ctx: Record<string, string> = {
    title,
    date: nowStr(),
    tags: tagsStr,
    category: args.category ?? "general",
    context: args.context ?? "待补充",
    process: args.process ?? "待补充",
    result: args.result ?? "待补充",
    reflection: args.reflection ?? "待补充",
  };
  const content = renderTemplate("experience", ctx);
  const filename = `${nowDate()}-${slugify(title)}.md`;
  const filePath = path.join(EXP_DIR, filename);
  saveFile(filePath, content);
  return { success: true, filename, type: "experience" };
}

function toolAddKnowledge(args: any) {
  const title = args.title ?? "";
  if (!title) return { error: "title is required" };

  const tags: string[] = args.tags ?? [];
  const tagsStr = tags.length ? `[${tags.map((t) => `"${t}"`).join(", ")}]` : "[]";

  const ctx: Record<string, string> = {
    title,
    date: nowStr(),
    tags: tagsStr,
    category: args.category ?? "general",
    concept: args.concept ?? "待补充",
    detail: args.detail ?? "待补充",
    examples: args.examples ?? "待补充",
    references: args.references ?? "待补充",
  };
  const content = renderTemplate("knowledge", ctx);
  const filename = `${nowDate()}-${slugify(title)}.md`;
  const filePath = path.join(KNOW_DIR, filename);
  saveFile(filePath, content);
  return { success: true, filename, type: "knowledge" };
}

function toolDistillWorkflow(args: any) {
  const source = args.source_experience ?? "";
  const title = args.title ?? "";
  if (!source || !title) return { error: "source_experience and title are required" };

  const srcPath = path.join(EXP_DIR, source);
  if (!fs.existsSync(srcPath)) return { error: `Experience file not found: ${source}` };

  const tags: string[] = args.tags ?? [];
  const tagsStr = tags.length ? `[${tags.map((t) => `"${t}"`).join(", ")}]` : "[]";
  const stepsRaw: string = args.steps ?? "";
  const stepLines =
    stepsRaw
      .split(";")
      .map((s) => s.trim())
      .filter(Boolean)
      .map((s) => `1. ${s}`)
      .join("\n") || "1. ";

  const ctx: Record<string, string> = {
    title,
    date: nowStr(),
    tags: tagsStr,
    source,
    scenario: args.scenario ?? "待补充",
    prerequisites: args.prerequisites ?? "待补充",
    steps: stepLines,
    faq: args.faq ?? "待补充",
  };
  const content = renderTemplate("workflow", ctx);
  const filename = `${nowDate()}-${slugify(title)}.md`;
  const filePath = path.join(FLOW_DIR, filename);
  saveFile(filePath, content);

  // Update experience file with back-link
  let expText = fs.readFileSync(srcPath, "utf-8");
  if (expText.includes("workflows:")) {
    expText = expText.replace("- workflows:", `- workflows: ${filename}`);
    saveFile(srcPath, expText);
  }

  return { success: true, filename, type: "workflow" };
}

function toolLinkItems(args: any) {
  const expFile = args.experience_filename ?? "";
  const flowFile = args.workflow_filename ?? null;
  const knowFile = args.knowledge_filename ?? null;

  const expPath = path.join(EXP_DIR, expFile);
  if (!fs.existsSync(expPath)) return { error: `Experience file not found: ${expFile}` };

  let text = fs.readFileSync(expPath, "utf-8");
  if (flowFile && text.includes("workflows:")) {
    text = text.replace("- workflows:", `- workflows: ${flowFile}`);
  }
  if (knowFile && text.includes("knowledge:")) {
    text = text.replace("- knowledge:", `- knowledge: ${knowFile}`);
  }

  saveFile(expPath, text);
  return { success: true, message: "Links updated" };
}

// ---------------------------------------------------------------------------
// Tool registry
// ---------------------------------------------------------------------------

const TOOLS: Tool[] = [
  {
    name: "search_items",
    description:
      "Search across experiences, workflows, and knowledge base by keyword. Returns matching items with title, type, filename, and a text snippet.",
    inputSchema: {
      type: "object",
      properties: {
        keyword: { type: "string", description: "Search keyword" },
        type: {
          type: "string",
          enum: ["all", "experience", "workflow", "knowledge"],
          default: "all",
          description: "Which category to search",
        },
      },
      required: ["keyword"],
    },
  },
  {
    name: "get_item",
    description:
      "Get the full Markdown content of a specific experience, workflow, or knowledge entry by filename.",
    inputSchema: {
      type: "object",
      properties: {
        filename: {
          type: "string",
          description: "Markdown filename (e.g. 20260417-api-timeout.md)",
        },
        type: {
          type: "string",
          enum: ["experience", "workflow", "knowledge"],
          description: "Item category",
        },
      },
      required: ["filename", "type"],
    },
  },
  {
    name: "list_items",
    description:
      "List all items in experiences, workflows, and/or knowledge. Returns filenames and titles.",
    inputSchema: {
      type: "object",
      properties: {
        type: {
          type: "string",
          enum: ["all", "experience", "workflow", "knowledge"],
          default: "all",
          description: "Which category to list",
        },
      },
    },
  },
  {
    name: "capture_experience",
    description: "Create a new experience record in the experiences folder.",
    inputSchema: {
      type: "object",
      properties: {
        title: { type: "string" },
        category: { type: "string", default: "general" },
        tags: { type: "array", items: { type: "string" }, default: [] },
        context: { type: "string" },
        process: { type: "string" },
        result: { type: "string" },
        reflection: { type: "string" },
      },
      required: ["title"],
    },
  },
  {
    name: "add_knowledge",
    description: "Add a new knowledge entry to the knowledge base.",
    inputSchema: {
      type: "object",
      properties: {
        title: { type: "string" },
        category: { type: "string", default: "general" },
        tags: { type: "array", items: { type: "string" }, default: [] },
        concept: { type: "string" },
        detail: { type: "string" },
        examples: { type: "string" },
        references: { type: "string" },
      },
      required: ["title"],
    },
  },
  {
    name: "distill_workflow",
    description:
      "Distill a standardized workflow (SOP) from an existing experience record.",
    inputSchema: {
      type: "object",
      properties: {
        source_experience: {
          type: "string",
          description: "Filename of the source experience markdown",
        },
        title: { type: "string", description: "Title for the new workflow" },
        scenario: { type: "string" },
        prerequisites: { type: "string" },
        steps: {
          type: "string",
          description: "Step descriptions separated by semicolons",
        },
        faq: { type: "string" },
        tags: { type: "array", items: { type: "string" }, default: [] },
      },
      required: ["source_experience", "title"],
    },
  },
  {
    name: "link_items",
    description:
      "Link an experience to a workflow and/or knowledge entry by updating the experience's frontmatter/links section.",
    inputSchema: {
      type: "object",
      properties: {
        experience_filename: { type: "string" },
        workflow_filename: { type: ["string", "null"] as any },
        knowledge_filename: { type: ["string", "null"] as any },
      },
      required: ["experience_filename"],
    },
  },
];

const TOOL_HANDLERS: Record<string, (args: any) => any> = {
  search_items: toolSearchItems,
  get_item: toolGetItem,
  list_items: toolListItems,
  capture_experience: toolCaptureExperience,
  add_knowledge: toolAddKnowledge,
  distill_workflow: toolDistillWorkflow,
  link_items: toolLinkItems,
};

// ---------------------------------------------------------------------------
// Resources
// ---------------------------------------------------------------------------

const RESOURCES = [
  {
    uri: "expforge://experiences/",
    name: "Experiences Directory",
    mimeType: "text/plain",
    description: "All experience markdown files",
  },
  {
    uri: "expforge://workflows/",
    name: "Workflows Directory",
    mimeType: "text/plain",
    description: "All workflow markdown files",
  },
  {
    uri: "expforge://knowledge/",
    name: "Knowledge Directory",
    mimeType: "text/plain",
    description: "All knowledge markdown files",
  },
];

function readResource(uri: string): string | null {
  const prefixMap: Record<string, string> = {
    "expforge://experiences/": EXP_DIR,
    "expforge://workflows/": FLOW_DIR,
    "expforge://knowledge/": KNOW_DIR,
  };
  for (const [prefix, directory] of Object.entries(prefixMap)) {
    if (uri.startsWith(prefix)) {
      const filename = uri.slice(prefix.length);
      if (!filename) {
        // directory listing
        return listMdFiles(directory)
          .map((f) => {
            const text = fs.readFileSync(path.join(directory, f), "utf-8");
            return `${f}: ${extractTitle(text)}`;
          })
          .join("\n");
      }
      const filePath = path.join(directory, filename);
      if (fs.existsSync(filePath)) {
        return fs.readFileSync(filePath, "utf-8");
      }
      return null;
    }
  }
  return null;
}

// ---------------------------------------------------------------------------
// Server bootstrap
// ---------------------------------------------------------------------------

async function main() {
  ensureDir(EXP_DIR);
  ensureDir(FLOW_DIR);
  ensureDir(KNOW_DIR);

  const server = new Server(
    {
      name: "expforge-mcp-server-ts",
      version: "0.1.0",
    },
    {
      capabilities: {
        tools: {},
        resources: {},
      },
    }
  );

  server.setRequestHandler(ListToolsRequestSchema, async () => {
    return { tools: TOOLS };
  });

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    const handler = TOOL_HANDLERS[name];
    if (!handler) {
      throw new Error(`Unknown tool: ${name}`);
    }
    const result = handler(args ?? {});
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result, null, 2),
        },
      ],
    };
  });

  server.setRequestHandler(ListResourcesRequestSchema, async () => {
    return { resources: RESOURCES };
  });

  server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
    const uri = request.params.uri;
    const content = readResource(uri);
    if (content === null) {
      throw new Error(`Resource not found: ${uri}`);
    }
    return {
      contents: [
        {
          uri,
          mimeType: "text/markdown",
          text: content,
        },
      ],
    };
  });

  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("ExpForge MCP Server (TS) started on stdio");
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
