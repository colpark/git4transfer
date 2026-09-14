"""Audited NCBI E-utilities fallback; not the unavailable scireason MCP."""

from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


def _get(endpoint: str, params: dict) -> dict:
    url = BASE + endpoint + "?" + urlencode(params)
    request = Request(url, headers={"User-Agent": "19C-Stage2-MCP-certification/0.1"})
    with urlopen(request, timeout=15) as response:
        return json.load(response)


def pubmed_search(term: str, max_hits: int = 3) -> dict | None:
    if not term.strip() or len(term) > 300 or not 1 <= max_hits <= 10:
        raise ValueError("term must be 1–300 characters and max_hits 1–10")
    found = _get("esearch.fcgi", {"db": "pubmed", "term": term, "retmax": max_hits,
                                  "retmode": "json"})["esearchresult"]
    ids = found.get("idlist", [])
    if not ids:
        return None
    summary = _get("esummary.fcgi", {"db": "pubmed", "id": ",".join(ids),
                                     "retmode": "json"})["result"]
    articles = [{"pmid": pmid, "title": summary[pmid].get("title"),
                 "publication_date": summary[pmid].get("pubdate")}
                for pmid in ids]
    return {"articles": articles, "count": int(found["count"]),
            "source": "NCBI_Eutilities_ESearch_ESummary",
            "scireason_mcp_reused": False}

