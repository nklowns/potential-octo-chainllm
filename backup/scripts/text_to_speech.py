#!/usr/bin/env python3
import requests
import os
import sys
from pathlib import Path

class TTSPipeline:
    def __init__(self):
        # Usar TTS_BASE_URL do .env (via Traefik) ou fallback para DNS interno
        self.tts_url = os.getenv('TTS_BASE_URL')
        if not self.tts_url:
            # Fallback para DNS interno (apenas se no mesmo docker-compose)
            tts_service = os.getenv('TTS_SERVICE_NAME', 'piper-tts')
            tts_port = os.getenv('TTS_PORT', '5000')
            self.tts_url = f"http://{tts_service}:{tts_port}"

        self.scripts_dir = Path(os.getenv('OUTPUT_SCRIPTS', '/home/appuser/app/output/scripts'))
        self.audio_dir = Path(os.getenv('OUTPUT_AUDIO', '/home/appuser/app/output/audio'))
        self.audio_dir.mkdir(parents=True, exist_ok=True)

        self.test_tts_connection()

    def test_tts_connection(self):
        """Testa se o TTS está acessível"""
        try:
            # Teste de conectividade via /voices endpoint
            response = requests.get(f"{self.tts_url}/voices", timeout=10)
            response.raise_for_status()
            print(f"✅ TTS conectado: {self.tts_url}")
        except Exception as e:
            print(f"❌ Erro conectando ao TTS ({self.tts_url}): {e}")
            print("💡 Verifique se TTS_BASE_URL está correto no .env")
            print("💡 Ou se o serviço está acessível via Traefik")
            sys.exit(1)

    def load_scripts(self):
        """Carrega todos os scripts gerados"""
        scripts = list(self.scripts_dir.glob("script_*.txt"))
        print(f"🎵 Encontrados {len(scripts)} scripts para converter")
        return scripts

    def extract_script_text(self, filepath):
        """Extrai o texto do script do arquivo"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                if "SCRIPT:" in content:
                    script_part = content.split("SCRIPT:")[1].strip()
                    return script_part
            return None
        except Exception as e:
            print(f"❌ Erro lendo {filepath}: {e}")
            return None

    def generate_audio(self, text, output_path):
        """Gera áudio a partir do texto usando Piper TTS (nova API HTTP v1.3.1)"""
        try:
            # Nova API HTTP (OHF-Voice/piper1-gpl v1.3.1)
            # POST / com JSON payload
            payload = {
                "text": text,
                "voice": "pt_BR-faber-medium",  # Especificar voz explicitamente
                "length_scale": 1.0,  # Velocidade normal
                "noise_scale": 0.667,  # Variabilidade de áudio
                "noise_w_scale": 0.8,  # Variabilidade de fonemas
            }

            response = requests.post(
                self.tts_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=120,
                stream=True
            )
            response.raise_for_status()

            # Salvar áudio WAV
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            return True
        except Exception as e:
            print(f"❌ Erro gerando áudio: {e}")
            print(f"💡 URL: {self.tts_url}")
            return False

    def run(self):
        """Executa o pipeline de conversão texto-áudio"""
        script_files = self.load_scripts()
        if not script_files:
            print("❌ Nenhum script encontrado para converter")
            return

        success_count = 0
        for script_file in script_files:
            print(f"\n🔊 Convertendo: {script_file.name}")

            text = self.extract_script_text(script_file)
            if not text:
                print(f"❌ Texto não encontrado em {script_file.name}")
                continue

            audio_filename = script_file.stem + ".wav"
            audio_path = self.audio_dir / audio_filename

            success = self.generate_audio(text, audio_path)
            if success:
                print(f"✅ Áudio salvo: {audio_filename}")
                success_count += 1
            else:
                print(f"❌ Falha na conversão: {script_file.name}")

        print(f"\n🎉 Concluído: {success_count}/{len(script_files)} áudios gerados")

if __name__ == "__main__":
    tts_pipeline = TTSPipeline()
    tts_pipeline.run()