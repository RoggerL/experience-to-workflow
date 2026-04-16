#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ExpForge - 将经验内化为工作流和知识库
"""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
EXP_DIR = BASE_DIR / "experiences"
FLOW_DIR = BASE_DIR / "workflows"
KNOW_DIR = BASE_DIR / "knowledge"
TMPL_DIR = BASE_DIR / "templates"


def slugify(text: str) -> str:
    return re.sub(r"[^\w\s-]", "", text).strip().replace(" ", "-")


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def now_date() -> str:
    return datetime.now().strftime("%Y%m%d")


def read_template(name: str) -> str:
    return (TMPL_DIR / f"{name}.md").read_text(encoding="utf-8")


def render_template(name: str, ctx: dict) -> str:
    tmpl = read_template(name)
    for k, v in ctx.items():
        tmpl = tmpl.replace(f"{{{{{k}}}}}", str(v))
    return tmpl


def prompt(msg: str, default: str = "") -> str:
    if default:
        val = input(f"{msg} [{default}]: ").strip()
        return val if val else default
    return input(f"{msg}: ").strip()


def save_file(path: Path, content: str):
    path.write_text(content, encoding="utf-8")
    print(f"[已保存] {path}")


def cmd_capture(args):
    title = args.title or prompt("经验标题")
    if not title:
        print("标题不能为空")
        return
    category = args.category or prompt("分类", "general")
    tags = args.tags or prompt("标签（逗号分隔）", "")
    print("\n请填写以下内容（多行输入，空行结束）：")
    
    def multi_input(label):
        print(f"\n--- {label} ---")
        lines = []
        while True:
            try:
                line = input()
            except EOFError:
                break
            if line == "" and lines and lines[-1] == "":
                lines.pop()
                break
            lines.append(line)
        return "\n".join(lines)

    context = multi_input("背景")
    process = multi_input("过程")
    result = multi_input("结果")
    reflection = multi_input("反思")

    ctx = {
        "title": title,
        "date": now_str(),
        "tags": f"[{', '.join(t.strip() for t in tags.split(',') if t.strip())}]",
        "category": category,
        "context": context or "待补充",
        "process": process or "待补充",
        "result": result or "待补充",
        "reflection": reflection or "待补充",
    }
    content = render_template("experience", ctx)
    filename = f"{now_date()}-{slugify(title)}.md"
    save_file(EXP_DIR / filename, content)


def cmd_distill(args):
    src = Path(args.source)
    if not src.is_absolute():
        src = EXP_DIR / src
    if not src.exists():
        print(f"文件不存在: {src}")
        return

    text = src.read_text(encoding="utf-8")
    # 提取标题
    m = re.search(r'^title:\s*"([^"]+)"', text, re.M)
    src_title = m.group(1) if m else src.stem

    print(f"从经验 [{src_title}] 提炼工作流...")
    title = prompt("工作流标题", f"{src_title} 工作流")
    scenario = prompt("适用场景")
    prerequisites = prompt("前置条件")
    steps = prompt("关键步骤（分号分隔）")
    faq = prompt("常见问题")
    tags = prompt("标签")

    step_lines = "\n".join(f"1. {s.strip()}" for s in steps.split(";") if s.strip()) or "1. "

    ctx = {
        "title": title,
        "date": now_str(),
        "tags": f"[{', '.join(t.strip() for t in tags.split(',') if t.strip())}]",
        "source": str(src.name),
        "scenario": scenario or "待补充",
        "prerequisites": prerequisites or "待补充",
        "steps": step_lines,
        "faq": faq or "待补充",
    }
    content = render_template("workflow", ctx)
    filename = f"{now_date()}-{slugify(title)}.md"
    save_file(FLOW_DIR / filename, content)

    # 更新经验文件中的关联
    if "workflows:" in text:
        link_line = f"- workflows: {filename}"
        text = text.replace("- workflows:", link_line, 1)
        save_file(src, text)


def cmd_know(args):
    title = args.title or prompt("知识条目标题")
    if not title:
        print("标题不能为空")
        return
    category = args.category or prompt("分类", "general")
    tags = args.tags or prompt("标签")
    concept = prompt("核心概念")
    detail = prompt("详细说明")
    examples = prompt("应用示例")
    references = prompt("参考资料")

    ctx = {
        "title": title,
        "date": now_str(),
        "tags": f"[{', '.join(t.strip() for t in tags.split(',') if t.strip())}]",
        "category": category,
        "concept": concept or "待补充",
        "detail": detail or "待补充",
        "examples": examples or "待补充",
        "references": references or "待补充",
    }
    content = render_template("knowledge", ctx)
    filename = f"{now_date()}-{slugify(title)}.md"
    save_file(KNOW_DIR / filename, content)


def cmd_search(args):
    keyword = args.keyword.lower()
    results = []
    for d in [EXP_DIR, FLOW_DIR, KNOW_DIR]:
        for f in d.glob("*.md"):
            text = f.read_text(encoding="utf-8").lower()
            if keyword in text:
                # 提取标题
                m = re.search(r'^title:\s*"([^"]+)"', text, re.M)
                title = m.group(1) if m else f.stem
                results.append((d.name, f.name, title))
    if not results:
        print(f"未找到包含 '{args.keyword}' 的内容")
        return
    print(f"\n找到 {len(results)} 条结果：\n")
    for loc, fname, title in results:
        print(f"  [{loc}] {title} ({fname})")


def cmd_list(args):
    dirs = {
        "experiences": EXP_DIR,
        "workflows": FLOW_DIR,
        "knowledge": KNOW_DIR,
    }
    for name, d in dirs.items():
        files = sorted(d.glob("*.md"), key=lambda x: x.name)
        print(f"\n[{name}] ({len(files)} files)")
        for f in files:
            text = f.read_text(encoding="utf-8")
            m = re.search(r'^title:\s*"([^"]+)"', text, re.M)
            title = m.group(1) if m else f.stem
            print(f"   - {title}")


def cmd_stats(args):
    def count_and_tag(d: Path):
        files = list(d.glob("*.md"))
        tags = set()
        for f in files:
            text = f.read_text(encoding="utf-8")
            m = re.search(r'^tags:\s*(\[.*\])', text, re.M)
            if m:
                for t in m.group(1).strip("[]").split(","):
                    t = t.strip().strip('"')
                    if t:
                        tags.add(t)
        return len(files), tags

    e_count, e_tags = count_and_tag(EXP_DIR)
    w_count, w_tags = count_and_tag(FLOW_DIR)
    k_count, k_tags = count_and_tag(KNOW_DIR)

    print("\n=== ExpForge 统计 ===")
    print(f"经验记录: {e_count}")
    print(f"工作流  : {w_count}")
    print(f"知识条目: {k_count}")
    print(f"总标签  : {len(e_tags | w_tags | k_tags)}")
    print(f"标签列表: {', '.join(sorted(e_tags | w_tags | k_tags)) or '无'}")


def cmd_link(args):
    print("\n关联管理: 输入文件名进行关联")
    exp_file = prompt("经验文件（experiences/ 下的文件名，不含路径）")
    exp_path = EXP_DIR / exp_file
    if not exp_path.exists():
        print("经验文件不存在")
        return
    
    flow_file = prompt("工作流文件（workflows/ 下的文件名，回车跳过）")
    know_file = prompt("知识文件（knowledge/ 下的文件名，回车跳过）")
    
    text = exp_path.read_text(encoding="utf-8")
    if flow_file and "workflows:" in text:
        text = text.replace("- workflows:", f"- workflows: {flow_file}", 1)
    if know_file and "knowledge:" in text:
        text = text.replace("- knowledge:", f"- knowledge: {know_file}", 1)
    save_file(exp_path, text)
    print("关联已更新")


def main():
    parser = argparse.ArgumentParser(description="ExpForge - 经验内化系统")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_cap = sub.add_parser("capture", help="记录一条经验")
    p_cap.add_argument("--title", "-t", help="标题")
    p_cap.add_argument("--category", "-c", help="分类")
    p_cap.add_argument("--tags", help="标签，逗号分隔")

    p_dis = sub.add_parser("distill", help="从经验提炼工作流")
    p_dis.add_argument("source", help="经验文件路径或文件名")

    p_know = sub.add_parser("know", help="添加知识库条目")
    p_know.add_argument("--title", "-t", help="标题")
    p_know.add_argument("--category", "-c", help="分类")
    p_know.add_argument("--tags", help="标签")

    p_search = sub.add_parser("search", help="搜索")
    p_search.add_argument("keyword", help="关键词")

    sub.add_parser("list", help="列出所有内容")
    sub.add_parser("stats", help="统计信息")

    p_link = sub.add_parser("link", help="建立经验与工作流/知识的关联")

    args = parser.parse_args()

    for d in [EXP_DIR, FLOW_DIR, KNOW_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    globals()[f"cmd_{args.cmd}"](args)


if __name__ == "__main__":
    main()
