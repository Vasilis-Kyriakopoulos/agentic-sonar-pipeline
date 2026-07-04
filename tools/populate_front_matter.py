from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"
NS = {"w": W_NS}


def w(local: str) -> str:
    return f"{{{W_NS}}}{local}"


def text_of(el: etree._Element) -> str:
    return "".join(el.xpath(".//w:t/text()", namespaces=NS)).strip()


def style_id(p: etree._Element) -> str:
    style = p.find("./w:pPr/w:pStyle", namespaces=NS)
    return style.get(w("val")) if style is not None else ""


def unzip_docx(docx_path: Path, out_dir: Path) -> None:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(docx_path, "r") as zf:
        zf.extractall(out_dir)


def zip_docx(in_dir: Path, out_docx_path: Path) -> None:
    tmp_out = out_docx_path.with_suffix(out_docx_path.suffix + ".tmp")
    if tmp_out.exists():
        tmp_out.unlink()
    with zipfile.ZipFile(tmp_out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(in_dir):
            for file_name in files:
                abs_path = Path(root) / file_name
                rel_path = abs_path.relative_to(in_dir)
                zf.write(abs_path, rel_path.as_posix())
    tmp_out.replace(out_docx_path)


def xml_space(t_el: etree._Element) -> None:
    if t_el.text and (t_el.text.startswith(" ") or t_el.text.endswith(" ")):
        t_el.set(f"{{{XML_NS}}}space", "preserve")


def run_text(text: str, bold: bool = False, size_half_points: int | None = None) -> etree._Element:
    run = etree.Element(w("r"))
    if bold or size_half_points:
        r_pr = etree.SubElement(run, w("rPr"))
        r_fonts = etree.SubElement(r_pr, w("rFonts"))
        r_fonts.set(w("ascii"), "Times New Roman")
        r_fonts.set(w("hAnsi"), "Times New Roman")
        r_fonts.set(w("cs"), "Times New Roman")
        if bold:
            etree.SubElement(r_pr, w("b"))
        if size_half_points:
            sz = etree.SubElement(r_pr, w("sz"))
            sz.set(w("val"), str(size_half_points))
    t = etree.SubElement(run, w("t"))
    t.text = text
    xml_space(t)
    return run


def run_tab() -> etree._Element:
    run = etree.Element(w("r"))
    etree.SubElement(run, w("tab"))
    return run


def title_paragraph(text: str) -> etree._Element:
    p = etree.Element(w("p"))
    p_pr = etree.SubElement(p, w("pPr"))
    spacing = etree.SubElement(p_pr, w("spacing"))
    spacing.set(w("before"), "360")
    spacing.set(w("after"), "180")
    p.append(run_text(text, bold=True, size_half_points=32))
    return p


def page_break_paragraph() -> etree._Element:
    p = etree.Element(w("p"))
    run = etree.SubElement(p, w("r"))
    br = etree.SubElement(run, w("br"))
    br.set(w("type"), "page")
    return p


def add_tabs_and_indent(p_pr: etree._Element, level: int) -> None:
    tabs = etree.SubElement(p_pr, w("tabs"))
    tab = etree.SubElement(tabs, w("tab"))
    tab.set(w("val"), "right")
    tab.set(w("leader"), "dot")
    tab.set(w("pos"), "9360")
    if level > 1:
        ind = etree.SubElement(p_pr, w("ind"))
        ind.set(w("left"), str((level - 1) * 360))


def entry_paragraph(text: str, page: str, style: str, level: int = 1) -> etree._Element:
    p = etree.Element(w("p"))
    p_pr = etree.SubElement(p, w("pPr"))
    p_style = etree.SubElement(p_pr, w("pStyle"))
    p_style.set(w("val"), style)
    add_tabs_and_indent(p_pr, level)
    p.append(run_text(text))
    p.append(run_tab())
    p.append(run_text(page))
    return p


def prepend_field_start(p: etree._Element, instruction: str) -> None:
    p_pr = p.find("w:pPr", namespaces=NS)
    insert_at = 1 if p_pr is not None else 0

    r_begin = etree.Element(w("r"))
    fld_begin = etree.SubElement(r_begin, w("fldChar"))
    fld_begin.set(w("fldCharType"), "begin")
    fld_begin.set(w("dirty"), "true")

    r_instr = etree.Element(w("r"))
    instr = etree.SubElement(r_instr, w("instrText"))
    instr.set(f"{{{XML_NS}}}space", "preserve")
    instr.text = f" {instruction} "

    r_sep = etree.Element(w("r"))
    fld_sep = etree.SubElement(r_sep, w("fldChar"))
    fld_sep.set(w("fldCharType"), "separate")

    p.insert(insert_at, r_sep)
    p.insert(insert_at, r_instr)
    p.insert(insert_at, r_begin)


def append_field_end(p: etree._Element) -> None:
    run = etree.SubElement(p, w("r"))
    fld_end = etree.SubElement(run, w("fldChar"))
    fld_end.set(w("fldCharType"), "end")


def field_result_block(instruction: str, entries: list[dict], style_prefix: str) -> list[etree._Element]:
    if not entries:
        entries = [{"text": "(no entries)", "page": "", "level": 1}]
    nodes = []
    for entry in entries:
        level = int(entry.get("level", 1))
        style = f"{style_prefix}{level}" if style_prefix == "TOC" else style_prefix
        nodes.append(entry_paragraph(entry["text"], str(entry.get("page", "0")), style, level))
    prepend_field_start(nodes[0], instruction)
    append_field_end(nodes[-1])
    return nodes


def heading_entries(body: etree._Element) -> list[dict]:
    entries = []
    counters = [0, 0, 0, 0]
    for p in body.findall("w:p", namespaces=NS):
        sid = style_id(p)
        match = re.match(r"Heading([1-3])$", sid)
        if not match:
            continue
        text = text_of(p)
        if not text:
            continue
        level = int(match.group(1))
        num_pr = p.find("./w:pPr/w:numPr", namespaces=NS)
        if num_pr is not None:
            ilvl_el = num_pr.find("w:ilvl", namespaces=NS)
            ilvl = int(ilvl_el.get(w("val"))) if ilvl_el is not None else level - 1
            counters[ilvl] += 1
            for i in range(ilvl + 1, len(counters)):
                counters[i] = 0
            prefix = ".".join(str(counters[i]) for i in range(ilvl + 1)) + "."
            text = f"{prefix} {text}"
        entries.append({"text": text, "level": level, "page": "0"})
    return entries


def caption_entries(body: etree._Element, label: str) -> list[dict]:
    entries = []
    for p in body.findall("w:p", namespaces=NS):
        if style_id(p) != "Caption":
            continue
        text = text_of(p)
        if text.startswith(label + " "):
            entries.append({"text": text, "level": 1, "page": "0"})
    return entries


def apply_page_numbers(entries: list[dict], pages: list[int]) -> None:
    if not pages:
        return
    if len(entries) != len(pages):
        raise RuntimeError(f"Page count mismatch: {len(entries)} entries vs {len(pages)} pages")
    for entry, page in zip(entries, pages):
        entry["page"] = str(page)


def read_pages(path: Path | None) -> dict[str, list[int]]:
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return {
        "headings": [int(item["page"]) for item in data.get("headings", [])],
        "figures": [int(item["page"]) for item in data.get("figures", [])],
        "tables": [int(item["page"]) for item in data.get("tables", [])],
    }


def replace_front_matter(body: etree._Element, pages: dict[str, list[int]]) -> None:
    headings = heading_entries(body)
    figures = caption_entries(body, "Εικόνα")
    tables = caption_entries(body, "Πίνακας")

    apply_page_numbers(headings, pages.get("headings", []))
    apply_page_numbers(figures, pages.get("figures", []))
    apply_page_numbers(tables, pages.get("tables", []))

    children = list(body)
    start = None
    end = None
    for idx, child in enumerate(children):
        if child.tag == w("p") and text_of(child) == "Πίνακας Περιεχομένων":
            start = idx
        if start is not None and idx > start and child.tag == w("p") and text_of(child) == "Περίληψη":
            end = idx
            break
    if start is None or end is None:
        raise RuntimeError("Could not locate front matter block")

    for child in children[start:end]:
        body.remove(child)

    new_nodes: list[etree._Element] = [
        title_paragraph("Πίνακας Περιεχομένων"),
        *field_result_block('TOC \\o "1-3" \\h \\z \\u', headings, "TOC"),
        page_break_paragraph(),
        title_paragraph("Ευρετήριο Εικόνων"),
        *field_result_block('TOC \\h \\z \\c "Figure"', figures, "TableofFigures"),
        page_break_paragraph(),
        title_paragraph("Ευρετήριο Πινάκων"),
        *field_result_block('TOC \\h \\z \\c "Table"', tables, "TableofFigures"),
        page_break_paragraph(),
    ]
    for offset, node in enumerate(new_nodes):
        body.insert(start + offset, node)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("docx", type=Path)
    ap.add_argument("--pages-json", type=Path, default=None)
    args = ap.parse_args()

    pages = read_pages(args.pages_json)
    with tempfile.TemporaryDirectory(prefix="front_matter_", dir=str(args.docx.parent)) as tmp:
        unzipped = Path(tmp) / "unzipped"
        unzip_docx(args.docx, unzipped)
        doc_xml = unzipped / "word" / "document.xml"
        parser = etree.XMLParser(remove_blank_text=False)
        tree = etree.parse(str(doc_xml), parser)
        root = tree.getroot()
        body = root.find("w:body", namespaces=NS)
        if body is None:
            raise RuntimeError("Document body not found")
        replace_front_matter(body, pages)
        tree.write(str(doc_xml), xml_declaration=True, encoding="UTF-8", standalone="yes")
        zip_docx(unzipped, args.docx)

    print(f"Populated front matter in {args.docx}")


if __name__ == "__main__":
    main()
