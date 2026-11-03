import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from html.parser import HTMLParser


class ElementSummary:
    def __init__(self, tag: str, attrs: Dict[str, str], text: str = ""):
        self.tag = tag
        self.attrs = attrs
        self.text = text.strip()

    @property
    def selector(self) -> str:
        if "id" in self.attrs:
            return f"#{self.attrs['id']}"
        if "data-testid" in self.attrs:
            return f"[data-testid='{self.attrs['data-testid']}']"
        if "name" in self.attrs:
            return f"{self.tag}[name='{self.attrs['name']}']"
        if "class" in self.attrs:
            classes = self.attrs["class"].split()
            if classes:
                return f".{classes[0]}"
        return self.tag

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selector": self.selector,
            "tag": self.tag,
            "text": self.text[:80] if self.text else "",
            "role": self.attrs.get("role", ""),
        }


class SimpleDOMParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements: List[ElementSummary] = []
        self._stack: List[Dict[str, Any]] = []

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        self._stack.append({
            "tag": tag,
            "attrs": attr_dict,
            "text": []
        })

    def handle_data(self, data):
        cleaned = data.strip()
        if cleaned and self._stack:
            self._stack[-1]["text"].append(cleaned)

    def handle_endtag(self, tag):
        if not self._stack:
            return
        item = self._stack.pop()
        t = item["tag"]
        attrs = item["attrs"]
        text = " ".join(item["text"])

        # Determine if this element is a visual landmark
        has_id_or_test = "id" in attrs or "data-testid" in attrs
        is_semantic = t in ("h1", "h2", "h3", "h4", "button", "nav", "form", "section", "article", "header", "main")
        is_card = any("card" in c or "panel" in c or "metric" in c for c in attrs.get("class", "").split())

        if has_id_or_test or is_semantic or is_card:
            self.elements.append(ElementSummary(t, attrs, text))


def inspect_html(html_content: str) -> Dict[str, Any]:
    """Parses HTML and extracts a structured UI Blueprint of landmarks and selectors."""
    parser = SimpleDOMParser()
    parser.feed(html_content)

    landmarks = []
    seen_selectors = set()

    for el in parser.elements:
        sel = el.selector
        if sel not in seen_selectors and sel not in ("div", "span", "p"):
            seen_selectors.add(sel)
            landmarks.append(el.to_dict())

    return {
        "landmark_count": len(landmarks),
        "landmarks": landmarks[:30],  # Top landmarks for the agent prompt
    }


def inspect_ui_source(file_or_dir: str | Path) -> Dict[str, Any]:
    """Inspects a local HTML file or project directory."""
    path = Path(file_or_dir).resolve()
    if path.is_file():
        text = path.read_text(encoding="utf-8", errors="ignore")
        return {"source": str(path), **inspect_html(text)}

    # If directory, find html or entry files
    html_files = list(path.glob("**/*.html"))
    if html_files:
        first = html_files[0]
        text = first.read_text(encoding="utf-8", errors="ignore")
        return {"source": str(first), **inspect_html(text)}

    return {"source": str(path), "landmark_count": 0, "landmarks": []}
