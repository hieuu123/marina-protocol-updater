import base64
import os
import html
import requests
from bs4 import BeautifulSoup

# ================= CONFIG =================
WP_URL = "https://blog.mexc.com/wp-json/wp/v2/posts"
WP_USERNAME = os.getenv("WP_USERNAME")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")
POST_ID = 331523  # 🔧 Cập nhật đúng ID bài Marina Protocol
TARGET_H2_TEXT = "Marina Protocol Today Quiz Answer for December 19, 2025"
CHECK_ANSWER = "A) Token rewards for engagement."
# ================ SCRAPE SITE ================
def scrape_quiz_site():
    url = "https://miningcombo.com/marina-protocol"
    print(f"[+] Scraping quiz from {url}")
    r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # Tìm p có chứa 'Question:' và 'Answer:'
    question, answer = None, None
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if text.startswith("Question:"):
            question = text.replace("Question:", "").strip()
        elif text.startswith("Answer:"):
            answer = text.replace("Answer:", "").strip()

    if not question or not answer:
        raise RuntimeError("❌ Không tìm thấy Question hoặc Answer trong trang")

    print("[+] Scraped question and answer")
    print("   Q:", question)
    print("   A:", answer)
    return question, answer


# ================ UPDATE POST ================
def update_post_after_h2(target_h2_text, question, answer):
    if not WP_USERNAME or not WP_APP_PASSWORD:
        raise RuntimeError("⚠️ Thiếu repo secret: WP_USERNAME hoặc WP_APP_PASSWORD")

    token = base64.b64encode(f"{WP_USERNAME}:{WP_APP_PASSWORD}".encode()).decode("utf-8")
    headers = {
        "Authorization": f"Basic {token}",
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    # 1️⃣ Lấy nội dung bài post
    url = f"{WP_URL}/{POST_ID}"
    response = requests.get(url, headers=headers, timeout=15)
    print("🔎 Fetch status:", response.status_code)
    if response.status_code != 200:
        print("❌ Không lấy được post:", response.text[:300])
        return

    post = response.json()
    old_content = post.get("content", {}).get("rendered", "")
    if not old_content:
        print("❌ Không thấy content.rendered")
        return

    print("✍️ Lấy content.rendered, độ dài:", len(old_content))
    soup = BeautifulSoup(old_content, "html.parser")

    # 2️⃣ Tìm H2 đúng
    def normalize(text):
        return (
            html.unescape(text)
            .lower()
            .replace("’", "'")
            .replace("–", "-")
            .replace("—", "-")
            .replace("\xa0", " ")
            .strip()
        )
    h2_tag = None
    for h2 in soup.find_all("h2"):
        h2_norm = normalize(h2.get_text())
        if "marina protocol today quiz answer" in h2_norm:
            h2_tag = h2
            break
    
    if not h2_tag:
        print("❌ Không tìm thấy H2 quiz")
        print("Rendered snippet:", old_content[:4000])
        return

    # 3️⃣ Xóa UL quiz cũ (nếu có)
    removed = 0
    ul = h2_tag.find_next_sibling("ul")
    
    if ul:
        ul.decompose()
        removed += 1
    
    print(f"[+] Removed {removed} quiz <ul>")

    # 4️⃣ Tạo UL mới
    ul_tag = soup.new_tag("ul")
    ul_tag["class"] = "wp-block-list"
    
    li_q = soup.new_tag("li")
    li_q.append(soup.new_tag("strong"))
    li_q.strong.string = f"Question: {question}"
    ul_tag.append(li_q)
    
    li_a = soup.new_tag("li")
    li_a.append(soup.new_tag("strong"))
    li_a.strong.string = f"Correct Answer: {answer}"
    ul_tag.append(li_a)

    # 5️⃣ Chèn <ul> mới ngay sau H2
    h2_tag.insert_after(ul_tag)

    new_content = str(soup)
    print("[+] New content length:", len(new_content))

    # 6️⃣ Update lên WordPress
    payload = {"content": new_content, "status": "publish"}
    update = requests.post(url, headers=headers, json=payload, timeout=15)
    print("🚀 Update status:", update.status_code)
    print("📄 Update response:", update.text[:500])

    if update.status_code == 200:
        print("✅ Post updated & published thành công!")
    else:
        print("❌ Error khi update")


# ================ MAIN =================
if __name__ == "__main__":
    try:
        q, a = scrape_quiz_site()
        if a.strip() != CHECK_ANSWER.strip():
            print("✅ Answer khác CHECK_ANSWER -> Update ngay")
            update_post_after_h2(TARGET_H2_TEXT, q, a)
        else:
            print("⚠️ Answer trùng CHECK_ANSWER -> Không cần update")
    except Exception as e:
        print("❌ Lỗi khi scrape hoặc update:", e)
