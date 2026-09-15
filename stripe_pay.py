"""Create or reuse a Stripe Payment Link. Key stays in the environment."""
import json
import os
import urllib.parse
import urllib.request

def _key():
    return os.environ.get("STRIPE_SECRET_KEY", "").strip()

def static_link():
    return os.environ.get("STRIPE_PAYMENT_LINK", "").strip()

def create_link(amount_cents, quote_id, work=""):
    """amount_cents=0 -> static dashboard link or None."""
    if amount_cents and _key():
        data = {
            "line_items[0][quantity]": "1",
            "line_items[0][price_data][currency]": "usd",
            "line_items[0][price_data][unit_amount]": str(int(amount_cents)),
            "line_items[0][price_data][product_data][name]": "Xtra Hands quote %s" % quote_id,
            "line_items[0][price_data][product_data][description]": work or "direct quote",
            "metadata[quote_id]": str(quote_id),
        }
        req = urllib.request.Request(
            "https://api.stripe.com/v1/payment_links",
            data=urllib.parse.urlencode(data).encode(),
            method="POST",
        )
        req.add_header("Authorization", "Bearer " + _key())
        with urllib.request.urlopen(req, timeout=20) as r:
            body = json.loads(r.read().decode())
        return body.get("url")
    return static_link() or None
