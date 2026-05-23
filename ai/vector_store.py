import os
import tiktoken
from openai import OpenAI
from database.models import SessionLocal, CrawlChunk

def get_client():
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def chunk_text(text: str, max_tokens: int = 500) -> list[str]:
    """Băm văn bản thành các chunk nhỏ hơn max_tokens"""
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    chunks = []
    for i in range(0, len(tokens), max_tokens):
        chunk_tokens = tokens[i:i + max_tokens]
        chunks.append(enc.decode(chunk_tokens))
    return chunks

def embed_and_store_chunks(text: str, url: str, crawl_id: int):
    client = get_client()
    chunks = chunk_text(text)
    if not chunks:
        return
        
    # Lấy embedding từ OpenAI
    response = client.embeddings.create(
        input=chunks,
        model="text-embedding-3-small"
    )
    
    db = SessionLocal()
    try:
        for i, chunk_text_content in enumerate(chunks):
            embedding = response.data[i].embedding
            chunk = CrawlChunk(
                web_crawl_id=crawl_id,
                url=url,
                content=chunk_text_content,
                embedding=embedding
            )
            db.add(chunk)
        db.commit()
    except Exception as e:
        print(f"Lỗi khi lưu chunk vào Postgres: {e}")
        db.rollback()
    finally:
        db.close()

def search_similar_chunks(query: str, crawl_id: int, limit: int = 200) -> str:
    """Vì chúng ta chỉ cào 10 trang, dữ liệu hoàn toàn nhét vừa não AI. Ta sẽ gom TẤT CẢ các chunks để AI không bỏ sót sản phẩm nào!"""
    db = SessionLocal()
    try:
        # Lấy thẳng tất cả dữ liệu đã cào (tối đa 200 chunks ~ 100k tokens)
        all_chunks = db.query(CrawlChunk).filter(CrawlChunk.web_crawl_id == crawl_id).limit(limit).all()
            
        context = "\n\n---\n\n".join([f"Nguồn trang {chunk.url}:\n{chunk.content}" for chunk in all_chunks])
        return context
    finally:
        db.close()
