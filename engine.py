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
        # headless=False agar kamu bisa melihat pergerakan otomatisasi bot
       browser = p.chromium.launch(headless=True) 
        page = browser.new_page()

        # Looping 1: Berdasarkan Tingkat Daerah (Kelurahan -> Kecamatan -> Kabupaten)
        for area in daftar_lokasi:
            if not area: continue
            
            # Looping 2: Berdasarkan Kata Kunci (Komputer -> CCTV)
            for keyword in kata_kunci:
                query = f"{keyword} di {area}"
                print(f"\n=======================================================")
                print(f"[INFO] 🔍 MENCARI (MAX {MAX_PER_KATEGORI}): {query.upper()}")
                print(f"=======================================================")
                
                # Menggunakan URL direct search resmi Google Maps yang paling stabil untuk bot
                url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
                page.goto(url)

                try:
                    # Tunggu sampai list tempat di sebelah kiri benar-benar muncul
                    feed_selector = 'div[role="feed"]'
                    page.wait_for_selector(feed_selector, timeout=15000)
                    time.sleep(3) 

                    # Ambil handle elemen list kiri untuk keperluan scrolling via JavaScript
                    sidebar = page.locator(feed_selector).first

                    # -- TAHAP A: KUMPULKAN LINK TEMPAT (SCROLLING DENGAN BATAS KUOTA) --
                    print(f"[INFO] Mencari kandidat terdekat...")
                    links_tempat = set()
                    
                    percobaan_scroll_mentok = 0
                    waktu_mulai = time.time()
                    
                    while percobaan_scroll_mentok < 6:
                        # Ambil semua elemen link yang termuat saat ini
                        elemen_terlihat = page.locator('a[href*="/maps/place/"]').all()
                        for el in elemen_terlihat:
                            href = el.get_attribute('href')
                            if href: links_tempat.add(href)
                        
                        # 🛑 REVISI BREAK: Jika link yang terkumpul sudah mencapai/melebihi kuota, stop scroll!
                        if len(links_tempat) >= MAX_PER_KATEGORI:
                            print(f"[DEBUG] Target {MAX_PER_KATEGORI} kandidat terpenuhi di list sidebar.")
                            break
                        
                        jumlah_sebelumnya = len(links_tempat)
                        
                        # EXECUTE JAVASCRIPT: Menggulung scrollbar tepat di dalam komponen panel kiri
                        sidebar.evaluate("el => el.scrollTo(0, el.scrollHeight)")
                        time.sleep(3) # Jeda loading agar server mengirimkan sisa data
                        
                        # Cek apakah setelah di-scroll, data bertambah
                        if len(links_tempat) == jumlah_sebelumnya:
                            # Trik hentakan: scroll ke atas sedikit, lalu banting ke bawah lagi
                            sidebar.evaluate("el => el.scrollBy(0, -300)")
                            time.sleep(0.5)
                            sidebar.evaluate("el => el.scrollTo(0, el.scrollHeight)")
                            time.sleep(2)
                            
                            percobaan_scroll_mentok += 1
                        else:
                            percobaan_scroll_mentok = 0 # Reset hitungan jika data sukses bertambah
                            
                        # Batas aman waktu scrolling maksimal 45 detik per kata kunci daerah
                        if time.time() - waktu_mulai > 45:
                            break
                    
                    # 🛑 REVISI SLICING: Pastikan kita hanya mengambil maksimal 15 teratas (jarak terdekat)
                    list_links = list(links_tempat)[:MAX_PER_KATEGORI]
                    total_tempat = len(list_links)
                    print(f"\n[INFO] 🔥 SELESAI SISIR LIST! Memproses {total_tempat} tempat terdekat.")

                    # -- TAHAP B: EKSTRAKSI & FILTER NOMOR TELEPON --
                    for i, link in enumerate(list_links):
                        page.goto(link)
                        time.sleep(2.5) # Tunggu panel detail toko terbuka penuh

                        # 1. Cek Nomor Telepon Dahulu (Sebagai Validasi Utama)
                        telp_locator = page.locator('button[data-tooltip*="nomor telepon"]')
                        if telp_locator.count() > 0:
                            telp_raw = telp_locator.first.get_attribute('aria-label') or ""
                            telepon = telp_raw.replace("Nomor telepon: ", "").strip()
                        else:
                            telepon = "Tidak ada nomor"

                        # 🛑 JIKA TIDAK ADA NOMOR TELEPON, LANGSUNG SKIP KANDIDAT INI
                        if telepon == "Tidak ada nomor" or not telepon or "Tutup" in telepon:
                            print(f"[{i+1}/{total_tempat}] ⏭️ Di-skip: Tidak ada nomor telepon.")
                            continue

                        # 2. Ambil Nama Toko
                        nama_locator = page.locator('h1.DUwDvf')
                        nama = nama_locator.first.inner_text() if nama_locator.count() > 0 else "Nama tidak diketahui"

                        # 3. Ambil Alamat Toko
                        alamat_locator = page.locator('button[data-item-id="address"]')
                        if alamat_locator.count() > 0:
                            alamat_raw = alamat_locator.first.get_attribute('aria-label') or ""
                            alamat = alamat_raw.replace("Alamat: ", "").strip()
                        else:
                            alamat = "Alamat tidak tersedia"

                        # Simpan data yang lolos kualifikasi nomor kontak
                        data_teknisi.append({
                            "Pencarian": keyword.title(),
                            "Area": area.title(),
                            "Nama": nama.strip(),
                            "Alamat": alamat,
                            "Nomor Telepon": telepon
                        })
                        print(f"[{i+1}/{total_tempat}] ✅ Lolos & Ditarik: {nama.strip()} ({telepon})")

                except Exception as e:
                    print(f"[INFO] Batas list tercapai atau area tidak ditemukan untuk {query}")

        browser.close()

    # Masukkan seluruh data ke DataFrame
    df = pd.DataFrame(data_teknisi)
    
    if not df.empty:
        # Bersihkan data jika ada entitas ganda yang terjaring di beberapa level wilayah
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
