import feedparser
import json
import os
import requests
import ssl
import time
from datetime import datetime

# Load .env file
if os.path.exists('.env'):
    with open('.env') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ[key.strip()] = val.strip().strip('"').strip("'")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

RSS_FEEDS = [
    {"url": "https://news.google.com/rss/search?q=bangladesh+diaspora&hl=en&gl=BD&ceid=BD:en", "source": "Google News", "category": "diaspora"},
    {"url": "https://news.google.com/rss/search?q=bangladesh+visa+immigration+europe&hl=en&gl=BD&ceid=BD:en", "source": "Google News", "category": "migration"},
    {"url": "https://news.google.com/rss/search?q=bangladesh+politics+election&hl=en&gl=BD&ceid=BD:en", "source": "Google News", "category": "politics"},
    {"url": "https://news.google.com/rss/search?q=bangladesh+economy+remittance&hl=en&gl=BD&ceid=BD:en", "source": "Google News", "category": "economy"},
    {"url": "https://news.google.com/rss/search?q=bangladesh+cricket+sports&hl=en&gl=BD&ceid=BD:en", "source": "Google News", "category": "sports"},
    {"url": "https://news.google.com/rss/search?q=bangladeshi+expat+uk+usa+sweden+canada&hl=en&gl=BD&ceid=BD:en", "source": "Google News", "category": "diaspora"},
]

def get_feed(url):
    import urllib.request
    import urllib.error
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))
    response = opener.open(req, timeout=15)
    return feedparser.parse(response.read())

def rewrite_with_gemini(title, summary, source):
    prompt = f"""তুমি একজন বাংলা সংবাদ সম্পাদক। নিচের সংবাদটি বাংলায় সারসংক্ষেপ করো।

শিরোনাম: {title}
সংবাদ: {summary[:400]}
সূত্র: {source}

গুরুত্বপূর্ণ: মূল সংবাদ copy করবে না, নিজের ভাষায় লিখবে।

শুধু এই JSON দাও:
{{
  "title": "বাংলা শিরোনাম",
  "summary": "২-৩ লাইনের সারসংক্ষেপ",
  "body": "৩ প্যারার বিস্তারিত সংবাদ"
}}"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 800}
    }

    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    result = response.json()

    text = result["candidates"][0]["content"]["parts"][0]["text"]
    text = text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)

def main():
    print(f"API Key: {'SET' if GEMINI_API_KEY else 'NOT SET'}")

    existing_news = []
    if os.path.exists("news.json"):
        with open("news.json", "r", encoding="utf-8") as f:
            existing_news = json.load(f)

    existing_titles = {n.get("original_title", "") for n in existing_news}
    new_articles = []

    for feed_info in RSS_FEEDS:
        try:
            print(f"\nFetching: {feed_info['category']}")
            feed = get_feed(feed_info["url"])
            print(f"Found: {len(feed.entries)} entries")

            for entry in feed.entries[:2]:
                title = entry.get("title", "")
                summary = entry.get("summary", entry.get("description", ""))[:400]
                link = entry.get("link", "")
                source = entry.get("source", {}).get("title", feed_info["source"])

                if title in existing_titles:
                    print(f"Skip: {title[:40]}")
                    continue

                print(f"Rewriting: {title[:50]}")

                try:
                    rewritten = rewrite_with_gemini(title, summary, source)

                    article = {
                        "id": f"news_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(new_articles)}",
                        "title": rewritten["title"],
                        "summary": rewritten["summary"],
                        "body": rewritten["body"],
                        "category": feed_info["category"],
                        "source": source,
                        "source_url": link,
                        "original_title": title,
                        "published_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "time_ago": "এইমাত্র"
                    }

                    new_articles.append(article)
                    print(f"Done: {rewritten['title'][:50]}")
                    time.sleep(5)

                except Exception as e:
                    print(f"Error: {e}")
                    time.sleep(6)
                    continue

        except Exception as e:
            print(f"Feed error: {e}")
            continue

    all_news = new_articles + existing_news
    all_news = all_news[:50]

    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(all_news, f, ensure_ascii=False, indent=2)

    print(f"\nNew: {len(new_articles)} articles")
    print(f"Total: {len(all_news)}")

if __name__ == "__main__":
    main()