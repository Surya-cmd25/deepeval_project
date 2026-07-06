# openrouter_provider.py
import os
import requests
from dotenv import load_dotenv
from deepeval.models import DeepEvalBaseLLM

# Gunakan override=True agar memastikan environment variable sistem dipaksa menggunakan isi file .env terbaru
load_dotenv(override=True)

class OpenRouterLLM(DeepEvalBaseLLM):
    # Mengganti default model ke Llama 3.3 70B Instruct Free
    def __init__(self, model_name="google/gemma-4-26b-a4b-it:free"):
        self.model_name = model_name
        
        # Ambil API key
        raw_key = os.getenv("OPENROUTER_API_KEY")
        
        if not raw_key:
            raise ValueError("❌ ERROR: OPENROUTER_API_KEY tidak ditemukan di environment variable atau file .env!")
            
        # KUNCI PERBAIKAN: Membersihkan karakter pengotor seperti tanda bintang (*), tanda kutip, atau spasi gaib
        self.api_key = raw_key.strip().replace("*", "").replace('"', '').replace("'", "")
        
        # Validasi format dasar token OpenRouter (biasanya diawali sk-or-v1-)
        if not self.api_key.startswith("sk-or-v1-"):
            raise ValueError(f"❌ ERROR: Format API Key salah! Key harus diawali 'sk-or-v1-'. Yang terbaca: {self.api_key[:12]}...")

        self.url = "https://openrouter.ai/api/v1/chat/completions"

    def load_model(self):
        return self.model_name

    def generate(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",  # Baik digunakan untuk kestabilan OpenRouter
            "X-Title": "MajaAIEval"
        }
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=60) 
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                return f"Error OpenRouter ({response.status_code}): {response.text}"
        except Exception as e:
            return f"Error Koneksi: {str(e)}"

    async def a_generate(self, prompt: str) -> str:
        return self.generate(prompt)

    def get_model_name(self) -> str:
        return self.model_name