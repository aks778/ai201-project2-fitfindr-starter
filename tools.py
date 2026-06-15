"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    listings = load_listings()

    # Keywords from the description, lowercased and de-duplicated.
    keywords = set(description.lower().split())

    scored: list[tuple[int, dict]] = []
    for listing in listings:
        # Price filter (inclusive).
        if max_price is not None and listing["price"] > max_price:
            continue

        # Size filter — case-insensitive substring so "m" matches "S/M".
        if size is not None and size.lower() not in listing["size"].lower():
            continue

        # Build the text to match keywords against.
        searchable = " ".join([
            listing["title"],
            listing["description"],
            listing["category"],
            " ".join(listing["style_tags"]),
            " ".join(listing["colors"]),
            listing.get("brand") or "",
        ]).lower()

        # Score = how many query keywords appear in the listing text.
        score = sum(1 for kw in keywords if kw in searchable)
        if score == 0:
            continue

        scored.append((score, listing))

    # Highest score first.
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [listing for _, listing in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    client = _get_groq_client()

    item_line = (
        f"{new_item['title']} "
        f"(category: {new_item['category']}, "
        f"colors: {', '.join(new_item['colors'])}, "
        f"style: {', '.join(new_item['style_tags'])})"
    )

    items = wardrobe.get("items", [])
    if not items:
        # Empty wardrobe — fall back to general styling advice.
        prompt = (
            f"A thrift shopper is considering this item:\n{item_line}\n\n"
            "They haven't told us what's in their wardrobe. Give 2-3 short, "
            "practical styling tips: what kinds of pieces pair well with it, "
            "what vibe it suits, and how to dress it up or down."
        )
    else:
        # Non-empty wardrobe — suggest specific combinations using named pieces.
        wardrobe_lines = "\n".join(
            f"- {it['name']} (category: {it['category']}, "
            f"colors: {', '.join(it['colors'])}, "
            f"style: {', '.join(it['style_tags'])})"
            for it in items
        )
        prompt = (
            f"A thrift shopper is considering this new item:\n{item_line}\n\n"
            f"Here is what's already in their wardrobe:\n{wardrobe_lines}\n\n"
            "Suggest 1-2 complete outfits that pair the new item with specific, "
            "named pieces from their wardrobe. Reference the pieces by name and "
            "briefly say why each outfit works."
        )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are a thoughtful personal stylist for secondhand "
                "and vintage fashion. Keep suggestions concise and wearable.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )
    content = response.choices[0].message.content
    return content.strip() if content else ""


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    # Guard: no outfit to caption.
    if not outfit or not outfit.strip():
        return "Can't make a fit card. No outfit suggestion was provided."

    client = _get_groq_client()

    prompt = (
        f"Write a short, shareable OOTD caption for a thrifted find.\n\n"
        f"Item: {new_item['title']}\n"
        f"Price: ${new_item['price']:.2f}\n"
        f"Platform: {new_item['platform']}\n"
        f"Outfit: {outfit}\n\n"
        "Write 2-4 sentences that sound like a real, casual social-media post — "
        "not a product description. Mention the item name, price, and platform "
        "naturally (once each), and capture the outfit's vibe in specific terms."
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You write fun, authentic Instagram/TikTok captions for "
                "thrifted and vintage fashion finds.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=1.0,
    )
    content = response.choices[0].message.content
    return content.strip() if content else "Couldn't generate a fit card caption."
