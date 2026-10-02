

import json
import os
import difflib
from datetime import datetime

import nltk
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer


REQUIRED_NLTK_RESOURCES = [
    ("tokenizers/punkt", "punkt"),
    ("tokenizers/punkt_tab", "punkt_tab"),
    ("taggers/averaged_perceptron_tagger", "averaged_perceptron_tagger"),
    ("taggers/averaged_perceptron_tagger_eng", "averaged_perceptron_tagger_eng"),
    ("corpora/wordnet", "wordnet"),
    ("corpora/stopwords", "stopwords"),
]


def ensure_nltk_resources():
    """Download any NLTK corpora/models the chatbot needs but that are not
    already installed on this machine. Only needs internet access once."""
    for resource_path, package_name in REQUIRED_NLTK_RESOURCES:
        try:
            nltk.data.find(resource_path)
        except LookupError:
            print(f"[setup] Downloading required NLTK package: {package_name} ...")
            nltk.download(package_name, quiet=True)


# ---------------------------------------------------------------------------
# 1. LOAD THE PRODUCT -> SHELF DATABASE
# ---------------------------------------------------------------------------

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "product_database.json")


def load_product_database(path=DB_PATH):
    """Load the JSON product database and build a fast lookup dictionary
    that maps every known name/alias (lower-cased) to its product record."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    products = data["products"]

    lookup_table = {}
    for product in products:
        lookup_table[product["name"].lower()] = product
        for alias in product.get("aliases", []):
            lookup_table[alias.lower()] = product

    return products, lookup_table


# ---------------------------------------------------------------------------
# 2. NLP PIPELINE: tokenize -> POS tag -> noun-phrase chunking -> lemmatize
# ---------------------------------------------------------------------------

lemmatizer = WordNetLemmatizer()

GOODS_GRAMMAR = r"""
    GOODS: {<JJ.*>*<NN.*>+}
"""

IGNORE_WORDS = {
    "i", "want", "to", "buy", "get", "need", "please", "also",
    "list", "some", "a", "an", "the", "of", "for", "me", "and",
    "item", "items", "thing", "things", "shelf", "shop", "store",
    "cart", "basket", "bag", "bags",
}


def clean_tokenize(text):
    return word_tokenize(text)


def pos_tag_tokens(tokens):
    return nltk.pos_tag(tokens)


def extract_goods_phrases(tagged_tokens):
    parser = nltk.RegexpParser(GOODS_GRAMMAR)
    tree = parser.parse(tagged_tokens)

    phrases = []
    for subtree in tree.subtrees(filter=lambda t: t.label() == "GOODS"):
        words = [word for word, tag in subtree.leaves()]
        phrases.append(words)
    return phrases


def lemmatize_phrase(words):
    return [lemmatizer.lemmatize(w.lower(), pos="n") for w in words]


def extract_candidate_items(user_text):
    tokens = clean_tokenize(user_text)
    tagged = pos_tag_tokens(tokens)
    phrases = extract_goods_phrases(tagged)

    candidates = []
    for phrase_words in phrases:
        lemmas = lemmatize_phrase(phrase_words)
        lemmas = [w for w in lemmas if w not in IGNORE_WORDS]
        if not lemmas:
            continue
        candidates.append(" ".join(lemmas))

    return candidates


# ---------------------------------------------------------------------------
# 3. MATCH CANDIDATE ITEMS AGAINST THE PRODUCT DATABASE
# ---------------------------------------------------------------------------

FUZZY_MATCH_CUTOFF = 0.78


def match_item(candidate, lookup_table):
    candidate = candidate.lower().strip()

    if candidate in lookup_table:
        return lookup_table[candidate], candidate

    for word in candidate.split():
        if word in lookup_table:
            return lookup_table[word], word

    close = difflib.get_close_matches(
        candidate, lookup_table.keys(), n=1, cutoff=FUZZY_MATCH_CUTOFF
    )
    if close:
        return lookup_table[close[0]], close[0]

    for word in candidate.split():
        close = difflib.get_close_matches(
            word, lookup_table.keys(), n=1, cutoff=FUZZY_MATCH_CUTOFF
        )
        if close:
            return lookup_table[close[0]], close[0]

    return None, candidate


def find_shelf_locations(user_text, lookup_table):
    candidates = extract_candidate_items(user_text)

    found = []
    not_found = []
    seen_products = set()

    for candidate in candidates:
        product, matched_as = match_item(candidate, lookup_table)
        if product:
            key = product["name"]
            if key not in seen_products:
                found.append({
                    "requested_as": candidate,
                    "product": product["name"],
                    "shelf": product["shelf"],
                    "aisle": product["aisle"],
                })
                seen_products.add(key)
        else:
            not_found.append(candidate)

    return found, not_found


# ---------------------------------------------------------------------------
# 4. RECEIPT GENERATION (used by the web app's download buttons)
# ---------------------------------------------------------------------------

RECEIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "receipts")


def save_text_receipt(found, not_found, filename=None):
    os.makedirs(RECEIPTS_DIR, exist_ok=True)
    if filename is None:
        filename = f"shelf_list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    path = os.path.join(RECEIPTS_DIR, filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write("SUPERMARKET ASSISTANT - SHELF LOCATION RECEIPT\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-" * 50 + "\n")
        if found:
            for entry in found:
                f.write(f"{entry['product'].title():<20} -> {entry['shelf']} ({entry['aisle']})\n")
        else:
            f.write("No matching items were found in the store.\n")

        if not_found:
            f.write("\nItems not found:\n")
            for item in not_found:
                f.write(f" - {item}\n")

        f.write("-" * 50 + "\n")
        f.write("Thank you for shopping with us!\n")

    return path


def save_pdf_receipt(found, not_found, filename=None):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        from reportlab.lib.units import cm
    except ImportError:
        return None

    os.makedirs(RECEIPTS_DIR, exist_ok=True)
    if filename is None:
        filename = f"shelf_list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    path = os.path.join(RECEIPTS_DIR, filename)

    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=2 * cm, bottomMargin=2 * cm)
    story = []

    story.append(Paragraph("Supermarket Assistant - Shelf Location Receipt", styles["Title"]))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["Normal"]))
    story.append(Spacer(1, 14))

    if found:
        table_data = [["Item", "Shelf", "Aisle / Category"]]
        for entry in found:
            table_data.append([entry["product"].title(), entry["shelf"], entry["aisle"]])

        table = Table(table_data, colWidths=[6 * cm, 4 * cm, 6 * cm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E7D32")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F8E9")]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(table)
    else:
        story.append(Paragraph("No matching items were found in the store.", styles["Normal"]))

    if not_found:
        story.append(Spacer(1, 16))
        story.append(Paragraph("Items we could not locate:", styles["Heading3"]))
        for item in not_found:
            story.append(Paragraph(f"- {item}", styles["Normal"]))

    story.append(Spacer(1, 20))
    story.append(Paragraph("Thank you for shopping with us!", styles["Italic"]))

    doc.build(story)
    return path
