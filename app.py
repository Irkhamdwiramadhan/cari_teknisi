import streamlit as st
import pandas as pd
from engine import cari_teknisi

os.system("playwright install chromium")
# Konfigurasi halaman
st.set_page_config(page_title="Pencari Teknisi", layout="wide")

st.title("🔍 Sistem Pencari Teknisi AKTIVASI")

# Form Input
lokasi = st.text_input("Masukkan Lokasi Aktivasi (Contoh: Kelurahan Dukuhbenda, Kecamatan Bumijawa, Kabupaten Tegal)")

# Tombol Eksekusi
if st.button("Cari Teknisi"):
    if lokasi:
        # Menampilkan efek loading
        with st.spinner(f"Mesin sedang mencari teknisi di area {lokasi}..."):
            df = cari_teknisi(lokasi)
            
            if not df.empty:
                # --- DATA CLEANING ADVANCED & LOGIKA WHATSAPP ---
                # 1. Paksa kolom Nomor Telepon menjadi string dan bersihkan semua teks pengantar
                df['Nomor Bersih'] = df['Nomor Telepon'].astype(str)
                df['Nomor Bersih'] = df['Nomor Bersih'].str.replace('Nomor telepon:', '', regex=False)
                df['Nomor Bersih'] = df['Nomor Bersih'].str.replace('Telepon:', '', regex=False)
                
                # 2. Bersihkan semua spasi dan karakter khusus (strip, tanda kurung)
                df['Nomor Bersih'] = df['Nomor Bersih'].str.replace('-', '', regex=False)
                df['Nomor Bersih'] = df['Nomor Bersih'].str.replace(' ', '', regex=False)
                df['Nomor Bersih'] = df['Nomor Bersih'].str.replace('(', '', regex=False)
                df['Nomor Bersih'] = df['Nomor Bersih'].str.replace(')', '', regex=False)
                df['Nomor Bersih'] = df['Nomor Bersih'].str.replace('+', '', regex=False)
                
                # 3. Fungsi komprehensif mengubah awalan nomor ke format internasional (62)
                def format_wa(nomor):
                    if not nomor:
                        return "Tidak Valid"
                    
                    if nomor.isalpha():
                        return "Tidak Valid"
                        
                    if nomor.startswith('0'):
                        return '62' + nomor[1:]
                    elif nomor.startswith('62'):
                        return nomor
                    return nomor
                
                df['Nomor WA'] = df['Nomor Bersih'].apply(format_wa)
                
                # 4. TEMPLATE PESAN BARU (Dinamis sesuai lokasi input)
                pesan_template = (
                    f"Halo pak, perkenalkan saya dari Satu Akses Indonesia (Satu ID).\n"
                    f"Saya dapet nomer bapak dari google maps, saat ini saya butuh tenaga freelance untuk aktivasi perangkat jaringan di area {lokasi}, "
                    f"kebutuhannya teknisi yang onsite harus membawa laptop yang sudah support port lan. "
                    f"Untuk pekerjaannya nanti akan dipandu oleh tim kami dari pusat dan untuk setting perangkat semua by team dari pusat, "
                    f"untuk perangkat jaringan sudah sampai di masing masing lokasi.\n\n"
                    f"Tools wajib:\n"
                    f"- Winbox\n"
                    f"- Ultraviewer / Anydesk\n"
                    f"- Timestamp di HP"
                )
                
                # Encode text agar aman digunakan di URL browser (spasi jadi %20, enter jadi %0A)
                pesan_url = pesan_template.replace(' ', '%20').replace('\n', '%0A')
                
                df['Link WhatsApp'] = df['Nomor WA'].apply(
                    lambda x: f"https://wa.me/{x}?text={pesan_url}" if str(x).isdigit() and len(str(x)) > 8 else "Tidak Valid"
                )
                
                # --- FILTER DATA AGAR STREAMLIT TIDAK CRASH ---
                df_valid = df[df['Link WhatsApp'] != "Tidak Valid"].copy()
                
                if not df_valid.empty:
                    # --- REVISI: TAMBAHKAN KOLOM NOMOR URUT MANUAL ---
                    df_valid.reset_index(drop=True, inplace=True)
                    df_valid['No'] = df_valid.index + 1
                    
                    # --- TAMPILKAN TABEL ---
                    st.success(f"Berhasil menemukan teknisi di {lokasi}! Menampilkan {len(df_valid)} data ber-WhatsApp murni.")
                    
                    st.dataframe(
                        df_valid[['No', 'Nama', 'Alamat', 'Nomor Telepon', 'Link WhatsApp']],
                        column_config={
                            "No": st.column_config.NumberColumn("No", format="%d"),
                            "Link WhatsApp": st.column_config.LinkColumn("Action", display_text="Chat WA 💬")
                        },
                        hide_index=True,
                        width="stretch"
                    )
                else:
                    st.warning("Data ditemukan, namun tidak ada nomor yang valid untuk WhatsApp (khusus telepon rumah/kantor).")
            else:
                st.warning("Waduh, tidak ada data teknisi yang ditemukan di lokasi tersebut.")
    else:
        st.error("Lokasi tidak boleh kosong!")