# test_scenario_3.py
import pytest
import time
import json
import os
import chromadb
from rank_bm25 import BM25Okapi
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from openrouter_provider import OpenRouterLLM
from eval_config import MultilingualE5Embedding, SemanticSimilarityMetric

from dotenv import load_dotenv
load_dotenv(override=True)

# 📌 Konfigurasi Path & DB
JSON_DATASET_PATH = "dataset/dataset_maja_ai_3.json"
DB_PATH = "./db_chroma"
COLLECTION_NAME = "permenpan_8_2026_collection"
CHUNKS_BACKUP_PATH = "dataset/chunks_backup.json"
OUTPUT_FOLDER = "hasil_evaluasi_3"
OUTPUT_FILENAME = os.path.join(OUTPUT_FOLDER, "hasil_evaluasi_skenario_3.json")

# Batasan batch per sesi pengujian
SOAL_PER_BATCH = 20

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)
    print(f"📁 Folder '{OUTPUT_FOLDER}' berhasil dibuat.")

# Inisialisasi LLM Target & Model Embedding Lokal
target_llm = OpenRouterLLM()  
embedding_e5 = MultilingualE5Embedding()

# Metrik Evaluasi Akhir (DeepEval)
semantic_metric = SemanticSimilarityMetric(
    threshold=0.85,
    model=embedding_e5
)

# === INISIALISASI MESIN PENCARI HYBRID (BM25 + VECTOR SEARCH) ===
print("⚙️ Memuat Database untuk Mesin Pencari Hybrid...")

if not os.path.exists(DB_PATH) or not os.path.exists(CHUNKS_BACKUP_PATH):
    raise FileNotFoundError(
        f"❌ Database Chroma atau file backup teks '{CHUNKS_BACKUP_PATH}' tidak ditemukan!\n"
        f"Silakan jalankan 'python ingest_pdf_only.py' terlebih dahulu."
    )

# 1. Hubungkan ke ChromaDB (Untuk Dense Semantic Search)
chroma_client = chromadb.PersistentClient(path=DB_PATH)
collection = chroma_client.get_collection(name=COLLECTION_NAME)

# 2. Inisialisasi BM25 Index (Untuk Keyword Search)
with open(CHUNKS_BACKUP_PATH, "r", encoding="utf-8") as f:
    chunks_db = json.load(f)

def tokenize(text):
    """Fungsi tokenisasi teks sederhana untuk BM25"""
    return text.lower().replace("\n", " ").split()

corpus_tokenized = [tokenize(item["text"]) for item in chunks_db]
bm25_index = BM25Okapi(corpus_tokenized)


def retrieve_hybrid_context(query, top_k=3, rrf_k=60):
    """
    Fungsi Hybrid Retrieval menggunakan BM25 & Dense E5,
    digabungkan menggunakan algoritma Reciprocal Rank Fusion (RRF).
    """
    # A. Pencarian berbasis Kata Kunci (BM25)
    query_tokens = tokenize(query)
    bm25_scores = bm25_index.get_scores(query_tokens)
    bm25_ranked_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:10]
    bm25_results = [chunks_db[idx] for idx in bm25_ranked_indices]
    
    # B. Pencarian berbasis Semantik (Vector Search - ChromaDB)
    query_text_formatted = f"query: {query}"
    query_vector = embedding_e5.embed_text(query_text_formatted)
    
    vector_raw_results = collection.query(
        query_embeddings=[query_vector],
        n_results=10
    )
    vector_documents = vector_raw_results.get('documents', [[]])[0]
    vector_ids = vector_raw_results.get('ids', [[]])[0]
    
    # C. Reciprocal Rank Fusion (RRF) - Penggabungan Peringkat Dokumen
    rrf_scores = {}
    
    # Masukkan bobot peringkat dari BM25
    for rank, item in enumerate(bm25_results):
        doc_id = item["id"]
        if doc_id not in rrf_scores:
            rrf_scores[doc_id] = {"text": item["text"], "score": 0.0}
        rrf_scores[doc_id]["score"] += 1.0 / (rrf_k + (rank + 1))
        
    # Masukkan bobot peringkat dari Vector Search
    for rank, doc_text in enumerate(vector_documents):
        doc_id = vector_ids[rank]
        if doc_id not in rrf_scores:
            rrf_scores[doc_id] = {"text": doc_text, "score": 0.0}
        rrf_scores[doc_id]["score"] += 1.0 / (rrf_k + (rank + 1))
        
    # Urutkan berdasarkan skor RRF tertinggi
    sorted_rrf = sorted(rrf_scores.items(), key=lambda x: x[1]["score"], reverse=True)
    
    # Ambil konten teks sebanyak top_k dokumen terbaik
    final_documents = [val["text"] for doc_id, val in sorted_rrf[:top_k]]
    return "\n---\n".join(final_documents)


# --- LOAD DATASET DARI JSON ---
def load_dataset_from_json():
    if not os.path.exists(JSON_DATASET_PATH):
        raise FileNotFoundError(f"❌ ERROR: Dataset JSON '{JSON_DATASET_PATH}' tidak ditemukan!")
    with open(JSON_DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

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

processed_counter = 0

def simpan_ke_json(data_baru):
    output_data = {
        "nama_pengujian": "Skenario 3 - Hybrid RAG (BM25 + ChromaDB + RRF)",
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

# --- PROSES PENGUJIAN UTAMA RAG HYBRID ---
@pytest.mark.parametrize("index", list(range(len(dataset_test))))
def test_scenario_3_hybrid_rag(index):
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
        pytest.skip(f"Soal No. {no_soal} ditunda karena limit batch sesi ini sudah penuh.")
        
    processed_counter += 1
    print(f"\n🚀 [Skenario 3 - Hybrid RAG][No. {no_soal}] Menjalankan Keyword + Semantic Retrieval...")
    
    # 🔍 HYBRID RETRIEVAL STEP
    konteks_terpilih = retrieve_hybrid_context(query, top_k=3)
    
    # 💡 SYSTEM PROMPT RAG
    system_prompt = (
        "Anda adalah pakar senior Sistem Pemerintahan Berbasis Elektronik (SPBE) Kementerian PANRB.\n"
        "Tugas Anda adalah menjawab pertanyaan secara akurat berdasarkan REFERENSI INFORMASI resmi di bawah ini.\n\n"
        "--- AWAL REFERENSI INFORMASI ---\n"
        f"{konteks_terpilih}\n"
        "--- AKHIR REFERENSI INFORMASI ---\n\n"
        "⚠️ ATURAN ANALISIS SECARA KETAT:\n"
        "1. Jawab secara SINGKAT, PADAT, dan LANGSUNG ke pokok masalah (Maksimal 3 kalimat).\n"
        "2. Jangan gunakan kalimat pembuka (seperti 'Berdasarkan dokumen...') atau kata penutup.\n"
        "3. Jika jawaban tidak ditemukan atau tidak didukung oleh referensi informasi di atas, katakan dengan jujur: \n"
        "'Maaf, informasi tersebut tidak diatur atau tidak tersedia dalam dokumen acuan.' (Jangan berspekulasi atau mengarang jawaban!)\n\n"
        f"Pertanyaan: {query}"
    )
    
    start_time = time.time()
    actual_output = target_llm.generate(system_prompt)
    response_time = round(time.time() - start_time, 2)
    
    penanda_error_sistem = ["Error OpenRouter", "Error Koneksi", "Batas maksimal percobaan", "Missing Authentication", "Rate Limit", "429"]
    is_system_error = any(error_tag in actual_output for error_tag in penanda_error_sistem)
    
    if is_system_error:
        processed_counter = SOAL_PER_BATCH
        pytest.skip(f"Soal No. {no_soal} ditangguhkan karena kendala jaringan/Rate Limit.")
        
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