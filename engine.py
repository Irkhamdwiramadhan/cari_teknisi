from playwright.sync_api import sync_playwright
import pandas as pd
import time

def cari_teknisi(lokasi_input):
    print(f"\n[INFO] Memulai proses scraping terpadu untuk: {lokasi_input}")
    
    # 1. PECAH HIERARKI LOKASI Berdasarkan Koma
    daftar_lokasi = [l.strip() for l in lokasi_input.split(',')]
    
    # 2. KATA KUNCI PENCARIAN
    kata_kunci = ["servis komputer", "teknisi cctv"]
    
    # Batasan kuota data per kategori pencarian
    MAX_PER_KATEGORI = 15
    
    data_teknisi = []

    with sync_playwright() as p:
        # Argumen anti-crash dan diet memori ekstrim untuk server Cloud
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-features=site-per-process", 
                "--disable-software-rasterizer"
            ]
        ) 
        
        # Pakaikan topeng manusia dengan resolusi HD (1280x720) agar RAM server lega
        context = browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='id-ID',
            timezone_id='Asia/Jakarta'
        )
        page = context.new_page()

        # Looping 1: Berdasarkan Tingkat Daerah
        for area in daftar_lokasi:
            if not area: continue
            
            # Looping 2: Berdasarkan Kata Kunci
            for keyword in kata_kunci:
                query = f"{keyword} di {area}"
                print(f"\n=======================================================")
                print(f"[INFO] 🔍 MENCARI (MAX {MAX_PER_KATEGORI}): {query.upper()}")
                print(f"=======================================================")
                
                # Menggunakan URL direct search resmi Google Maps
                url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
                
                try:
                    # Timeout 60 detik agar tidak putus asa saat koneksi melambat
                    page.goto(url, timeout=60000)

                    feed_selector = 'div[role="feed"]'
                    page.wait_for_selector(feed_selector, timeout=15000)
                    time.sleep(3.5) 

                    sidebar = page.locator(feed_selector).first

                    print(f"[INFO] Mencari kandidat terdekat dan mengidentifikasi informasi jarak...")
                    
                    dict_kandidat = {}
                    
                    percobaan_scroll_mentok = 0
                    waktu_mulai = time.time()
                    
                    # -- TAHAP A: SCROLL & AMBIL JARAK --
                    while percobaan_scroll_mentok < 5:
                        links_el = page.locator('a[href*="/maps/place/"]').all()
                        
                        for el in links_el:
                            href = el.get_attribute('href')
                            if href and href not in dict_kandidat:
                                jarak_toko = "Cek di alamat"
                                
                                try:
                                    card_parent = el.locator('xpath=./ancestor::div[contains(@class, "Nv2ybe") or contains(@class, "hfpxzc") or @role="article" or @jsaction]').first
                                    if card_parent.count() > 0:
                                        spans = card_parent.locator('span').all()
                                        for span in spans:
                                            txt = span.inner_text().strip()
                                            if len(txt) < 15 and (' km' in txt or ' m' in txt) and 'mnt' not in txt and 'jam' not in txt:
                                                jarak_toko = txt
                                                break
                                except:
                                    pass 
                                
                                dict_kandidat[href] = jarak_toko
                        
                        if len(dict_kandidat) >= MAX_PER_KATEGORI:
                            print(f"[DEBUG] Target {MAX_PER_KATEGORI} kandidat terdekat terpenuhi.")
                            break
                        
                        jumlah_sebelumnya = len(dict_kandidat)
                        
                        sidebar.evaluate("el => el.scrollTo(0, el.scrollHeight)")
                        time.sleep(3) 
                        
                        if len(dict_kandidat) == jumlah_sebelumnya:
                            sidebar.evaluate("el => el.scrollBy(0, -300)")
                            time.sleep(0.5)
                            sidebar.evaluate("el => el.scrollTo(0, el.scrollHeight)")
                            time.sleep(2)
                            percobaan_scroll_mentok += 1
                        else:
                            percobaan_scroll_mentok = 0 
                            
                        if time.time() - waktu_mulai > 50:
                            break
                    
                    list_kandidat = list(dict_kandidat.items())[:MAX_PER_KATEGORI]
                    total_tempat = len(list_kandidat)
                    
                    # FALLBACK MODE DARURAT
                    if total_tempat == 0:
                        print("[INFO] Mode deteksi jarak gagal, mengaktifkan mode Fallback Darurat...")
                        elements_fallback = page.locator('a[href*="/maps/place/"]').all()
                        list_kandidat = [(el.get_attribute('href'), "Cek di alamat") for el in elements_fallback if el.get_attribute('href')][:MAX_PER_KATEGORI]
                        total_tempat = len(list_kandidat)

                    print(f"\n[INFO] 🔥 SELESAI SISIR LIST! Memproses detail {total_tempat} tempat terdekat.")

                    # -- TAHAP B: EKSTRAKSI DETAIL --
                    for i, (link, jarak) in enumerate(list_kandidat):
                        # Timeout 45 detik untuk setiap detail toko
                        page.goto(link, timeout=45000)
                        time.sleep(2.5) 

                        telp_locator = page.locator('button[data-tooltip*="nomor telepon"]')
                        if telp_locator.count() > 0:
                            telp_raw = telp_locator.first.get_attribute('aria-label') or ""
                            telepon = telp_raw.replace("Nomor telepon: ", "").strip()
                        else:
                            telepon = "Tidak ada nomor"

                        if telepon == "Tidak ada nomor" or not telepon or "Tutup" in telepon:
                            print(f"[{i+1}/{total_tempat}] ⏭️ Di-skip: Tidak ada nomor telepon.")
                            continue

                        nama_locator = page.locator('h1.DUwDvf')
                        nama = nama_locator.first.inner_text() if nama_locator.count() > 0 else "Nama tidak diketahui"

                        alamat_locator = page.locator('button[data-item-id="address"]')
                        if alamat_locator.count() > 0:
                            alamat_raw = alamat_locator.first.get_attribute('aria-label') or ""
                            alamat = alamat_raw.replace("Alamat: ", "").strip()
                        else:
                            alamat = "Alamat tidak tersedia"

                        # Menyimpan 'Jarak' wajib ada agar app.py tidak error
                        data_teknisi.append({
                            "Pencarian": keyword.title(),
                            "Area": area.title(),
                            "Nama": nama.strip(),
                            "Alamat": alamat,
                            "Nomor Telepon": telepon,
                            "Jarak": jarak
                        })
                        print(f"[{i+1}/{total_tempat}] ✅ Lolos & Ditarik: {nama.strip()} (Jarak: {jarak})")

                except Exception as e:
                    print(f"[INFO] Batas list tercapai atau area tidak ditemukan untuk {query}")

        browser.close()

    df = pd.DataFrame(data_teknisi)
    
    if not df.empty:
        df = df.drop_duplicates(subset=['Nama', 'Nomor Telepon'])
        df.reset_index(drop=True, inplace=True)
        
    return df

if __name__ == "__main__":
    lokasi_test = "Kabupaten Tegal"
    df_hasil = cari_teknisi(lokasi_test)
    
    print("\n=======================================================")
    print("                HASIL AKHIR SCRAPING                   ")
    print("=======================================================")
    print(df_hasil.to_string())
    print(f"\nTotal Data Didapatkan: {len(df_hasil)} Teknisi")
