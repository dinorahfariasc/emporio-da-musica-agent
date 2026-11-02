# Plan — Semantic recommendations

Constitution check: I (facts from tools), VI (no new dependency) pass.

1. `backend/app/tools/products.py`: add `category_id` to `find_similar_products` and pass it to
   `ProductFilters` for the description search (`app/retrieval/hybrid.py::search_products`).
2. `backend/app/agent/prompts.py`: `product_search` block with the category ids and the
   translation rule.
3. Tests: tool test for the category filter; eval scenarios `us4-5`, `us4-6`.
4. Live check (needs Gemini + OpenRouter): `uv run python -m evals --live`, then try 3-4 subjective
   requests in the chat.
