from flask import Flask, render_template, request, jsonify

import chatbot_core as core

app = Flask(__name__)

# Download required NLTK resources
core.ensure_nltk_resources()

# Load product database once when the application starts
PRODUCTS, LOOKUP_TABLE = core.load_product_database()


@app.route("/")
def home():
    return render_template(
        "index.html",
        product_count=len(PRODUCTS)
    )


@app.route("/api/search", methods=["POST"])
def api_search():

    data = request.get_json(silent=True) or {}

    user_text = (data.get("text") or "").strip()

    # Check for empty input
    if not user_text:
        return jsonify({
            "error": "Please type at least one item you'd like to find."
        }), 400

    # NLP processing and product search
    found, not_found = core.find_shelf_locations(
        user_text,
        LOOKUP_TABLE
    )

    return jsonify({
        "found": found,
        "not_found": not_found
    })


if __name__ == "__main__":
    app.run(debug=True)