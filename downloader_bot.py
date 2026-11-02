import telebot
import yt_dlp
import os

TOKEN = os.environ.get('BOT_TOKEN_DOWNLOADER')
bot = telebot.TeleBot(TOKEN)

DOWNLOAD_DIR = 'downloads'
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Здарова. Кидай ссылку на видео или трек из ВК, я скачаю.")

@bot.message_handler(func=lambda message: True)
def download_media(message):
    url = message.text
    if not url.startswith('http'):
        bot.reply_to(message, "Это не похоже на ссылку, брат. Кидай нормальный URL.")
        return

    msg = bot.reply_to(message, "Качаю, подожди...")
    
    try:
        # Настройки: если ссылка на ВК, качаем только аудио
        ydl_opts = {
            'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
            'quiet': True,
        }

        if 'vk.com' in url or 'vk.ru' in url:
            # Для ВК просим только аудио в mp3
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        else:
            # Для остальных (Инста, ТикТок) качаем видео
            ydl_opts['format'] = 'best[ext=mp4]/best'

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # Если это было аудио, yt-dlp меняет расширение на .mp3
            if 'vk.com' in url or 'vk.ru' in url:
                filename = os.path.splitext(filename)[0] + '.mp3'
                with open(filename, 'rb') as audio:
                    bot.send_audio(message.chat.id, audio, caption="Держи трек, братуха.")
            else:
                with open(filename, 'rb') as video:
                    bot.send_video(message.chat.id, video, caption="Держи, братуха.")
        
        os.remove(filename)
        bot.delete_message(message.chat.id, msg.message_id)
        
    except Exception as e:
        bot.edit_message_text(f"Ошибка: {e}", message.chat.id, msg.message_id)

if __name__ == '__main__':
    print("Бот-качальщик запущен...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
