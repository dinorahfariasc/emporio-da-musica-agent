"""Generates eda.ipynb from code/markdown cell sources defined below.

Run with `uv run python build_notebook.py` then execute with nbconvert.
This script is a build tool, not part of the committed analysis itself.
"""

import nbformat as nbf

nb = nbf.v4.new_notebook()
cells = []


def md(text):
    cells.append(nbf.v4.new_markdown_cell(text))


def code(text):
    cells.append(nbf.v4.new_code_cell(text))


md("""# Empório da Música — Exploratory Data Analysis

Read-only EDA over `challenge/data/`: products, categories, orders, order_items, customers,
promotions. This complements `docs/data-quality-report.md` (the authoritative, ETL-generated
anomaly list, DL-002) with distributions and visual evidence; it does not replace it.
""")

code("""\
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

DATA = Path("../challenge/data")
pd.set_option("display.max_columns", None)
plt.rcParams["figure.figsize"] = (8, 4)

products = pd.read_csv(DATA / "products.csv")
categories = pd.read_csv(DATA / "categories.csv")
orders = pd.read_csv(DATA / "orders.csv")
order_items = pd.read_csv(DATA / "order_items.csv")
customers = pd.read_csv(DATA / "customers.csv")
promotions = pd.read_csv(DATA / "promotions.csv")

tables = {
    "products": products,
    "categories": categories,
    "orders": orders,
    "order_items": order_items,
    "customers": customers,
    "promotions": promotions,
}
for name, df in tables.items():
    print(f"{name}: {df.shape[0]} rows x {df.shape[1]} cols")
""")

md("## 1. Schema overview")
code("""\
for name, df in tables.items():
    print(f"--- {name} ---")
    print(df.dtypes)
    print()
""")

md("""## 2. Products

Price, stock and status distributions, and the category mix.
""")
code("""\
products[["price_brl", "stock_quantity"]].describe()
""")
code("""\
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
products["price_brl"].plot.hist(bins=15, ax=axes[0], title="Price distribution (BRL)")
products["stock_quantity"].plot.hist(bins=15, ax=axes[1], title="Stock quantity distribution")
plt.tight_layout()
plt.show()
""")
code("""\
products["status"].value_counts()
""")
code("""\
products["status"].value_counts().plot.bar(title="Products by status")
plt.tight_layout()
plt.show()
""")
code("""\
# out_of_stock_active anomaly (data-quality-report.md)
products[(products["status"] == "active") & (products["stock_quantity"] == 0)][
    ["product_id", "name", "status", "stock_quantity"]
]
""")
code("""\
cat_counts = products.merge(categories, on="category_id", how="left")["name_y"].value_counts()
cat_counts.plot.barh(title="Products per category")
plt.tight_layout()
plt.show()
""")
code("""\
# empty_category anomaly: categories with zero products
cat_with_products = products["category_id"].unique()
categories[~categories["category_id"].isin(cat_with_products)]
""")

md("""## 3. Orders & order items

Order value, status, payment method, and a check of stored totals against the sum of
current item prices (the `order_total_mismatch` anomaly is about *historical* prices at
purchase time, so a mismatch here is expected and not itself a new finding — see
`docs/data-quality-report.md`).
""")
code("""\
orders["status"].value_counts()
""")
code("""\
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
orders["status"].value_counts().plot.bar(ax=axes[0], title="Orders by status")
orders["payment_method"].value_counts().plot.bar(ax=axes[1], title="Orders by payment method")
plt.tight_layout()
plt.show()
""")
code("""\
orders["total_brl"].plot.hist(bins=10, title="Order total distribution (BRL)")
plt.tight_layout()
plt.show()
""")
code("""\
items_with_price = order_items.merge(
    products[["product_id", "price_brl"]], on="product_id", how="left"
)
items_with_price["line_total"] = items_with_price["quantity"] * items_with_price["price_brl"]
order_sums = items_with_price.groupby("order_id")["line_total"].sum().rename("items_sum_current_price")
compare = orders.merge(order_sums, on="order_id", how="left")
compare["diff_current_price"] = compare["total_brl"] - compare["items_sum_current_price"]
compare[compare["diff_current_price"].abs() > 0][
    ["order_id", "total_brl", "items_sum_current_price", "diff_current_price"]
]
""")
code("""\
# missing_purchase_channel: orders lack a channel column entirely (§4.1 needs it for 7-day withdrawal)
"channel" in orders.columns
""")

md("## 4. Customers")
code("""\
customers["city"].value_counts().plot.bar(title="Customers by city")
plt.tight_layout()
plt.show()
""")
code("""\
# shared_email anomaly
dupes = customers[customers.duplicated("email", keep=False)].sort_values("email")
dupes
""")

md("""## 5. Promotions

Active vs. duplicate promotions per product (only `is_active` promotions are real discounts;
duplicates on the same product are a known anomaly, largest discount wins per DL-002).
""")
code("""\
promotions["is_active"].value_counts()
""")
code("""\
dup_promo_products = promotions[promotions["is_active"] == 1].groupby("product_id").size()
dup_promo_products[dup_promo_products > 1]
""")
code("""\
active_promos = promotions[promotions["is_active"] == 1].merge(
    products[["product_id", "name", "price_brl"]], on="product_id", how="left"
)
active_promos[["product_id", "name", "price_brl", "discount_percent", "description"]]
""")

md("""## 6. Cross-cutting summary

Findings surfaced above, mapped to the authoritative anomaly table in
`docs/data-quality-report.md` (DL-002):

| Finding here | `data-quality-report.md` row |
|---|---|
| Section 2: active products with 0 stock | `out_of_stock_active` |
| Section 2: discontinued / coming_soon counts | `discontinued`, `coming_soon` |
| Section 2: categories with no products | `empty_category` |
| Section 3: no `channel` column on orders | `missing_purchase_channel` |
| Section 3: stored total vs. current-price item sum | related to `order_total_mismatch` (that
  anomaly compares against *historical* item prices, not current ones; the diff shown here is
  expected for any product whose price changed since the order) |
| Section 4: duplicate customer emails | `shared_email` |
| Section 5: >1 active promotion per product | `duplicate_promotions` |
| Section 5: active promotions list | `active_promotions` |

No new anomaly beyond those already catalogued was found in this pass; this notebook adds
distributions and visual confirmation for the report's existing findings.
""")

nb["cells"] = cells
with open("eda.ipynb", "w") as f:
    nbf.write(nb, f)
print("wrote eda.ipynb")
