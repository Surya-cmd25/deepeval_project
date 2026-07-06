# generate_charts.py
import json
import os
import time
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 📁 INPUT PATH (Menyesuaikan dengan lokasi di folder 'hasil_evaluasi')
INPUT_FILENAME = "hasil_evaluasi_1/hasil_evaluasi_skenario_1.json"

# 📁 CONFIG FOLDER INDUK & ANAK
BASE_OUTPUT_FOLDER = "grafik_evaluasi"

def create_graphics():
    if not os.path.exists(INPUT_FILENAME):
        print(f"❌ File {INPUT_FILENAME} tidak ditemukan!")
        return

    # 1. Membuat sub-folder dinamis di dalam 'grafik_evaluasi' berdasarkan timestamp saat running
    timestamp_folder = time.strftime("run_%Y%m%d_%H%M%S")
    target_output_folder = os.path.join(BASE_OUTPUT_FOLDER, timestamp_folder)
    
    # Membuat folder berjenjang jika belum ada (grafik_evaluasi/run_xxxxxxxx_xxxxxx/)
    if not os.path.exists(target_output_folder):
        os.makedirs(target_output_folder)
        print(f"📁 Folder baru berhasil dibuat: '{target_output_folder}'")

    # 2. Load Data JSON
    with open(INPUT_FILENAME, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    detail_data = data.get("detail_perbandingan", [])
    df = pd.DataFrame(detail_data)
    
    # Ekstrak data evaluasi
    df['skor_aktual'] = df['evaluasi'].apply(lambda x: x.get('skor_aktual', 0.0))
    df['status'] = df['evaluasi'].apply(lambda x: x.get('status', 'FAILED'))
    
    # Rumus Kalkulasi Tingkat Halusinasi (%)
    df['hallucination_rate'] = (1.0 - df['skor_aktual']) * 100
    df['hallucination_rate'] = df['hallucination_rate'].clip(lower=0)

    print(f"📈 Memproses {len(df)} data soal untuk dijadikan grafik...")
    sns.set_theme(style="whitegrid")
    
    # =========================================================================
    # GRAFIK 1: Tren Skor Kedekatan Makna per Nomor Soal (Line Chart)
    # =========================================================================
    plt.figure(figsize=(14, 5))
    plt.plot(df['no_soal'], df['skor_aktual'], marker='o', color='#1f77b4', linestyle='-', linewidth=1.5, markersize=4, label='Skor Aktual AI')
    plt.axhline(y=0.85, color='#d62728', linestyle='--', linewidth=1.5, label='Threshold Kelulusan (0.85)')
    
    plt.title('Tren Skor Semantic Similarity per Nomor Soal (Gemma 4)', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('Nomor Soal', fontsize=12)
    plt.ylabel('Skor Kedekatan Makna (0.0 - 1.0)', fontsize=12)
    plt.ylim(0, 1.05)
    plt.legend(loc='lower left')
    plt.tight_layout()
    plt.savefig(os.path.join(target_output_folder, '1_tren_skor_akurasi.png'), dpi=300)
    plt.close()

    # =========================================================================
    # GRAFIK 2: Tren Tingkat Halusinasi AI per Nomor Soal (Area & Line Chart)
    # =========================================================================
    plt.figure(figsize=(14, 5))
    plt.fill_between(df['no_soal'], df['hallucination_rate'], color='#e74c3c', alpha=0.3, label='Area Halusinasi/Deviasi')
    plt.plot(df['no_soal'], df['hallucination_rate'], color='#c0392b', linewidth=1.5, marker='x', markersize=4, label='Tingkat Halusinasi (%)')
    plt.axhline(y=15.0, color='#2c3e50', linestyle=':', linewidth=1.5, label='Batas Toleransi Eror (15%)')
    
    plt.title('Analisis Tingkat Halusinasi (Hallucination Rate) per Nomor Soal', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('Nomor Soal', fontsize=12)
    plt.ylabel('Persentase Deviasi / Halusinasi (%)', fontsize=12)
    plt.ylim(-2, 105)
    plt.legend(loc='upper right')
    plt.tight_layout()
    plt.savefig(os.path.join(target_output_folder, '2_analisis_halusinasi.png'), dpi=300)
    plt.close()

    # =========================================================================
    # GRAFIK 3: Distribusi Status Hasil Pengujian PASSED vs FAILED (Pie Chart)
    # =========================================================================
    status_counts = df['status'].value_counts()
    plt.figure(figsize=(6, 6))
    colors = ['#2ecc71', '#e74c3c'] if status_counts.index[0] == 'PASSED' else ['#e74c3c', '#2ecc71']
    
    plt.pie(status_counts, labels=status_counts.index, autopct='%1.1f%%', startangle=140, colors=colors, 
            wedgeprops={'edgecolor': 'white', 'linewidth': 2}, textprops={'fontsize': 12, 'weight': 'bold'})
    
    plt.title('Persentase Status Kelulusan Soal Skenario 1', fontsize=14, fontweight='bold', pad=15)
    plt.tight_layout()
    plt.savefig(os.path.join(target_output_folder, '3_pie_status_kelulusan.png'), dpi=300)
    plt.close()

    # =========================================================================
    # GRAFIK 4: Distribusi Waktu Respons AI (Histogram)
    # =========================================================================
    plt.figure(figsize=(10, 5))
    sns.histplot(df['response_time'], kde=True, color='teal', bins=15)
    
    plt.title('Distribusi Kecepatan Waktu Respons Gemma 4', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('Response Time (Detik)', fontsize=12)
    plt.ylabel('Frekuensi (Jumlah Soal)', fontsize=12)
    plt.tight_layout()
    plt.savefig(os.path.join(target_output_folder, '4_distribusi_waktu_respons.png'), dpi=300)
    plt.close()

    print(f"✨ BERHASIL! Seluruh grafik sesi ini disimpan di: '{target_output_folder}/'")

if __name__ == "__main__":
    create_graphics()