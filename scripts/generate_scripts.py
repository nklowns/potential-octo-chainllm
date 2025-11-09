#!/usr/bin/env python3
"""
Script Generator usando Ollama
Gera roteiros de vídeo a partir de tópicos usando LLMs via Ollama
"""
import os
import sys
import time
from pathlib import Path
from typing import Optional, List
import warnings

# Suprimir warnings de SSL para ambiente de desenvolvimento
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

try:
    from ollama import Client, ResponseError
except ImportError:
    print("❌ Biblioteca 'ollama' não encontrada. Instalando...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "ollama>=0.4.0"])
    from ollama import Client, ResponseError


class ScriptGeneratorError(Exception):
    """Exceção base para erros do ScriptGenerator"""
    pass


class OllamaConnectionError(ScriptGeneratorError):
    """Erro de conexão com Ollama"""
    pass


class ModelNotFoundError(ScriptGeneratorError):
    """Modelo não encontrado"""
    pass


class ScriptGenerator:
    """Gerador de scripts usando Ollama"""

    # Configurações de retry
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # segundos
    TIMEOUT = 120  # segundos

    def __init__(self):
        self.ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        self.model = os.getenv('OLLAMA_MODEL', 'gemma3:4b')
        self.input_file = os.getenv('INPUT_FILE', '/home/appuser/app/input/topics.txt')
        self.output_dir = Path(os.getenv('OUTPUT_SCRIPTS', '/home/appuser/app/output/scripts'))
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Configurar cliente Ollama com timeout
        # Para HTTPS via Traefik, não precisamos configurar SSL pois o Traefik já gerencia
        self.client = Client(
            host=self.ollama_url,
            timeout=self.TIMEOUT
        )

        self.test_ollama_connection()

    def test_ollama_connection(self) -> None:
        """Testa se o Ollama está acessível e o modelo existe"""
        try:
            # Testar conexão listando modelos
            response = self.client.list()
            print(f"✅ Ollama conectado: {self.ollama_url}")

            # Verificar se o modelo existe
            # A resposta tem um atributo 'models' que é uma lista de objetos Model
            models_list = getattr(response, 'models', [])
            model_names = [getattr(m, 'model', '') for m in models_list]

            if self.model not in model_names:
                print(f"⚠️  Modelo '{self.model}' não encontrado")
                if model_names:
                    print(f"📥 Modelos disponíveis: {', '.join(model_names[:5])}")
                print(f"💡 Puxando modelo '{self.model}'...")
                try:
                    self.client.pull(self.model)
                    print(f"✅ Modelo '{self.model}' baixado com sucesso")
                except ResponseError as e:
                    raise ModelNotFoundError(
                        f"Não foi possível baixar o modelo '{self.model}': {e.error}"
                    )
            else:
                print(f"✅ Modelo '{self.model}' disponível")

        except ConnectionError as e:
            raise OllamaConnectionError(
                f"Não foi possível conectar ao Ollama em {self.ollama_url}. "
                f"Verifique se o serviço está rodando. Erro: {e}"
            )
        except ResponseError as e:
            if e.status_code == 404:
                raise OllamaConnectionError(
                    f"Endpoint não encontrado em {self.ollama_url}. "
                    f"Verifique a URL do Ollama."
                )
            raise OllamaConnectionError(f"Erro ao conectar ao Ollama: {e.error}")

    def load_topics(self) -> List[str]:
        """Carrega tópicos do arquivo de input"""
        topics_file = Path(self.input_file)
        if not topics_file.exists():
            print(f"❌ Arquivo de tópicos não encontrado: {topics_file}")
            return []

        with open(topics_file, 'r', encoding='utf-8') as f:
            topics = [line.strip() for line in f if line.strip() and not line.startswith('#')]

        print(f"📝 Carregados {len(topics)} tópicos de {topics_file}")
        return topics

    def generate_script(self, topic: str) -> Optional[str]:
        """
        Gera roteiro usando Ollama com retry automático

        Args:
            topic: Tópico do vídeo

        Returns:
            Script gerado ou None em caso de falha
        """
        prompt = self._build_prompt(topic)

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                response = self.client.generate(
                    model=self.model,
                    prompt=prompt,
                    options={
                        'temperature': 0.7,
                        'top_k': 40,
                        'top_p': 0.9,
                        'num_predict': 150  # Limita tamanho da resposta
                    }
                )
                return response['response'].strip()

            except ResponseError as e:
                if e.status_code == 404:
                    print(f"⚠️  Modelo não encontrado, tentando pull...")
                    try:
                        self.client.pull(self.model)
                        continue  # Tentar novamente após pull
                    except Exception as pull_error:
                        print(f"❌ Erro ao fazer pull do modelo: {pull_error}")
                        return None

                print(f"❌ Erro Ollama (tentativa {attempt}/{self.MAX_RETRIES}): {e.error}")

                if attempt < self.MAX_RETRIES:
                    delay = self.RETRY_DELAY * attempt  # Exponential backoff
                    print(f"⏳ Aguardando {delay}s antes de tentar novamente...")
                    time.sleep(delay)
                else:
                    print(f"❌ Falhou após {self.MAX_RETRIES} tentativas")
                    return None

            except ConnectionError as e:
                print(f"❌ Erro de conexão (tentativa {attempt}/{self.MAX_RETRIES}): {e}")
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY * attempt)
                else:
                    return None

            except Exception as e:
                print(f"❌ Erro inesperado: {type(e).__name__}: {e}")
                return None

        return None

    def _build_prompt(self, topic: str) -> str:
        """Constrói o prompt para geração do script"""
        return f"""Crie um roteiro para um vídeo curto de 60 segundos sobre: {topic}

REQUISITOS:
- Duração exata: 60 segundos
- Linguagem natural e conversacional em português brasileiro
- Frases curtas e impactantes
- Máximo 160 palavras
- Estrutura: Introdução (5s), Desenvolvimento (20s), Conclusão (5s)

Retorne APENAS o texto do narrador, sem marcações, títulos ou formatação extra."""

    def save_script(self, topic: str, script: str, index: int) -> Path:
        """Salva o script gerado em arquivo"""
        safe_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"script_{index:03d}_{safe_topic[:20]}.txt"
        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# Tópico: {topic}\n")
            f.write(f"# Modelo: {self.model}\n")
            f.write(f"# Ollama: {self.ollama_url}\n")
            f.write(f"# Gerado em: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"\n{script}\n")

        return filepath

    def run(self) -> int:
        """
        Executa o pipeline de geração de scripts

        Returns:
            Código de saída (0 = sucesso, 1 = falha)
        """
        try:
            topics = self.load_topics()
            if not topics:
                print("❌ Nenhum tópico para processar")
                return 1

            print(f"🎯 Processando {len(topics)} tópicos...")
            print(f"🤖 Modelo: {self.model}")
            print(f"📁 Output: {self.output_dir}\n")

            success_count = 0
            start_time = time.time()

            for i, topic in enumerate(topics, 1):
                print(f"📝 [{i}/{len(topics)}] Gerando: {topic}")

                script = self.generate_script(topic)
                if script:
                    saved_path = self.save_script(topic, script, i)
                    word_count = len(script.split())
                    print(f"✅ Salvo: {saved_path.name} ({word_count} palavras)")
                    success_count += 1
                else:
                    print(f"❌ Falha: {topic}")

                print()  # Linha em branco

            elapsed = time.time() - start_time
            print(f"🎉 Concluído: {success_count}/{len(topics)} scripts gerados")
            print(f"⏱️  Tempo total: {elapsed:.1f}s ({elapsed/len(topics):.1f}s por script)")

            return 0 if success_count > 0 else 1

        except ScriptGeneratorError as e:
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
    generator = ScriptGenerator()
    sys.exit(generator.run())
