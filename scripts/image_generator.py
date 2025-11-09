import os
import requests
import time
import json
from logging import getLogger, basicConfig, INFO

# Configuração do logging
basicConfig(level=INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = getLogger(__name__)

# Variáveis de ambiente
SD_API_URL = os.getenv("SD_API_URL", "http://stable-diffusion-api:7860/sdapi/v1/txt2img")
SCRIPTS_DIR = os.getenv("SCRIPTS_DIR", "/home/appuser/app/output/scripts")
IMAGES_DIR = os.getenv("IMAGES_DIR", "/home/appuser/app/output/images")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 10))

def check_service_health(url):
    """Verifica se o serviço de Stable Diffusion está disponível."""
    try:
        response = requests.get(url.replace("/sdapi/v1/txt2img", "/"), timeout=5)
        if response.status_code == 200:
            logger.info("✅ Serviço de Stable Diffusion está disponível.")
            return True
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Serviço de Stable Diffusion indisponível: {e}")
    return False

def generate_image_from_prompt(prompt, script_name):
    """Gera uma imagem a partir de um prompt usando a API do Stable Diffusion."""
    payload = {
        "prompt": prompt,
        "steps": 25,
        "cfg_scale": 7,
        "width": 1024,
        "height": 1024,
        "sampler_name": "DPM++ 2M Karras"
    }

    try:
        start_time = time.time()
        logger.info(f"🖼️ Gerando imagem para o script: {script_name}...")
        response = requests.post(url=SD_API_URL, json=payload, timeout=300)
        response.raise_for_status()

        r = response.json()
        image_data = r['images'][0]

        output_path = os.path.join(IMAGES_DIR, f"{script_name}.png")
        with open(output_path, 'wb') as f:
            import base64
            f.write(base64.b64decode(image_data))

        end_time = time.time()
        generation_time = end_time - start_time

        logger.info(f"✅ Imagem gerada com sucesso: {output_path}")
        logger.info(f"⏱️ Tempo de geração: {generation_time:.2f} segundos.")

        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Erro ao chamar a API do Stable Diffusion: {e}")
    except (KeyError, IndexError) as e:
        logger.error(f"❌ Erro ao processar a resposta da API: {e}")
    except Exception as e:
        logger.error(f"❌ Erro inesperado ao gerar imagem: {e}")

    return False

def extract_prompt_from_script(file_path):
    """Extrai a primeira linha não vazia de um script como prompt."""
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                return line.strip()
    return None

def main():
    """Função principal para orquestrar a geração de imagens."""
    logger.info("🚀 Iniciando processo de geração de imagens...")

    if not check_service_health(SD_API_URL):
        logger.error("Encerrando devido à indisponibilidade do serviço. Tente novamente mais tarde.")
        return

    os.makedirs(IMAGES_DIR, exist_ok=True)

    while True:
        logger.info(f"🔍 Verificando scripts em {SCRIPTS_DIR}...")
        scripts = [f for f in os.listdir(SCRIPTS_DIR) if f.endswith('.txt')]

        if not scripts:
            logger.info("Nenhum script encontrado. Aguardando...")
            time.sleep(POLL_INTERVAL)
            continue

        for script_file in scripts:
            script_path = os.path.join(SCRIPTS_DIR, script_file)
            image_name = os.path.splitext(script_file)[0]
            image_path = os.path.join(IMAGES_DIR, f"{image_name}.png")

            if os.path.exists(image_path):
                logger.info(f"⏭️ Imagem para '{script_file}' já existe. Pulando.")
                continue

            prompt = extract_prompt_from_script(script_path)
            if prompt:
                logger.info(f"✨ Encontrado prompt para '{script_file}': '{prompt[:50]}...'")
                generate_image_from_prompt(prompt, image_name)
            else:
                logger.warning(f"⚠️ Script '{script_file}' está vazio ou não contém prompt.")

        logger.info(f"🏁 Ciclo de verificação concluído. Próxima verificação em {POLL_INTERVAL} segundos.")
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
