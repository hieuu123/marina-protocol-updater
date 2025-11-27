import base64
import os
import requests
from bs4 import BeautifulSoup

# ================= CONFIG =================
WP_URL = "https://blog.mexc.com/wp-json/wp/v2/posts"
WP_USERNAME = os.getenv("WP_USERNAME")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD")
POST_ID = 304394  # 🔧 Marina Protocol
TARGET_H2_TEXT = "Marina Protocol Today Quiz Answer for November 27, 2025"
CHECK_ANSWER = "A) An agent that can execute smart contracts autonomously."

# Find & Replace ngày
OLD_DATE = "November 27"
NEW_DATE = "November 28"


# ================ SCRAPE SITE ================
def scrape_quiz_site():
    url = "https://miningcombo.com/marina-protocol"
    print(f"[+] Scraping quiz from {url}")
    r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

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

    # 1️⃣ Fetch current post
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

    # 2️⃣ Find H2
    h2_tag = soup.find("h2", string=lambda t: t and target_h2_text in t)
    if not h2_tag:
        print("❌ Không tìm thấy H2 phù hợp")
        print("Rendered snippet:", old_content[:400])
        return

    # 3️⃣ Xóa <ul> cũ
    next_tag = h2_tag.find_next_sibling()
    removed = 0
    if next_tag and next_tag.name == "ul":
        next_tag.decompose()
        removed += 1
    print(f"[+] Removed {removed} <ul> cũ sau H2")

    # 4️⃣ Tạo UL mới
    ul_tag = soup.new_tag("ul")
    ul_tag["class"] = "wp-block-list"

    li_q = soup.new_tag("li")
    li_q["style"] = "font-size:17px"
    strong_q = soup.new_tag("strong")
    strong_q.string = f"The question for {NEW_DATE}, 2025:"
    li_q.append(strong_q)
    li_q.append(f" {question}")
    ul_tag.append(li_q)

    li_a = soup.new_tag("li")
    li_a["style"] = "font-size:17px"
    strong_a_label = soup.new_tag("strong")
    strong_a_label.string = "Correct Answer:"
    li_a.append(strong_a_label)
    li_a.append(" ")

    strong_a = soup.new_tag("strong")
    strong_a.string = answer
    li_a.append(strong_a)
    ul_tag.append(li_a)

    # 5️⃣ Insert sau H2
    h2_tag.insert_after(ul_tag)

    # ---- Find & Replace ngày trong CONTENT ----
    new_content = str(soup).replace(OLD_DATE, NEW_DATE)
    print("[+] New content length:", len(new_content))

    # ---- UPDATE CONTENT ----
    payload = {"content": new_content, "status": "publish"}
    update = requests.post(url, headers=headers, json=payload, timeout=15)
    print("🚀 Update content status:", update.status_code)

    if update.status_code != 200:
        print("❌ Error khi update content")
        return

    print("✅ Content updated & published!")

    # ============================
    # UPDATE TITLE (KHÔNG ĐỤNG SEO)
    # ============================

    updated_post = update.json()
    current_title = updated_post.get("title", {}).get("rendered", "")

    new_title = current_title.replace(OLD_DATE, NEW_DATE)

    title_payload = {
        "title": new_title
    }

    title_update = requests.post(url, headers=headers, json=title_payload, timeout=15)
    print("📝 Update Title status:", title_update.status_code)

    if title_update.status_code == 200:
        print("✅ WP Post Title updated!")
    else:
        print("⚠️ Title update failed (content OK)")


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
