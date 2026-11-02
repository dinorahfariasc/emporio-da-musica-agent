# Spec 010 — Semantic recommendations

## Problem
A customer who describes what they want in subjective terms ("a soft-sounding guitar for a
beginner, up to R$ 700") should get sellable products that fit, not a keyword match. The hybrid
index (full-text + Gemini vectors, DL-010) already understands the product descriptions; the gap
was the tool and the prompt around it.

## Requirements
- FR-1: `find_similar_products(description=...)` accepts an optional `category_id` so a request
  does not return another instrument family.
- FR-2: The product-search prompt tells the model to turn subjective requests into
  `description` + `category_id` + `max_price_brl`, and to cite only facts from tool results.
- FR-3: Results are only sellable products; price and stock stay deterministic (constitution I).
- FR-4: Scenarios cover a beginner/soft request with a budget and a warm-tone nylon request.

## Out of scope
New embeddings, re-ranking models, personalisation, enriching product documents (the CSV
descriptions already carry level and tone).
