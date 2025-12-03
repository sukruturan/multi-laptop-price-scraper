import asyncio
from playwright.async_api import async_playwright
import pandas as pd

TARGET_PER_SITE = 10
OUTPUT_FILE = "multi_laptop_links_step1.xlsx"


# ---------------- ORTAK – YAVAŞ SCROLL (Trendyol) ----------------
async def slow_scroll_collect(
    page,
    product_selector: str,
    base_url: str,
    site_name: str,
    target_count: int = 100,
    scroll_step: int = 1200,
    wait_ms: int = 5000,
):
    links = []
    seen = set()
    round_no = 0

    while len(links) < target_count:
        round_no += 1

        cards = await page.query_selector_all(product_selector)
        for a in cards:
            href = await a.get_attribute("href")
            if not href:
                continue
            if not href.startswith("http"):
                href = base_url + href
            if href not in seen:
                seen.add(href)
                links.append(href)
                if len(links) >= target_count:
                    break

        print(f"[{site_name}] Scroll {round_no} → şu an {len(links)} link")

        if len(links) >= target_count:
            break

        await page.mouse.wheel(0, scroll_step)
        await page.wait_for_timeout(wait_ms)

    return links[:target_count]


# ---------------- HEPSIBURADA – LİNK TOPLAMA ----------------
async def collect_hepsiburada_links(
    context,
    query: str = "laptop",
    max_products: int = TARGET_PER_SITE,
    max_pages: int = 10,
):
    page = await context.new_page()
    print("[Hepsiburada] Link toplama başlıyor (sayfa sayfa)...")

    base_search = f"https://www.hepsiburada.com/ara?q={query}"
    product_selector = "a[data-test-id='product-card-name'], a[href*='-p-']"
    base_url = "https://www.hepsiburada.com"

    links = []
    seen = set()

    for page_no in range(1, max_pages + 1):
        if len(links) >= max_products:
            break

        url = base_search if page_no == 1 else f"{base_search}&sayfa={page_no}"

        print(f"[Hepsiburada] Sayfa {page_no} açılıyor: {url}")
        await page.goto(url, timeout=60000)
        await page.wait_for_timeout(3000)

        cards = await page.query_selector_all(product_selector)
        print(f"[Hepsiburada] Sayfa {page_no} içinde {len(cards)} kart bulundu.")

        if not cards:
            print("[Hepsiburada] Kart bulunamadı, muhtemelen son sayfa.")
            break

        before = len(links)
        for a in cards:
            href = await a.get_attribute("href")
            if not href:
                continue
            if not href.startswith("http"):
                href = base_url + href
            if "-p-" not in href:
                continue
            if href not in seen:
                seen.add(href)
                links.append(href)
                if len(links) >= max_products:
                    break

        added = len(links) - before
        print(f"[Hepsiburada] Sayfa {page_no} ile {added} yeni link eklendi, toplam {len(links)}.")

        if added == 0:
            print("[Hepsiburada] Yeni link gelmedi, durduruluyor.")
            break

    await page.close()
    print(f"[Hepsiburada] TOPLAM {len(links)} link toplandı (hedef {max_products}).")
    return [{"site": "Hepsiburada", "link": url} for url in links[:max_products]]


# ---------------- TRENDYOL – LİNK TOPLAMA ----------------
async def collect_trendyol_links(context):
    page = await context.new_page()
    print("[Trendyol] Link toplama başlıyor...")

    await page.goto("https://www.trendyol.com/sr?q=laptop", timeout=60000)
    await page.wait_for_timeout(5000)

    selector = "a[href*='-p-']"
    base_url = "https://www.trendyol.com"

    links = await slow_scroll_collect(
        page,
        selector,
        base_url,
        "Trendyol",
        target_count=TARGET_PER_SITE,
        scroll_step=1200,
        wait_ms=5000,
    )

    await page.close()
    print(f"[Trendyol] TOPLAM {len(links)} link toplandı (hedef {TARGET_PER_SITE}).")
    return [{"site": "Trendyol", "link": url} for url in links]


# ---------------- MEDIAMARKT – LİNK TOPLAMA ----------------
async def collect_mediamarkt_links(context):
    page = await context.new_page()
    print("[Mediamarkt] Link toplama başlıyor...")

    await page.goto(
        "https://www.mediamarkt.com.tr/tr/search.html?query=laptop",
        timeout=60000,
    )
    await page.wait_for_timeout(5000)

    product_selector = "a.c-product-tile__main-link, a[href*='/product/']"
    base_url = "https://www.mediamarkt.com.tr"

    links = []
    seen = set()

    async def collect_once():
        nonlocal links, seen
        cards = await page.query_selector_all(product_selector)
        for a in cards:
            href = await a.get_attribute("href")
            if not href:
                continue
            if not href.startswith("http"):
                href = base_url + href
            if href not in seen:
                seen.add(href)
                links.append(href)

    await collect_once()
    print(f"[Mediamarkt] İlk sayfada {len(links)} link var.")

    for i in range(1, 80):
        if len(links) >= TARGET_PER_SITE:
            break

        btn = await page.query_selector("button[data-test='mms-search-srp-loadmore']")
        if not btn:
            print("[Mediamarkt] Load-more butonu yok, durduruluyor.")
            break

        aria_disabled = await btn.get_attribute("aria-disabled")
        if aria_disabled == "true":
            print("[Mediamarkt] Load-more disabled, daha fazla ürün yok.")
            break

        print(f"[Mediamarkt] Load-more tıklanıyor ({i}).")
        try:
            await btn.click()
        except Exception as e:
            print(f"[Mediamarkt] Load-more tıklama hatası: {e}")
            break

        await page.wait_for_timeout(3000)
        await collect_once()
        print(f"[Mediamarkt] Şu ana kadar {len(links)} link toplandı.")

        if len(links) >= TARGET_PER_SITE:
            break

    links = links[:TARGET_PER_SITE]
    await page.close()
    print(f"[Mediamarkt] TOPLAM {len(links)} link toplandı (hedef {TARGET_PER_SITE}).")
    return [{"site": "Mediamarkt", "link": url} for url in links]


# ---------------- MAIN – SADECE LİNK TOPLA & EXCEL ----------------
async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context()

        results = await asyncio.gather(
            collect_hepsiburada_links(context),
            collect_trendyol_links(context),
            collect_mediamarkt_links(context),
        )

        await browser.close()

    all_links = []
    for r in results:
        all_links.extend(r)

    df = pd.DataFrame(all_links)
    print("\n=== Link sayıları ===")
    if not df.empty:
        print(df["site"].value_counts())

    df.to_excel(OUTPUT_FILE, index=False)
    print(f"\n✅ Linkler {OUTPUT_FILE} dosyasına kaydedildi.")


if __name__ == "__main__":
    asyncio.run(main())