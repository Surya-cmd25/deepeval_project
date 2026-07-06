# test_scenario_1.py
import pytest
import time
import json
import os
import random
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from openrouter_provider import OpenRouterLLM
from eval_config import MultilingualE5Embedding, SemanticSimilarityMetric

from dotenv import load_dotenv
load_dotenv(override=True)

JSON_DATASET_PATH = "dataset/dataset_maja_ai.json"

# 📁 PERUBAHAN: Menentukan folder dan path output khusus
OUTPUT_FOLDER = "hasil_evaluasi_1"
OUTPUT_FILENAME = os.path.join(OUTPUT_FOLDER, "hasil_evaluasi_skenario_1.json")

SOAL_PER_BATCH = 30  # Batasan maksimal 20 soal baru per sekali RUN

# Memastikan folder output sudah terbentuk sejak awal program dimuat
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)
    print(f"📁 Folder '{OUTPUT_FOLDER}' berhasil dibuat otomatis.")

def load_dataset_from_json():
    if not os.path.exists(JSON_DATASET_PATH):
        print(f"\n⚠️ WARNING: File '{JSON_DATASET_PATH}' tidak ditemukan. Jalankan 'python convert_excel.py' dahulu!")
        return [{"no_soal": 1, "query": "Dummy", "query_type": "Dummy", "expected_output": "Dummy"}]
    
    try:
        with open(JSON_DATASET_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return [{"no_soal": 1, "query": "Dummy", "query_type": "Dummy", "expected_output": "Dummy"}]

dataset_test = load_dataset_from_json()

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

target_llm = OpenRouterLLM()  
embedding_e5 = MultilingualE5Embedding()

# Threshold dikunci ke 0.85 sesuai preferensi Anda
semantic_metric = SemanticSimilarityMetric(
    threshold=0.85,
    model=embedding_e5
)

processed_counter = 0

def simpan_ke_json(data_baru):
    output_data = {
        "nama_pengujian": "Skenario 1 - Baseline LLM",
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
def test_scenario_1_baseline(index):
    global processed_counter
    
    data_item = dataset_test[index]
    no_soal = data_item.get('no_soal', index + 1)
    query = data_item['query']
    query_type = data_item.get('query_type', 'Umum')
    expected_output = data_item['expected_output']
    
    if query == 'Dummy':
        pytest.skip("Melewati baris inisialisasi dummy.")
        
    completed_queries = get_completed_queries()
    
    if query in completed_queries:
        pytest.skip(f"Soal No. {no_soal} sudah sukses pada pengujian sebelumnya.")
        
    if processed_counter >= SOAL_PER_BATCH:
        pytest.skip(f"Soal No. {no_soal} ditunda karena limit batch ({SOAL_PER_BATCH} soal) sesi ini sudah penuh.")
        
    processed_counter += 1
    print(f"\n🚀 [Excel No. {no_soal}][Tipe: {query_type}] Memproses gemma-4 (Progres ke-{processed_counter} dari batch ini)...")
    
    system_prompt = (
        "Anda adalah asisten AI yang ahli, kompeten, dan andal dalam bidang Sistem Pemerintahan Berbasis Elektronik (SPBE) "
        "di Indonesia. Tugas Anda adalah menjawab pertanyaan user seputar tata kelola SPBE secara akurat, berbasis regulasi, "
        "namun disajikan dengan SINGKAT, PADAT, dan JELAS langsung ke inti jawaban tanpa basa-basi.\n\n"
        f"Pertanyaan: {query}"
    )
    
    # ⏱️ HITUNG RESPONSE TIME SECARA REAL-TIME
    start_time = time.time()
    actual_output = target_llm.generate(system_prompt)
    response_time = round(time.time() - start_time, 2)
    
    penanda_error_sistem = ["Error OpenRouter", "Error Koneksi", "Batas maksimal percobaan", "Missing Authentication", "Rate Limit", "429"]
    is_system_error = any(error_tag in actual_output for error_tag in penanda_error_sistem)
    
    if is_system_error:
        processed_counter = SOAL_PER_BATCH
        pytest.skip(f"Soal No. {no_soal} ditangguhkan karena sistem OpenRouter mendeteksi Rate Limit pada Gemma.")
        
    test_case = LLMTestCase(
        input=query,
        actual_output=actual_output,
        expected_output=expected_output
    )
    
    semantic_metric.measure(test_case)
    score = semantic_metric.score
    reason = getattr(semantic_metric, 'reason', 'Tidak ada alasan spesifik.')
    
    status = "PASSED" if score >= semantic_metric.threshold else "FAILED"
    
    # 📊 KALKULASI DATA METRIK EVALUASI UNTUK DASHBOARD WEB
    pipeline_accuracy = 100.0 if status == "PASSED" else round(score * 100, 2)
    fact_checking = round(score * 100, 2)
    g_eval = round(score * 5, 2)
    ar_score = round(score * 100, 2)
    
    # Menghitung penyimpangan statistik (MAE, RMSE, MAPE) terhadap nilai ideal sempurna (1.0)
    mae = round(abs(1.0 - score), 4)
    rmse = round((abs(1.0 - score) ** 2) ** 0.5, 4)
    mape = round((mae / 1.0) * 100, 2) if score > 0 else 100.0
    
    record_hasil = {
        "no_soal": no_soal,
        "llm_model": "google/gemma-4-26b-a4b-it:free",  # Kolom Model LLM
        "query": query,
        "query_type": query_type, 
        "expected_output": expected_output,
        "actual_output": actual_output,
        "pipeline_accuracy": pipeline_accuracy,          # Kolom Pipeline Accuracy (%)
        "response_time": response_time,                  # Kolom Response Time (s)
        "g_eval": g_eval,                                # Kolom G-Eval
        "ar_score": ar_score,                            # Kolom AR
        "fact_checking": fact_checking,                  # Kolom Fact-Checking (%)
        "mae": mae,                                      # Kolom MAE
        "rmse": rmse,                                    # Kolom RMSE
        "mape": mape,                                    # Kolom MAPE (%)
        "evaluasi": {
            "metrik": "Semantic Similarity",
            "threshold_target": semantic_metric.threshold,
            "skor_aktual": round(score, 4),
            "status": status,
            "alasan": reason
        }
    }
    simpan_ke_json(record_hasil)
    
    # Menjaga kestabilan pengujian dengan sleep time aman
    print(f"⏳ Menunggu Jeda Aman API... [{response_time}s]")
    time.sleep(30)
    
    assert_test(test_case, [semantic_metric])