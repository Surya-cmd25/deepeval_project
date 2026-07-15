# ingest_pdf_only.py
import os
import json
import chromadb
from pypdf import PdfReader
from eval_config import MultilingualE5Embedding

# 📌 Konfigurasi Path
PDF_FOLDER_PATH = "dataset/dokumen_pdf"
DB_PATH = "./db_chroma"
COLLECTION_NAME = "permenpan_8_2026_collection"
CHUNKS_BACKUP_PATH = "dataset/chunks_backup.json" # Untuk mesin BM25

def chunk_pdf_file(pdf_path, chunk_size=700, overlap=150):
    reader = PdfReader(pdf_path)
    full_text = ""
    file_name = os.path.basename(pdf_path)
    
    for page_idx, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            full_text += text + f"\n\n[Sumber Dokumen: {file_name} - Halaman {page_idx + 1}]\n\n"
            
    chunks = []
    start = 0
    while start < len(full_text):
        end = start + chunk_size
        chunks.append(full_text[start:end].strip())
        start += chunk_size - overlap
    return chunks

def main():
    print("⏳ Menghubungkan ke database ChromaDB...")
    chroma_client = chromadb.PersistentClient(path=DB_PATH)
    
    try:
        chroma_client.delete_collection(name=COLLECTION_NAME)
        print("🗑️ Koleksi database lama berhasil dibersihkan.")
    except Exception:
        pass

    collection = chroma_client.create_collection(name=COLLECTION_NAME)
    embedding_e5 = MultilingualE5Embedding()
    
    if not os.path.exists(PDF_FOLDER_PATH):
        os.makedirs(PDF_FOLDER_PATH)
        print(f"⚠️ Folder '{PDF_FOLDER_PATH}' dibuat otomatis. Silakan taruh file PDF Anda di sana.")
        return

    pdf_files = [f for f in os.listdir(PDF_FOLDER_PATH) if f.lower().endswith('.pdf')]
    if not pdf_files:
        print(f"❌ Tidak ada PDF di '{PDF_FOLDER_PATH}'")
        return

    all_chunks_data = [] # List untuk menyimpan semua chunk teks murni untuk BM25
    total_chunks = 0

    for pdf_file in pdf_files:
        pdf_path = os.path.join(PDF_FOLDER_PATH, pdf_file)
        print(f"📖 Memproses: {pdf_file}...")
        try:
            chunks = chunk_pdf_file(pdf_path)
            for idx, chunk in enumerate(chunks):
                passage_text = f"passage: {chunk}"
                vector = embedding_e5.embed_text(passage_text)
                
                chunk_id = f"pdf_{pdf_file}_chunk_{idx}"
                
                # Simpan ke ChromaDB
                collection.add(
                    ids=[chunk_id],
                    embeddings=[vector],
                    documents=[chunk],
                    metadatas=[{"source_file": pdf_file, "chunk_index": idx}]
                )
                
                # Simpan ke struktur data lokal untuk backup BM25
                all_chunks_data.append({
                    "id": chunk_id,
                    "text": chunk,
                    "source_file": pdf_file
                })
                
            total_chunks += len(chunks)
        except Exception as e:
            print(f"   ❌ Gagal memproses {pdf_file}: {e}")

    # Simpan salinan teks mentah untuk inisialisasi BM25 yang instan
    with open(CHUNKS_BACKUP_PATH, "w", encoding="utf-8") as f:
        json.dump(all_chunks_data, f, indent=4, ensure_ascii=False)
    
    print(f"\n🎉 DATABASE BERHASIL SELESAI DIBUAT!")
    print(f"📊 Total dokumen PDF terindeks: {len(pdf_files)}")
    print(f"📦 Total chunks tersimpan di database: {total_chunks}")
    print(f"💾 Backup teks untuk BM25 berhasil ditulis ke: '{CHUNKS_BACKUP_PATH}'")

if __name__ == "__main__":
    main()