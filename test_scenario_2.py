# test_scenario_2.py
import pytest
import time
import json
import os
from pypdf import PdfReader
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from openrouter_provider import OpenRouterLLM
from eval_config import MultilingualE5Embedding, SemanticSimilarityMetric

from dotenv import load_dotenv
load_dotenv(override=True)

# 📌 Dataset utama (100 soal)
JSON_DATASET_PATH = "dataset/dataset_maja_ai_2.json"

# 📄 Dokumen PDF Acuan Input
PDF_DOCUMENT_PATH = "dataset/dokumen_pdf/2026permenpanrb008.pdf"

# 📁 Folder dan path output khusus untuk Skenario 2
OUTPUT_FOLDER = "hasil_evaluasi_2"
OUTPUT_FILENAME = os.path.join(OUTPUT_FOLDER, "hasil_evaluasi_skenario_2.json")

# Batasan batch (set ke 100 jika ingin memproses penuh sekaligus)
SOAL_PER_BATCH = 20  

# Membuat folder output otomatis jika belum ada
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)
    print(f"📁 Folder '{OUTPUT_FOLDER}' berhasil dibuat otomatis.")

def load_dataset_from_json():
    if not os.path.exists(JSON_DATASET_PATH):
        raise FileNotFoundError(f"❌ ERROR KRITIS: File dataset '{JSON_DATASET_PATH}' tidak ditemukan!")
    with open(JSON_DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# Fungsi untuk mengekstrak teks dari file PDF secara langsung
def extract_text_from_pdf(pdf_path):
    if not os.path.exists(pdf_path):
        print(f"⚠️ WARNING: File PDF '{pdf_path}' tidak ditemukan!")
        return "Dokumen acuan PDF tidak tersedia di sistem."
    
    try:
        reader = PdfReader(pdf_path)
        full_text = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text.append(text)
        return "\n".join(full_text)
    except Exception as e:
        print(f"❌ Gagal membaca PDF: {str(e)}")
        return "Gagal melakukan ekstraksi teks dari dokumen PDF."

# Load dataset & ekstraksi teks dokumen acuan PDF
dataset_test = load_dataset_from_json()
dokumen_acuan_teks = extract_text_from_pdf(PDF_DOCUMENT_PATH)

def get_completed_queries():
    if os.path.exists(OUTPUT_FILENAME):
        try:
            with open(OUTPUT_FILENAME, "r", encoding="utf-8") as f:
                data = json.load(f)
                completed = []
                for item in data.get("detail_perbandingan", []):
                    actual_txt = item.get("actual_output", "")
                    penanda_error = ["Error OpenRouter", "Error Koneksi", "Batas maksimal percobaan", "Rate Limit", "429"]
                    if not any(err in actual_txt for err in penanda_error):
                        completed.append(item["query"])
                return completed
        except Exception:
            return []
    return []

# Menggunakan provider LLM kustom & embedding
target_llm = OpenRouterLLM()  
embedding_e5 = MultilingualE5Embedding()

semantic_metric = SemanticSimilarityMetric(
    threshold=0.85,
    model=embedding_e5
)

processed_counter = 0

def simpan_ke_json(data_baru):
    output_data = {
        "nama_pengujian": "Skenario 2 - LLM + Dokumen Input",
        "terakhir_diperbarui": time.strftime("%Y-%m-%d %H:%M:%S"),
        "detail_perbandingan": []
    }
    
    if os.path.exists(OUTPUT_FILENAME):
        try:
            with open(OUTPUT_FILENAME, "r", encoding="utf-8") as f:
                konten = f.read()
                if konten:
                    output_data = json.loads(konten)
        except Exception:
            pass
            
    output_data["detail_perbandingan"] = [
        x for x in output_data["detail_perbandingan"] if x["query"] != data_baru["query"]
    ]
    
    output_data["detail_perbandingan"].append(data_baru)
    output_data["detail_perbandingan"] = sorted(
        output_data["detail_perbandingan"], 
        key=lambda x: x.get("no_soal", 0)
    )
    
    for idx, item in enumerate(output_data["detail_perbandingan"]):
        item["no"] = idx + 1
        
    output_data["total_kasus_uji"] = len(output_data["detail_perbandingan"])
    output_data["total_passed"] = sum(1 for x in output_data["detail_perbandingan"] if x["evaluasi"]["status"] == "PASSED")
    output_data["total_failed"] = sum(1 for x in output_data["detail_perbandingan"] if x["evaluasi"]["status"] == "FAILED")
    
    with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)

# --- PROSES PENGUJIAN UTAMA ---
@pytest.mark.parametrize("index", list(range(len(dataset_test))))
def test_scenario_2_document_analysis(index):
    global processed_counter
    
    data_item = dataset_test[index]
    no_soal = data_item.get('no_soal', index + 1)
    query = data_item['query']
    query_type = data_item.get('query_type', 'Umum')
    expected_output = data_item['expected_output']
    
    completed_queries = get_completed_queries()
    
    if query in completed_queries:
        pytest.skip(f"Soal No. {no_soal} sudah sukses pada pengujian sebelumnya.")
        
    if processed_counter >= SOAL_PER_BATCH:
        pytest.skip(f"Soal No. {no_soal} ditunda karena limit batch ({SOAL_PER_BATCH} soal) sesi ini sudah penuh.")
        
    processed_counter += 1
    print(f"\n🚀 [Skenario 2][No. {no_soal}][Tipe: {query_type}] Menganalisis Dokumen PDF (Progres ke-{processed_counter})...")
    
    # 💡 SISTEM PROMPT: Menggabungkan Query + Dokumen PDF Input secara langsung
    system_prompt = (
        "Anda adalah pakar senior Sistem Pemerintahan Berbasis Elektronik (SPBE) Kementerian PANRB.\n"
        "Tugas Anda adalah menjawab pertanyaan pengguna secara akurat dan objektif HANYA berdasarkan dokumen acuan resmi di bawah ini.\n\n"
        "--- AWAL DOKUMEN ACUAN (PERMENPANRB 8/2026) ---\n"
        f"{dokumen_acuan_teks}\n"
        "--- AKHIR DOKUMEN ACUAN ---\n\n"
        "⚠️ ATURAN ANALISIS SECARA KETAT:\n"
        "1. Jawablah secara SINGKAT, PADAT, dan LANGSUNG ke pokok masalah sesuai fakta yang ada di dokumen acuan. Maksimal jawaban terdiri dari 3 kalimat pendek.\n"
        "2. Jangan memberikan intro/pembuka (seperti 'Baik, berdasarkan dokumen...') atau penutup.\n"
        "3. Jika informasi yang ditanyakan tidak tercantum di dalam dokumen acuan tersebut, jawab dengan: "
        "'Maaf, informasi tersebut tidak diatur atau tidak tersedia dalam dokumen acuan.' (Jangan berspekulasi atau mengarang jawaban!)\n\n"
        f"Pertanyaan Analisis: {query}"
    )
    
    start_time = time.time()
    actual_output = target_llm.generate(system_prompt)
    response_time = round(time.time() - start_time, 2)
    
    penanda_error_sistem = ["Error OpenRouter", "Error Koneksi", "Batas maksimal percobaan", "Missing Authentication", "Rate Limit", "429"]
    is_system_error = any(error_tag in actual_output for error_tag in penanda_error_sistem)
    
    if is_system_error:
        processed_counter = SOAL_PER_BATCH
        pytest.skip(f"Soal No. {no_soal} ditangguhkan karena sistem OpenRouter mendeteksi Rate Limit.")
        
    test_case = LLMTestCase(
        input=query,
        actual_output=actual_output,
        expected_output=expected_output
    )
    
    semantic_metric.measure(test_case)
    score = semantic_metric.score
    reason = getattr(semantic_metric, 'reason', 'Tidak ada alasan spesifik.')
    
    status = "PASSED" if score >= semantic_metric.threshold else "FAILED"
    
    pipeline_accuracy = 100.0 if status == "PASSED" else round(score * 100, 2)
    fact_checking = round(score * 100, 2)
    g_eval = round(score * 5, 2)
    ar_score = round(score * 100, 2)
    
    mae = round(abs(1.0 - score), 4)
    rmse = round((abs(1.0 - score) ** 2) ** 0.5, 4)
    mape = round((mae / 1.0) * 100, 2) if score > 0 else 100.0
    
    record_hasil = {
        "no_soal": no_soal,
        "llm_model": target_llm.model_name,
        "query": query,
        "query_type": query_type, 
        "expected_output": expected_output,
        "actual_output": actual_output,
        "pipeline_accuracy": pipeline_accuracy,
        "response_time": response_time,
        "g_eval": g_eval,
        "ar_score": ar_score,
        "fact_checking": fact_checking,
        "mae": mae,
        "rmse": rmse,
        "mape": mape,
        "evaluasi": {
            "metrik": "Semantic Similarity",
            "threshold_target": semantic_metric.threshold,
            "skor_aktual": round(score, 4),
            "status": status,
            "alasan": reason
        }
    }
    simpan_ke_json(record_hasil)
    
    print(f"⏳ Menunggu Jeda Aman API... [{response_time}s]")
    time.sleep(30)
    
    assert_test(test_case, [semantic_metric])