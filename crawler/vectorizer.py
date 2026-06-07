import chromadb
from chromadb.utils import embedding_functions
import os
import re

def chunk_text_smart(text, chunk_size=800, chunk_overlap=150):
    """
    Smart chunking that:
    1. Tries to keep product/service blocks together
    2. Splits on paragraph/section boundaries first
    3. Falls back to sentence boundaries
    4. Only does character-level splits as last resort
    """
    # First, split on major page/section breaks
    sections = re.split(r'(=== PAGE:.*?===)', text)
    
    chunks = []
    current_chunk = ""
    
    for section in sections:
        if not section.strip():
            continue
        
        # If this is a page header, start a new chunk
        if section.startswith('=== PAGE:'):
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = section + "\n"
            continue

        # Split section into paragraphs (double newline or heading markers)
        paragraphs = re.split(r'\n\n+|(?=\n## )|(?=PRODUCT/SERVICE:)|(?=PRICE:)', section)
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # If adding this paragraph would exceed chunk_size, flush current
            if len(current_chunk) + len(para) > chunk_size and current_chunk.strip():
                chunks.append(current_chunk.strip())
                # Overlap: keep last N chars of previous chunk for context
                overlap_text = current_chunk[-chunk_overlap:] if len(current_chunk) > chunk_overlap else current_chunk
                current_chunk = overlap_text + "\n" + para
            else:
                current_chunk += "\n" + para
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    # Safety: break up any chunks that are still too large
    final_chunks = []
    for chunk in chunks:
        if len(chunk) <= chunk_size * 1.5:
            final_chunks.append(chunk)
        else:
            # Sentence-level split
            sentences = re.split(r'(?<=[.!?])\s+', chunk)
            curr = ""
            for sent in sentences:
                if len(curr) + len(sent) > chunk_size and curr:
                    final_chunks.append(curr.strip())
                    curr = sent
                else:
                    curr += " " + sent
            if curr.strip():
                final_chunks.append(curr.strip())
    
    return [c for c in final_chunks if len(c) > 20]


def extract_product_catalog(text):
    """
    Attempt to extract a structured product catalog from scraped text.
    Returns a list of product snippet strings to be vectorized separately
    with higher priority (added multiple times for stronger retrieval signal).
    """
    product_chunks = []
    
    # Pattern: PRODUCT/SERVICE: ... lines
    product_blocks = re.findall(r'PRODUCT/SERVICE:\s*(.+?)(?=\nPRODUCT/SERVICE:|=== PAGE:|$)', text, re.DOTALL)
    for block in product_blocks:
        block = block.strip()
        if len(block) > 10:
            product_chunks.append(f"PRODUCT CATALOG ENTRY:\n{block}")
    
    # Pattern: heading followed by price-like text
    price_patterns = re.findall(
        r'##\s*(.+?)\n(.*?(?:tk|taka|bdt|৳|\$|price|cost|rate)[^\n]*)',
        text, re.IGNORECASE | re.DOTALL
    )
    for name, details in price_patterns:
        entry = f"PRODUCT: {name.strip()}\nDETAILS: {details.strip()[:300]}"
        product_chunks.append(entry)
    
    return product_chunks


def vectorize_content(content_items, collection_name="site_content"):
    """
    content_items: List of dicts [{"text": str, "source_type": "website"|"facebook"}]
    
    Improvements:
    - Smart paragraph-aware chunking
    - Product catalog entries are added with triple weight for better retrieval
    - Larger chunk retrieval window
    """
    db_path = os.path.join(os.getcwd(), "chroma_db")
    client = chromadb.PersistentClient(path=db_path)
    
    sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )

    # Reset collection for clean slate
    try:
        client.delete_collection(name=collection_name)
    except:
        pass

    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=sentence_transformer_ef
    )

    all_chunks = []
    all_metadatas = []
    all_ids = []

    for item in content_items:
        text = item["text"]
        source_type = item["source_type"]
        
        # Regular smart chunks
        chunks = chunk_text_smart(text)
        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_metadatas.append({"source": source_type, "type": "content", "index": i})
            all_ids.append(f"{source_type}_content_{i}_{os.urandom(4).hex()}")
        
        # Product catalog entries — add with 3x weight for better retrieval
        if source_type == "website":
            product_chunks = extract_product_catalog(text)
            for i, p_chunk in enumerate(product_chunks):
                # Add 3 copies with unique IDs — this boosts retrieval score for product queries
                for copy in range(3):
                    all_chunks.append(p_chunk)
                    all_metadatas.append({"source": "product_catalog", "type": "product", "index": i, "copy": copy})
                    all_ids.append(f"product_{i}_copy{copy}_{os.urandom(4).hex()}")

    if not all_chunks:
        print("No content to vectorize.")
        return

    # Add in batches to avoid memory issues
    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        batch_docs = all_chunks[i:i+batch_size]
        batch_meta = all_metadatas[i:i+batch_size]
        batch_ids = all_ids[i:i+batch_size]
        collection.add(
            documents=batch_docs,
            metadatas=batch_meta,
            ids=batch_ids
        )

    print(f"Vectorized {len(all_chunks)} chunks ({len([m for m in all_metadatas if m.get('type')=='product'])} product entries) into '{collection_name}'.")


if __name__ == "__main__":
    test_content = [
        {"text": "Hello world from website\n\nPRODUCT/SERVICE: Nike Air Max 270 | Price: 4,500 Taka\n\nPRODUCT/SERVICE: Adidas Ultraboost | Price: 6,000 Taka", "source_type": "website"},
        {"text": "Latest post from FB", "source_type": "facebook"}
    ]
    vectorize_content(test_content, collection_name="test_collection")
