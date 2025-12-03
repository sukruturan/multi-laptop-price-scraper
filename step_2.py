import asyncio
import pandas as pd
import re
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

INPUT_FILE = "multi_laptop_links_step1.xlsx"
OUTPUT_FILE = "multi_laptop_details_step2.xlsx"
PARALLEL_TABS = 10


def clean_price(txt):
    if not txt:
        return None
    txt = re.sub(r"[^\d]", "", txt)
    return int(txt) if txt.isdigit() else None


async def extract_common(page):
    brand = "None"
    price = "None"
    screen = "None"
    storage = "None"

    html = await page.content()

    # BRAND
    m = re.search(r"(asus|lenovo|acer|monster|apple|hp|casper|msi|dell)", html, re.I)
    if m:
        brand = m.group().upper()

    # PRICE (sadece gerçek fiyat aralığı)
    spans = await page.locator("span").all_inner_texts()
    for s in spans:
        val = clean_price(s)
        if val and 3000 < val < 300000:
            price = val
            break

    # SCREEN SIZE
    m = re.search(r"(\d{1,2}[.,]\d)\s*(inç|inch)", html.lower())
    if m:
        screen = m.group(1)

    # STORAGE
    m = re.search(r"(\d+)\s*(gb|tb)", html.lower())
    if m:
        storage = m.group(0).upper()

    return brand, price, screen, storage


async def fetch_and_extract(context, site_name, url, index):
    page = await context.new_page()
    try:
        print(f"[{site_name}] Açılıyor → {index}: {url}")
        await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)

        brand, price, screen, storage = await extract_common(page)

    except TimeoutError:
        print(f"[{site_name}] ZAMAN AŞIMI → {index}: {url}")
        brand, price, screen, storage = "None", "None", "None", "None"
    except Exception as e:
        print(f"[{site_name}] Hata ({index}): {e}")
        brand, price, screen, storage = "None", "None", "None", "None"
    finally:
        await page.close()

    return {
        "site": site_name,
        "brand": brand,
        "price": price,
        "screen_size": screen,
        "storage": storage,
        "url": url
    }


async def process_site(context, site_name, links):
    results = []

    for i in range(0, len(links), PARALLEL_TABS):
        batch = links[i:i + PARALLEL_TABS]

        tasks = [
            fetch_and_extract(context, site_name, url, i + idx + 1)
            for idx, url in enumerate(batch)
        ]

        batch_results = await asyncio.gather(*tasks)
        results.extend(batch_results)

    return results


async def main():
    df = pd.read_excel(INPUT_FILE)

    hb = df[df["site"] == "Hepsiburada"]["link"].head(300).tolist()
    ty = df[df["site"] == "Trendyol"]["link"].head(300).tolist()
    mm = df[df["site"] == "Mediamarkt"]["link"].head(300).tolist()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context()

        all_results = []

        if hb:
            hb_data = await process_site(context, "Hepsiburada", hb)
            all_results.extend(hb_data)

        if ty:
            ty_data = await process_site(context, "Trendyol", ty)
            all_results.extend(ty_data)

        if mm:
            mm_data = await process_site(context, "Mediamarkt", mm)
            all_results.extend(mm_data)

        await browser.close()

    # ---- TÜM SİTELER TEK EXCEL SAYFASINDA ----
    df_all = pd.DataFrame(all_results)
    df_all.to_excel(OUTPUT_FILE, index=False)

    print("\n✅ multi_laptop_details_step2.xlsx oluşturuldu (tek sheet, tüm siteler).")


if __name__ == "__main__":
    asyncio.run(main())