"""
Manim API Scraper & RAG
Manim 공식 문서와 GitHub 예제를 크롤링해서 벡터 DB에 저장
"""
import os
import requests
from typing import List, Dict
from openai import OpenAI
import json

# === Step 1: Manim 공식 문서 크롤링 ===

MANIM_DOCS_URLS = [
    "https://docs.manim.community/en/stable/reference/manim.mobject.geometry.polygram.Square.html",
    "https://docs.manim.community/en/stable/reference/manim.mobject.geometry.arc.Circle.html",
    "https://docs.manim.community/en/stable/reference/manim.mobject.text.text_mobject.Text.html",
    "https://docs.manim.community/en/stable/reference/manim.animation.creation.Create.html",
    "https://docs.manim.community/en/stable/reference/manim.animation.fading.FadeIn.html",
    # 필요한 만큼 추가...
]

def scrape_manim_docs() -> List[Dict[str, str]]:
    """Manim 공식 문서에서 API 정보 크롤링"""
    docs = []
    for url in MANIM_DOCS_URLS:
        try:
            response = requests.get(url)
            # 간단히 텍스트만 추출 (실제로는 BeautifulSoup 사용)
            docs.append({
                "source": url,
                "content": response.text[:2000]  # 앞부분만
            })
        except Exception as e:
            print(f"Failed to scrape {url}: {e}")
    return docs


# === Step 2: Manim GitHub 예제 크롤링 ===

MANIM_GITHUB_EXAMPLES = [
    "https://raw.githubusercontent.com/ManimCommunity/manim/main/example_scenes/basic_scenes.py",
    "https://raw.githubusercontent.com/ManimCommunity/manim/main/example_scenes/advanced_scenes.py",
]

def scrape_github_examples() -> List[Dict[str, str]]:
    """GitHub에서 Manim 예제 코드 크롤링"""
    examples = []
    for url in MANIM_GITHUB_EXAMPLES:
        try:
            response = requests.get(url)
            examples.append({
                "source": url,
                "content": response.text
            })
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
    return examples


# === Step 3: 벡터 DB에 저장 (간단 버전: JSON 파일) ===

def build_api_knowledge_base():
    """API 문서 + 예제를 모아서 knowledge base 생성"""
    
    docs = scrape_manim_docs()
    examples = scrape_github_examples()
    
    knowledge_base = {
        "docs": docs,
        "examples": examples
    }
    
    with open("manim_api_knowledge.json", "w", encoding="utf-8") as f:
        json.dump(knowledge_base, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Knowledge base saved: {len(docs)} docs, {len(examples)} examples")


# === Step 4: RAG 검색 (OpenAI Embeddings) ===

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_embedding(text: str) -> List[float]:
    """텍스트를 벡터로 변환"""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


def search_relevant_examples(query: str, top_k: int = 3) -> List[str]:
    """
    쿼리와 관련된 Manim 예제 검색
    (실제로는 벡터 DB 사용, 여기서는 간단히 키워드 매칭)
    """
    
    # Knowledge base 로드
    try:
        with open("manim_api_knowledge.json", "r", encoding="utf-8") as f:
            kb = json.load(f)
    except FileNotFoundError:
        return []
    
    # 간단한 키워드 매칭 (실제로는 cosine similarity 사용)
    results = []
    for example in kb.get("examples", []):
        content = example["content"]
        if any(keyword in content.lower() for keyword in query.lower().split()):
            results.append(content[:1000])  # 앞부분만
    
    return results[:top_k]


# === Step 5: Codegen에 RAG 적용 ===

def augment_prompt_with_rag(base_prompt: str, domain: str) -> str:
    """
    기본 프롬프트에 관련 예제 추가
    """
    
    # 도메인 키워드로 검색
    relevant_examples = search_relevant_examples(domain)
    
    if not relevant_examples:
        return base_prompt
    
    rag_context = "\n\n".join([
        f"<relevant_example_{i}>\n{ex}\n</relevant_example_{i}>"
        for i, ex in enumerate(relevant_examples)
    ])
    
    return f"""
{base_prompt}

Additionally, here are some relevant Manim code examples for reference:

{rag_context}
"""


if __name__ == "__main__":
    # 최초 1회 실행: knowledge base 구축
    build_api_knowledge_base()
