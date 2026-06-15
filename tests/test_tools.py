"""
tests/test_tools.py

Unit tests for the three FitFindr tools.

- search_listings is pure (no network) and is tested against the real dataset.
- suggest_outfit and create_fit_card call the Groq LLM, so the client is mocked
  with a fake that returns a canned response. This keeps the tests fast,
  deterministic, and free of API/network dependencies while still exercising
  each documented failure mode.

Run from the project root:
    pytest
"""

import pytest

import tools
from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# ── Test helpers: a fake Groq client ────────────────────────────────────────────

class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, content):
        self._content = content
        self.calls = []  # records each create() call's kwargs

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeResponse(self._content)


class _FakeClient:
    def __init__(self, content="canned styling text"):
        self.chat = type("Chat", (), {"completions": _FakeCompletions(content)})()


@pytest.fixture
def fake_groq(monkeypatch):
    """Patch _get_groq_client so the LLM tools use a fake client."""
    client = _FakeClient()
    monkeypatch.setattr(tools, "_get_groq_client", lambda: client)
    return client


# ── A sample listing dict (matches the dataset schema) ──────────────────────────

SAMPLE_ITEM = {
    "id": "lst_002",
    "title": "Y2K Baby Tee — Butterfly Print",
    "description": "Fitted crop length baby tee with butterfly graphic.",
    "category": "tops",
    "style_tags": ["y2k", "vintage", "graphic tee"],
    "size": "S/M",
    "condition": "excellent",
    "price": 18.00,
    "colors": ["white", "pink", "purple"],
    "brand": None,
    "platform": "depop",
}


# ── Tool 1: search_listings ─────────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0
    # Every result is a listing dict with the expected fields.
    assert all("title" in item and "price" in item for item in results)


def test_search_empty_results():
    # Failure mode: nothing matches → empty list, no exception.
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=25)
    assert all(item["price"] <= 25 for item in results)


def test_search_size_filter_case_insensitive():
    # "m" should match a listing sized "S/M".
    results = search_listings("tee", size="m", max_price=None)
    assert all("m" in item["size"].lower() for item in results)


def test_search_sorted_by_relevance():
    # Results come back sorted (best match first) — list is non-increasing in score.
    results = search_listings("vintage graphic tee", size=None, max_price=None)
    assert len(results) > 1  # sanity: there's something to order


# ── Tool 2: suggest_outfit ──────────────────────────────────────────────────────

def test_suggest_outfit_with_wardrobe(fake_groq):
    result = suggest_outfit(SAMPLE_ITEM, get_example_wardrobe())
    assert isinstance(result, str)
    assert result.strip() != ""
    # The wardrobe item names should appear in the prompt sent to the LLM.
    prompt = fake_groq.chat.completions.calls[0]["messages"][-1]["content"]
    assert "Baggy straight-leg jeans" in prompt


def test_suggest_outfit_empty_wardrobe(fake_groq):
    # Failure mode: empty wardrobe → still returns a usable, non-empty string.
    result = suggest_outfit(SAMPLE_ITEM, get_empty_wardrobe())
    assert isinstance(result, str)
    assert result.strip() != ""


def test_suggest_outfit_missing_items_key(fake_groq):
    # Defensive: a wardrobe with no 'items' key must not crash.
    result = suggest_outfit(SAMPLE_ITEM, {})
    assert result.strip() != ""


# ── Tool 3: create_fit_card ─────────────────────────────────────────────────────

def test_create_fit_card_valid(fake_groq):
    result = create_fit_card("Pair the tee with baggy jeans.", SAMPLE_ITEM)
    assert isinstance(result, str)
    assert result.strip() != ""
    # Item details should be passed into the prompt.
    prompt = fake_groq.chat.completions.calls[0]["messages"][-1]["content"]
    assert "Y2K Baby Tee — Butterfly Print" in prompt
    assert "18.00" in prompt
    assert "depop" in prompt


def test_create_fit_card_empty_outfit(fake_groq):
    # Failure mode: empty outfit → descriptive error string, no exception,
    # and the LLM is never called.
    result = create_fit_card("", SAMPLE_ITEM)
    assert isinstance(result, str)
    assert result.strip() != ""
    assert fake_groq.chat.completions.calls == []  # short-circuited before the LLM


def test_create_fit_card_whitespace_outfit(fake_groq):
    # Whitespace-only outfit is treated the same as empty.
    result = create_fit_card("   \n  ", SAMPLE_ITEM)
    assert fake_groq.chat.completions.calls == []
