from pyvirtualdisplay import Display
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import pandas as pd

def get_chrome_options():
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,800")
    prefs = {"profile.default_content_setting_values": {"images": 2, "stylesheets": 2}}
    options.add_experimental_option("prefs", prefs)
    return options

def scrape_product_page(driver, url):
    wait = WebDriverWait(driver, 30)
    driver.get(url)
    try:
        table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table[role='region'][aria-live='polite']")))
        return table.get_attribute("outerHTML")
    except Exception as e:
        print(f"Table not found or failed to load for {url}: {e}")
        return None

def parse_numeric(value):
    value = value.replace("$", "").replace(",", "").strip()
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return 0

def parse_price_history(html):
    soup = BeautifulSoup(html, "html.parser")
    price_table = soup.find("table", {"role": "region", "aria-live": "polite"})
    price_history = []
    if price_table:
        rows = price_table.find_all("tr")[1:]
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 3:
                date_range = cells[0].get_text(strip=True)
                normal_price = parse_numeric(cells[10].get_text(strip=True))
                volume = parse_numeric(cells[11].get_text(strip=True))
                price_history.append({"date_range": date_range, "normal_price": normal_price, "volume": volume})
    return pd.DataFrame(price_history)

def convert_to_second_date(df):
    df['date'] = df['date_range'].str.split(' to ').str[10]
    current_year = pd.Timestamp.now().year
    df['date'] = pd.to_datetime(df['date'] + f'/{current_year}', format='%m/%d/%Y', errors='coerce')
    df.drop(columns=['date_range'], inplace=True)
    return df

def process_chunk(rows_chunk):
    display = Display(visible=0, size=(1280, 800))
    display.start()
    driver = webdriver.Chrome(options=get_chrome_options())
    local_history = []

    for _, row in rows_chunk.iterrows():
        html = scrape_product_page(driver, row['link'])
        if html:
            hist_df = parse_price_history(html)
            if not hist_df.empty:
                hist_df = convert_to_second_date(hist_df)
                hist_df["name"] = row["name"]
                hist_df["set"] = row["set"]
                local_history.append(hist_df)

    driver.quit()
    display.stop()
    return local_history
