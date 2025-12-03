# Multi Laptop Price Scraper (Python & Playwright)

This project automatically collects laptop product data from **Hepsiburada, Trendyol, and MediaMarkt** using **Python and Playwright (async)**.  
Data from **10 products per website** is scraped and merged into **a single Excel file**.

---

## Scraped Data Fields

The following information is extracted for each product:

- Website name  
- Brand  
- Price  
- Screen size  
- Storage (GB / TB)  
- Product URL  

All records are saved into **one Excel sheet**.

---

## Technologies Used

- Python 3.10+
- Playwright (Async)
- Pandas
- Regex (re)
- OpenPyXL (for Excel export)

---

## Input File

Before running the script, you must provide an Excel file with product links.

**File name:**  
`multi_laptop_links_step1.xlsx`

**Required columns:**
- `site` → Hepsiburada / Trendyol / Mediamarkt  
- `link` → Product page URL  

The script automatically takes the **first 10 links per site**.

---

## Output File

After successful execution, the following file is created:

**`multi_laptop_details_step2.xlsx`**

**Columns:**
- site  
- brand  
- price  
- screen_size  
- storage  
- url  

All data is stored in **a single worksheet**.

---
YOUTUBE LİNK============ https://www.youtube.com/watch?v=HVfW3E3Sgm0
## Installation

```bash
pip install playwright pandas openpyxl
playwright install
