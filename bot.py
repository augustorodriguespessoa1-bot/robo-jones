import threading
import io
import PIL.Image
from google import genai
import telebot
from flask import Flask

# Inicializa o servidor Web
app = Flask(__name__)

# Configurações de Acesso
TELEGRAM_TOKEN = "8567344691:AAFTRLThr6novIb-TEMWp2wHOEhQQjdwfro"
GEMINI_API_KEY = "AQ.Ab8RN6Jt55CA2_n4CRng_4-tDxnhDHPCvzPmSjcEjy9wsxDqJw"
MEU_TELEGRAM_ID = 8785567767  

client = genai.Client(api_key=GEMINI_API_KEY)
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Variável para guardar a resposta atual que o ESP32 vai buscar
ultima_resposta = "Nenhuma questao processada ainda."

# Rotas do Servidor para o ESP32 e para o Render
@app.route('/')
def home():
    return "Servidor do Jones rodando com sucesso!"

@app.route('/resposta', methods=['GET'])
def obter_resposta():
    return ultima_resposta

# Função de verificação de segurança
def usuario_autorizado(message):
    if message.from_user.id != MEU_TELEGRAM_ID:
        bot.reply_to(message, "Acesso negado. Este bot é privado.")
        return False
    return True

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if not usuario_autorizado(message):
        return
    bot.reply_to(message, "Olá! Envie uma foto da questão para eu resolver.")

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    global ultima_resposta
    if not usuario_autorizado(message):
        return
        
    try:
        bot.reply_to(message, "Processando a imagem, aguarde um instante...")
        
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        image = PIL.Image.open(io.BytesIO(downloaded_file))
        
        prompt_calculadora = """
        Você é um assistente para resolução de provas. Resolva a questão da imagem de forma completa, exata e passo a passo.

        REGRAS RÍGIDAS DE FORMATAÇÃO PARA DISPLAY PEQUENO:
        1. Divida a resposta estritamente em PÁGINAS usando o marcador [PAG X].
        2. Cada página deve ter no máximo 4 a 5 linhas curtas para caber na tela.
        
        REGRAS DE SIMBOLOGIA (USE APENAS TEXTO ASCII SIMPLES):
        - Integral: Use 'INT'
        - Somatório: Use 'SUM'
        - Raiz quadrada/n-ésima: Use 'sqrt()' ou 'root()'
        - Frações: Use parenteses e barra (Exemplo: (a + b) / (c - d))
        - Potência/Expoente: Use '^'
        - Letras Gregas: Escreva o nome por extenso (pi, theta, alpha, beta, etc)
        - Operadores Básicos: Use '*', '/', '+', '-', '=', '~='
        - Derivadas: Use 'df/dx' ou 'f'(x)'
        
        ESTRUTURA DAS PÁGINAS:
        - [PAG 1]: Enunciado resumido e dados/fórmulas principais.
        - [PAG 2, 3...]: Desenvolvimento passo a passo dos cálculos sem pular etapas.
        - [ÚLTIMA PAG]: Resposta final destacada de forma direta.

        PROIBIDO: Não use LaTeX, caracteres especiais, emojis ou Markdown (*, _).
        """
        
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=[prompt_calculadora, image]
        )
        
        # Salva o texto gerado na variável global do servidor para o ESP32 ler
        ultima_resposta = response.text
        
        # Envia de volta no Telegram também
        bot.reply_to(message, response.text)
    except Exception as e:
        bot.reply_to(message, f"Ocorreu um erro: {e}")

def rodar_bot():
    bot.infinity_polling()

# Inicia o Telegram em paralelo para o Render carregar o Flask sem travar
threading.Thread(target=rodar_bot, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)