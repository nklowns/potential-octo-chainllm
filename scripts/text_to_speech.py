#!/usr/bin/env python3
"""
Text-to-Speech Pipeline usando Piper TTS
Converte scripts de texto em áudio WAV
"""
import os
import sys
import time
import warnings
from pathlib import Path
from typing import Optional, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Suprimir warnings de SSL para ambiente de desenvolvimento com Traefik
warnings.filterwarnings('ignore', message='Unverified HTTPS request')


class TTSPipelineError(Exception):
    """Exceção base para erros do TTS Pipeline"""
    pass


class TTSConnectionError(TTSPipelineError):
    """Erro de conexão com TTS"""
    pass


class TTSPipeline:
    """Pipeline de conversão de texto para áudio usando Piper TTS"""

    # Configurações de retry
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # segundos
    TIMEOUT = 120  # segundos

    def __init__(self):
        # Configuração da URL do TTS
        self.tts_url = os.getenv('TTS_BASE_URL')
        if not self.tts_url:
            # Fallback para DNS interno Docker
            tts_service = os.getenv('TTS_SERVICE_NAME', 'piper-tts')
            tts_port = os.getenv('TTS_PORT', '5000')
            self.tts_url = f"http://{tts_service}:{tts_port}"

        self.scripts_dir = Path(os.getenv('OUTPUT_SCRIPTS', '/home/appuser/app/output/scripts'))
        self.audio_dir = Path(os.getenv('OUTPUT_AUDIO', '/home/appuser/app/output/audio'))
        self.audio_dir.mkdir(parents=True, exist_ok=True)

        # Configurar sessão com retry automático
        self.session = self._create_session()

        # Configurações de voz
        self.voice = os.getenv('TTS_VOICE', 'pt_BR-faber-medium')
        self.length_scale = float(os.getenv('TTS_LENGTH_SCALE', '1.0'))
        self.noise_scale = float(os.getenv('TTS_NOISE_SCALE', '0.667'))
        self.noise_w_scale = float(os.getenv('TTS_NOISE_W_SCALE', '0.8'))

        self.test_tts_connection()

    def _create_session(self) -> requests.Session:
        """Cria sessão HTTP com retry automático"""
        session = requests.Session()

        # Configurar retry strategy
        retry_strategy = Retry(
            total=self.MAX_RETRIES,
            backoff_factor=1,  # 1, 2, 4 segundos
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Para HTTPS via Traefik, não verificamos certificado em dev
        # Em produção, o Traefik gerencia os certificados corretamente
        if self.tts_url and self.tts_url.startswith('https'):
            session.verify = False

        return session

    def test_tts_connection(self) -> None:
        """Testa se o TTS está acessível"""
        try:
            response = self.session.get(
                f"{self.tts_url}/voices",
                timeout=10
            )
            response.raise_for_status()

            voices = response.json()
            print(f"✅ TTS conectado: {self.tts_url}")
            print(f"🗣️  Voz selecionada: {self.voice}")

            # Verificar se a voz existe
            voice_names = [v.get('name') for v in voices] if isinstance(voices, list) else []
            if voice_names and self.voice not in voice_names:
                print(f"⚠️  Voz '{self.voice}' pode não estar disponível")
                print(f"📋 Vozes disponíveis: {', '.join(voice_names[:3])}")

        except requests.exceptions.ConnectionError as e:
            raise TTSConnectionError(
                f"Não foi possível conectar ao TTS em {self.tts_url}. "
                f"Verifique se o serviço está rodando. Erro: {e}"
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise TTSConnectionError(
                    f"Endpoint /voices não encontrado em {self.tts_url}. "
                    f"Verifique a URL do TTS."
                )
            raise TTSConnectionError(f"Erro HTTP ao conectar ao TTS: {e}")
        except Exception as e:
            raise TTSConnectionError(f"Erro inesperado ao testar TTS: {e}")

    def load_scripts(self) -> List[Path]:
        """Carrega todos os scripts gerados"""
        scripts = sorted(self.scripts_dir.glob("script_*.txt"))
        print(f"🎵 Encontrados {len(scripts)} scripts para converter")
        return scripts

    def extract_script_text(self, filepath: Path) -> Optional[str]:
        """
        Extrai o texto do script do arquivo

        Args:
            filepath: Caminho do arquivo de script

        Returns:
            Texto do script ou None se não encontrado
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Filtrar linhas de comentário/metadados (iniciadas com #)
            text_lines = [
                line.strip()
                for line in lines
                if line.strip() and not line.strip().startswith('#')
            ]

            if not text_lines:
                return None

            return ' '.join(text_lines)

        except Exception as e:
            print(f"❌ Erro lendo {filepath.name}: {e}")
            return None

    def generate_audio(self, text: str, output_path: Path) -> bool:
        """
        Gera áudio a partir do texto usando Piper TTS

        Args:
            text: Texto para converter em áudio
            output_path: Caminho para salvar o arquivo WAV

        Returns:
            True se sucesso, False caso contrário
        """
        payload = {
            "text": text,
            "voice": self.voice,
            "length_scale": self.length_scale,
            "noise_scale": self.noise_scale,
            "noise_w_scale": self.noise_w_scale,
        }

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = self.session.post(
                    self.tts_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=self.TIMEOUT,
                    stream=True
                )
                response.raise_for_status()

                # Salvar áudio WAV
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                # Verificar se o arquivo foi criado e não está vazio
                if output_path.exists() and output_path.stat().st_size > 0:
                    return True
                else:
                    print(f"⚠️  Arquivo criado mas está vazio")
                    return False

            except requests.exceptions.Timeout:
                print(f"⏱️  Timeout (tentativa {attempt}/{self.MAX_RETRIES})")
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY * attempt)

            except requests.exceptions.HTTPError as e:
                print(f"❌ Erro HTTP {e.response.status_code} (tentativa {attempt}/{self.MAX_RETRIES}): {e}")
                if e.response.status_code >= 500 and attempt < self.MAX_RETRIES:
                    # Servidor com problema, tentar novamente
                    time.sleep(self.RETRY_DELAY * attempt)
                else:
                    # Erro do cliente (4xx) ou última tentativa
                    return False

            except requests.exceptions.ConnectionError as e:
                print(f"❌ Erro de conexão (tentativa {attempt}/{self.MAX_RETRIES}): {e}")
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY * attempt)

            except Exception as e:
                print(f"❌ Erro inesperado: {type(e).__name__}: {e}")
                return False

        print(f"❌ Falhou após {self.MAX_RETRIES} tentativas")
        return False

    def run(self) -> int:
        """
        Executa o pipeline de conversão texto-áudio

        Returns:
            Código de saída (0 = sucesso, 1 = falha)
        """
        try:
            script_files = self.load_scripts()
            if not script_files:
                print("❌ Nenhum script encontrado para converter")
                return 1

            success_count = 0
            start_time = time.time()

            for i, script_file in enumerate(script_files, 1):
                print(f"\n🔊 [{i}/{len(script_files)}] Convertendo: {script_file.name}")

                text = self.extract_script_text(script_file)
                if not text:
                    print(f"❌ Texto não encontrado em {script_file.name}")
                    continue

                audio_filename = script_file.stem + ".wav"
                audio_path = self.audio_dir / audio_filename

                if self.generate_audio(text, audio_path):
                    size_kb = audio_path.stat().st_size / 1024
                    print(f"✅ Áudio salvo: {audio_filename} ({size_kb:.1f} KB)")
                    success_count += 1
                else:
                    print(f"❌ Falha na conversão: {script_file.name}")

            elapsed = time.time() - start_time
            print(f"\n🎉 Concluído: {success_count}/{len(script_files)} áudios gerados")
            print(f"⏱️  Tempo total: {elapsed:.1f}s ({elapsed/len(script_files):.1f}s por áudio)")

            return 0 if success_count > 0 else 1

        except TTSPipelineError as e:
            print(f"❌ Erro: {e}")
            return 1
        except KeyboardInterrupt:
            print("\n⚠️  Processo interrompido pelo usuário")
            return 130
        except Exception as e:
            print(f"❌ Erro inesperado: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return 1


if __name__ == "__main__":
    tts_pipeline = TTSPipeline()
    sys.exit(tts_pipeline.run())
