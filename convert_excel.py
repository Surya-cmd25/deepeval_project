# convert_excel.py
import pandas as pd
import json
import os

EXCEL_PATH = "dataset/dataset_maja_ai_3.xlsx"
JSON_OUTPUT_PATH = "dataset/dataset_maja_ai_3.json"

def convert():
    if not os.path.exists(EXCEL_PATH):
        print(f"❌ File {EXCEL_PATH} tidak ditemukan!")
        return
        
    try:
        # Membaca excel (Sheet1)
        try:
            df = pd.read_excel(EXCEL_PATH, sheet_name="Sheet1")
        except Exception:
            df = pd.read_excel(EXCEL_PATH, sheet_name=0)
            
        df.columns = df.columns.str.strip().str.lower()
        
        kolom_no = 'no' if 'no' in df.columns else None
        kolom_query = 'query' if 'query' in df.columns else None
        kolom_expected = 'expected_output' if 'expected_output' in df.columns else None
        kolom_type = 'query_type' if 'query_type' in df.columns else ('type' if 'type' in df.columns else None)
        
        if not kolom_expected:
            for col in df.columns:
                if 'expected' in col or 'truth' in col or 'jawaban' in col:
                    kolom_expected = col
                    break

        if not kolom_query or not kolom_expected:
            print("❌ Kolom 'Query' atau 'Expected_output' tidak ditemukan!")
            return

        df = df.rename(columns={kolom_query: 'Query', kolom_expected: 'Expected_output'})
        if kolom_type:
            df = df.rename(columns={kolom_type: 'Query_type'})
        if kolom_no:
            df = df.rename(columns={kolom_no: 'No_soal'})
        
        df = df.dropna(subset=['Query', 'Expected_output'])
        
        # Format ke bentuk list of dictionary dengan metadata lengkap
        dataset_list = []
        for idx, row in df.iterrows():
            # Ambil nomor dari kolom Excel, jika kosong gunakan indeks baris + 1
            n_soal = int(row['No_soal']) if 'No_soal' in df.columns and pd.notna(row['No_soal']) else (idx + 1)
            q_type = str(row['Query_type']).strip() if 'Query_type' in df.columns else "Umum"
            
            dataset_list.append({
                "no_soal": n_soal,
                "query": str(row['Query']).strip(),
                "query_type": q_type,
                "expected_output": str(row['Expected_output']).strip()
            })
            
        with open(JSON_OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(dataset_list, f, indent=4, ensure_ascii=False)
            
        print(f"✅ BERHASIL! Mengonversi {len(dataset_list)} soal ke '{JSON_OUTPUT_PATH}' lengkap dengan Nomor Soal dan Tipe Query.")
        
    except Exception as e:
        print(f"❌ Gagal konversi: {e}")

if __name__ == "__main__":
    convert()