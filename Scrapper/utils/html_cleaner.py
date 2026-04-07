import re
from bs4 import BeautifulSoup

def clean_html(raw_html: str, max_chars: int = 80000) -> str:
    """
    Surgically cleans Amazon HTML to preserve price, ASIN, and product info.
    Identifies and keeps price-specific containers regardless of location.
    """
    soup = BeautifulSoup(raw_html, "html.parser")

    # Remove only the most egregious noise
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "iframe", "video", "input", "button"]):
        tag.decompose()

    # Identify and PRESERVE crucial segments
    crucial_selectors = [
        # IDs
        "#centerCol", "#ppd", "#main-content", "#dp-container", 
        "#corePriceDisplay_desktop_feature_div", "#corePrice_feature_div",
        "#productDetails_feature_div", "#technicalSpecifications_section_resStyle", 
        "#feature-bullets", "#priceblock_ourprice", "#priceblock_dealprice",
        "#aod-offer-list", "#aod-price-1", # Offer listing IDs
        "#cm_cr-review_list", # Review section
        # Classes
        ".a-section.a-spacing-none.a-spacing-top-mini", ".priceToPay", ".apexPriceToPay",
        ".aod-price", ".review-text-content"
    ]
    
    # 2. Any element that looks like it contains a price or ASIN
    price_elements = soup.find_all(id=re.compile(r"price", re.I)) + \
                     soup.find_all(class_=re.compile(r"price|buying|offer|price-to-pay", re.I))
    asin_elements = soup.find_all(string=re.compile(r"ASIN|B0[A-Z0-9]{8}", re.I))

    # Construct the final text by prioritizing these segments
    context_blocks = []
    seen_texts = set()
    
    def add_block(tag):
        if not tag: return
        t = tag.get_text(separator=" ", strip=True)
        if t and t not in seen_texts:
            context_blocks.append(t)
            seen_texts.add(t)

    # 1. Try selectors
    for selector in crucial_selectors:
        if selector.startswith("#"):
            add_block(soup.find(id=selector[1:]))
        else:
            for item in soup.select(selector):
                add_block(item)
    
    # 2. Known price tags
    for pe in price_elements[:10]:
        add_block(pe)
        
    # 3. ASIN context
    for ae in asin_elements[:5]:
        parent = ae.parent
        if parent:
            add_block(parent.parent if parent.parent else parent)

    if not context_blocks:
        cleaned_text = soup.get_text(separator="\n", strip=True)
    else:
        cleaned_text = "\n\n".join(context_blocks)

    # Clean up whitespace
    cleaned_text = re.sub(r"\s+", " ", cleaned_text)
    cleaned_text = re.sub(r"\n{2,}", "\n\n", cleaned_text)

    if len(cleaned_text) > max_chars:
        cleaned_text = cleaned_text[:max_chars] + "\n\n[...truncated...]"

    return cleaned_text.strip()
