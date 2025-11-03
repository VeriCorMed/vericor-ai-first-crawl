# test_wc_api.py
import os
from woocommerce import API
import json

# Pull credentials from environment variables
ck = os.getenv("WC_CK")
cs = os.getenv("WC_CS")
site = os.getenv("WC_SITE")

if not (ck and cs and site):
    print("❌ Missing WC_CK, WC_CS, or WC_SITE environment variables.")
    exit(1)

wcapi = API(
    url=site,
    consumer_key=ck,
    consumer_secret=cs,
    version="wc/v3",
    timeout=30
)

print("Fetching sample products…\n")

# Get first 5 products
products = wcapi.get("products", params={"per_page": 5}).json()

if isinstance(products, dict) and products.get("code"):
    # WooCommerce returned an error object
    print("❌ API error:", products)
    exit(1)

for p in products:
    print("=" * 60)
    print(f"ID: {p.get('id')}")
    print(f"Name: {p.get('name')}")
    print(f"Slug: {p.get('slug')}")
    print(f"SKU: {p.get('sku')}")
    print(f"Price: {p.get('price')}")
    print(f"Regular Price: {p.get('regular_price')}")
    print(f"Sale Price: {p.get('sale_price')}")
    print(f"Weight: {p.get('weight')}")
    print(f"Dimensions: {p.get('dimensions')}")
    print(f"Categories: {[c['name'] for c in p.get('categories', [])]}")
    print(f"Shipping Class: {p.get('shipping_class')}")
    print(f"Stock Status: {p.get('stock_status')}")
    print(f"Attributes: {p.get('attributes')}")
    print(f"Variations: {p.get('variations')}")
    print(f"Permalink: {p.get('permalink')}")
    print("\n--- Raw JSON ---")
    print(json.dumps(p, indent=2))
    print()

print("\n✓ Done")
