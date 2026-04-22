import feedparser
import json
import os
import urllib.request
import urllib.error
from datetime import datetime

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

RSS_FEEDS = [
    {"url": "https://www.thedailystar.net/rss.xml", "source": "The Daily Star", "category": "bangladesh"},
    {"url": "https://bdnews24.com/feed", "source": "bdnews24", "category": "bangladesh"},
    {"url": "https://feeds.bbci.co.uk/bengali/rss.xml", "source": "BBC Bangla", "category": "world"},
    {"url": "https://www.thedailystar.net/diaspora/rss.xml", "source": "The Daily Star", "category": "diaspora"},
]

CATEGORY_KEYWORDS = {
    "diaspora": ["diaspora", "expat", "abroad", "immigrant", "migrant", "প্রবাসী", "sweden", "uk", "usa", "canada", "europe"],
    "migration": ["visa", "immigration", "migration", "asylum", "refugee", "permit", "ভিসা", "EU", "schengen"],
    "politics": ["politics", "election", "government", "minister", "parliament", "রাজনীতি", "নির্বাচন"],
    "economy": ["economy", "gdp", "remittance", "trade", "business", "অর্থনীতি", "রেমিট্যান্স"],
    "crime": ["crime", "court", "arrest", "murder", "corruption", "অপরাধ", "দুর্নীতি"],
    "sports": ["cricket", "football", "sports", "ক্রিকেট", "খেলা", "tigers"],
    "world": ["world", "international", "global", "বিশ্ব"],
}

def detect_category(title, summary):
    text = (title + " " + summary).lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text:
                return cat
    return "bangladesh"

def rewrite_with_gemini(title, summary, source):
    import json as json_mod
    
    prompt = f"""তুমি একজন বাংলা সংবাদ সম্পাদক। নিচের সংবাদটি পড়ো এবং বাংলায় পুনর্লিখন করো।

মূল শিরোনাম: {title}
মূল সংবাদ: {summary}
সূত্র: {source}

নিয়ম:
1. সম্পূর্ণ নিজের ভাষায় লিখবে
2. সহজ ও প্রাঞ্জল বাংলায় লিখবে
3. তথ্য সঠিক রাখবে

এই JSON format এ দাও, অন্য কিছু না:
{{
  "title": "বাংলা শিরোনাম",
  "summary": "২-৩ লাইনের বাংলা সারসংক্ষেপ",
  "body": "৩-৪ প্যারার বিস্তারিত বাংলা সংবাদ"
}}"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    data = json_mod.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1000}
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    response = urllib.request.urlopen(req, timeout=30)
    result = json_mod.loads(response.read().decode("utf-8"))
    
    text = result["candidates"][0]["content"]["parts"][0]["text"]
    text = text.replace("```json", "").replace("```", "").strip()
    return json_mod.loads(text)

def main():
    existing_news = []
    if os.path.exists("news.json"):
        with open("news.json", "r", encoding="utf-8") as f:
            existing_news = json.load(f)
    
    existing_titles = {n.get("original_title", "") for n in existing_news}
    new_articles = []
    
    for feed_info in RSS_FEEDS:
        try:
            print(f"Fetching: {feed_info['source']}")
            feed = feedparser.parse(feed_info["url"])
            
            for entry in feed.entries[:3]:
                title = entry.get("title", "")
                summary = entry.get("summary", entry.get("description", ""))[:500]
                link = entry.get("link", "")
                
                if title in existing_titles:
                    print(f"Skipping: {title[:50]}")
                    continue
                
                print(f"Rewriting: {title[:50]}")
                
                try:
                    rewritten = rewrite_with_gemini(title, summary, feed_info["source"])
                    category = detect_category(title, summary)
                    
                    article = {
                        "id": f"news_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(new_articles)}",
                        "title": rewritten["title"],
                        "summary": rewritten["summary"],
                        "body": rewritten["body"],
                        "category": category,
                        "source": feed_info["source"],
                        "source_url": link,
                        "original_title": title,
                        "published_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "time_ago": "এইমাত্র"
                    }
                    
                    new_articles.append(article)
                    print(f"Done: {rewritten['title'][:50]}")
                    
                except Exception as e:
                    print(f"Error: {e}")
                    continue
                    
        except Exception as e:
            print(f"Feed error {feed_info['source']}: {e}")
            continue
    
    all_news = new_articles + existing_news
    all_news = all_news[:50]
    
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(all_news, f, ensure_ascii=False, indent=2)
    
    print(f"\nNew: {len(new_articles)} articles")
    print(f"Total: {len(all_news)}")

if __name__ == "__main__":
    main()