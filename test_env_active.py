# test_env_active.py
import os
from dotenv import load_dotenv

print("==================================================")
print("🔄 STATUS MEMORI SEBELUM LOAD_DOTENV()")
print("==================================================")
print(f"OPENROUTER_API_KEY di OS: {os.environ.get('OPENROUTER_API_KEY') is not None}")
print(f"OPENAI_API_KEY di OS:     {os.environ.get('OPENAI_API_KEY') is not None}")

# Proses pengaktifan .env
print("\n⚙️  MENJALANKAN: load_dotenv(override=True)...")
termuat = load_dotenv(override=True)

print("\n==================================================")
print("🎯 STATUS MEMORI SETELAH LOAD_DOTENV()")
print("==================================================")
if termuat:
    print("✅ Pustaka dotenv BERHASIL membaca file .env Anda!")
else:
    print("❌ Pustaka dotenv GAGAL membaca file .env! (File mungkin tidak terbaca/salah folder)")

print("\n📋 Hasil Pengecekan Nilai Variabel:")

# Cek OpenRouter
router_key = os.getenv("OPENROUTER_API_KEY")
if router_key:
    print(f"✅ OPENROUTER_API_KEY -> AKTIF & TERBACA (Ujung key: ...{router_key[-4:]})")
else:
    print("❌ OPENROUTER_API_KEY -> TIDAK AKTIF / KOSONG!")

# Cek OpenAI Dummy
openai_key = os.getenv("OPENAI_API_KEY")
if openai_key:
    print(f"✅ OPENAI_API_KEY     -> AKTIF & TERBACA (Ujung key: ...{openai_key[-4:]})")
else:
    print("❌ OPENAI_API_KEY     -> TIDAK AKTIF / KOSONG!")
print("==================================================")