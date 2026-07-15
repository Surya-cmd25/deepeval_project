# check_env.py
import os
from dotenv import load_dotenv

def cek_konfigurasi_env():
    # 1. Tentukan file .env yang ingin dicek
    env_filename = ".env"
    
    print("==================================================")
    print("🔍 MEMULAI PEMERIKSAAN KONFIGURASI LINGKUNGAN (.env)")
    print("==================================================")
    
    # 2. Cek apakah file .env secara fisik ada di folder proyek
    if not os.path.exists(env_filename):
        print(f"❌ ERROR: File '{env_filename}' TIDAK DITEMUKAN di direktori ini!")
        print("💡 Solusi: Buat file bernama '.env' terlebih dahulu di folder utama proyek Anda.")
        print("==================================================")
        return False
    
    print(f"✅ File '{env_filename}' ditemukan.")
    
    # 3. Load variabel dari file .env (override=True agar mengambil nilai terbaru)
    load_dotenv(override=True)
    
    # 4. Daftar variabel wajib yang harus ada untuk skrip evaluasi Anda
    variabel_wajib = {
        "OPENROUTER_API_KEY": "Dibutuhkan untuk koneksi ke model LLM (Gemma) via OpenRouter.",
        "OPENAI_API_KEY": "Dibutuhkan oleh DeepEval sebagai default judge metric jika menggunakan model tertentu.",
    }
    
    ada_error = False
    print("\n📋 Memeriksa variabel di dalam .env:")
    
    for var, deskripsi in variabel_wajib.items():
        nilai = os.getenv(var)
        
        # Cek apakah variabel tidak terdaftar atau nilainya kosong/hanya spasi
        if nilai is None:
            print(f"❌ {var:<20} -> BELUM TERDAFTAR!")
            print(f"   ℹ️  Keterangan: {deskripsi}")
            ada_error = True
        elif nilai.strip() == "":
            print(f"⚠️  {var:<20} -> ADA, TAPI NILAINYA KOSONG (KOSONG/STRIP)!")
            print(f"   ℹ️  Keterangan: {deskripsi}")
            ada_error = True
        else:
            # Sensor nilai API Key agar aman saat ditampilkan di layar/terminal
            sensor_nilai = nilai[:6] + "..." + nilai[-4:] if len(nilai) > 10 else "******"
            print(f"✅ {var:<20} -> TERKONFIGURASI JELAS ({sensor_nilai})")
            
    print("==================================================")
    
    # 5. Kesimpulan Hasil Pemeriksaan
    if ada_error:
        print("❌ STATUS: Konfigurasi .env BELUM SIAP.")
        print("💡 Solusi: Silakan buka file .env Anda dan pastikan variabel di atas sudah diisi dengan benar.")
        print("==================================================")
        return False
    else:
        print("🚀 STATUS: KONDISI AMAN! Semua variabel .env siap digunakan.")
        print("==================================================")
        return True

if __name__ == "__main__":
    cek_konfigurasi_env()