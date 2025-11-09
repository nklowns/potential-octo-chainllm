#!/usr/bin/env python3
import requests
import json
import os
import sys
from pathlib import Path
from urllib.parse import urljoin

class ScriptGenerator:
    def __init__(self):
        self.ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.api_url = f"{self.ollama_url}/api/generate"
        self.model = os.getenv('OLLAMA_MODEL', 'gemma3:4b')
        self.input_file = os.getenv('INPUT_FILE', '/home/appuser/app/input/topics.txt')
        self.output_dir = Path(os.getenv('OUTPUT_SCRIPTS', '/home/appuser/app/output/scripts'))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Headers para HTTPS se necessário
        self.session = requests.Session()
        if self.ollama_url.startswith('https'):
            self.session.verify = False  # Apenas para desenvolvimento

        self.test_ollama_connection()

    def test_ollama_connection(self):
        """Testa se o Ollama está acessível"""
        try:
            response = self.session.get(f"{self.ollama_url}/api/tags", timeout=10)
            if response.status_code == 200:
                print(f"✅ Ollama conectado: {self.ollama_url}")
            else:
                print(f"❌ Ollama retornou status {response.status_code}")
                sys.exit(1)
        except Exception as e:
            print(f"❌ Erro conectando ao Ollama: {e}")
            sys.exit(1)

    def load_topics(self):
        """Carrega tópicos do arquivo de input"""
        topics_file = Path(self.input_file)
        if not topics_file.exists():
            print(f"❌ Arquivo de tópicos não encontrado: {topics_file}")
            return []

        with open(topics_file, 'r', encoding='utf-8') as f:
            topics = [line.strip() for line in f if line.strip()]

        print(f"📝 Carregados {len(topics)} tópicos de {topics_file}")
        return topics

    def generate_script(self, topic):
        """Gera roteiro usando Ollama externo"""
        prompt = f"""
        Crie um roteiro para um vídeo curto de 30 segundos sobre: {topic}

        REQUISITOS:
        - Duração exata: 30 segundos
        - Linguagem natural e conversacional
        - Frases curtas e impactantes
        - Máximo 120 palavras
        - Estrutura: Introdução (5s), Desenvolvimento (20s), Conclusão (5s)

        Retorne APENAS o texto do narrador, sem marcações.
        """

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_k": 40,
                "top_p": 0.9
            }
        }

        try:
            response = self.session.post(self.api_url, json=payload, timeout=120)
            response.raise_for_status()
            return response.json()['response'].strip()
        except Exception as e:
            print(f"❌ Erro ao gerar script para '{topic}': {e}")
            return None

    def save_script(self, topic, script, index):
        """Salva o script gerado"""
        safe_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"script_{index:03d}_{safe_topic[:20]}.txt"
        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"TÓPICO: {topic}\n")
            f.write(f"OLLAMA_URL: {self.ollama_url}\n")
            f.write(f"SCRIPT:\n{script}\n")

        return filepath

    def run(self):
        """Executa o pipeline de geração de scripts"""
        topics = self.load_topics()
        if not topics:
            print("❌ Nenhum tópico para processar")
            return

        print(f"🎯 Processando {len(topics)} tópicos...")

        success_count = 0
        for i, topic in enumerate(topics, 1):
            print(f"\n📝 [{i}/{len(topics)}] Gerando: {topic}")

            script = self.generate_script(topic)
            if script:
                saved_path = self.save_script(topic, script, i)
                print(f"✅ Salvo: {saved_path.name}")
                success_count += 1
            else:
                print(f"❌ Falha: {topic}")

        print(f"\n🎉 Concluído: {success_count}/{len(topics)} scripts gerados")

if __name__ == "__main__":
    generator = ScriptGenerator()
    generator.run()