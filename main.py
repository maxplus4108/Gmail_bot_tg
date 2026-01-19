import time
import datetime
from imap_tools import MailBox, AND
import requests
import os
import html # Нужно для защиты текста (чтобы спецсимволы не ломали HTML телеграма)
from bs4 import BeautifulSoup
from dotenv import load_dotenv
# --- НАСТРОЙКИ ---
load_dotenv()
GMAIL_USER = os.getenv('GMAIL_USER')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')
TG_BOT_TOKEN = os.getenv('TG_BOT_TOKEN')
TG_CHAT_ID = os.getenv('TG_CHAT_ID')

CHECK_INTERVAL = 30



def send_telegram(text):
    """Отправляет сообщение в Telegram"""
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TG_CHAT_ID,
        "text": text,
        "parse_mode": "HTML", 
        "disable_web_page_preview": True
    }
    try:
        response = requests.post(url, data=data)
        if response.status_code != 200:
            print(f"Ошибка Telegram: {response.text}")
    except Exception as e:
        print(f"Не удалось отправить в ТГ: {e}")

def send_telegram_photo(filename, image_data):
    """Отправляет фото"""
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendPhoto"
    data = {"chat_id": TG_CHAT_ID}
    
    # Telegram API требует передавать файл в специальном формате
    # (filename, image_data) - имя файла и сами байты картинки
    files = {'photo': (filename, image_data)}
    
    try:
        print(f" Загружаю фото: {filename}")
        response = requests.post(url, data=data, files=files)
        if response.status_code != 200:
            print(f"Ошибка отправки фото: {response.text}")
    except Exception as e:
        print(f"Не удалось отправить фото в ТГ: {e}")



def send_telegram_document(filename, file_data):
    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendDocument"
    data = {"chat_id": TG_CHAT_ID}
    files = {'document': (filename, file_data)}
    
    try:
        print(f" Загружаю документ: {filename}")
        requests.post(url, data=data, files=files, timeout=None)
    except Exception as e:
        print(f"Ошибка документа: {e}")


def get_clean_body(msg):
    """Извлекает чистый текст из письма, убирая HTML теги"""
    body = msg.text
    
    # Если текстовой версии нет, но есть HTML (как в письмах Cloud.ru)
    if not body and msg.html:
        try:
            soup = BeautifulSoup(msg.html, "html.parser")
            # get_text берет слова, separator="\n" делает переносы строк
            body = soup.get_text(separator="\n", strip=True)
        except Exception:
            body = "Не удалось распознать текст письма (сложный HTML)."
            
    if not body:
        body = "[Пустое тело письма или только картинка]"
        
    return body


def run_realtime_bot():
    print(f"Запуск: {datetime.datetime.now().strftime('%H:%M:%S')} ---")
    
    # Переменная для хранения номера последнего письма
    last_uid = 0
    
    # 1. Узнаем номер последнего письма в ящике прямо сейчас
    try:
        print("Получаю ID последнего письма...", end='')
        with MailBox('imap.gmail.com').login(GMAIL_USER, GMAIL_APP_PASSWORD) as mailbox:
            # Берем ровно 1 самое свежее письмо (limit=1, reverse=True)
            for msg in mailbox.fetch(limit=1, reverse=True):
                last_uid = int(msg.uid)
        print(f" OK. Последний ID: {last_uid}")
        
    except Exception as e:
        print(f"\n Ошибка при старте: {e}")
        return

   # 2. ЦИКЛ ПРОВЕРКИ
    while True:
        try:
            with MailBox('imap.gmail.com').login(GMAIL_USER, GMAIL_APP_PASSWORD) as mailbox:
                
                # Запрашиваем письма, начиная с последнего известного (last_uid) и новее
                # Синтаксис "ID:*" означает "от ID до конца"
                search_criteria = AND(uid=f"{last_uid}:*")
                
                for msg in mailbox.fetch(search_criteria, mark_seen=False):
                    
                    current_msg_uid = int(msg.uid)
                    
                    # === ВАША ПРОВЕРКА ===
                    # Если ID совпадает с тем, что мы уже видели — пропускаем
                    if current_msg_uid == last_uid:
                        continue 

                    # Если мы здесь, значит current_msg_uid > last_uid (это НОВОЕ письмо)
                    if current_msg_uid > last_uid:

                        # Обновляем счетчик
                        last_uid = current_msg_uid
                        # Подготовка данных (чистим от лишних символов)
                        sender = html.escape(msg.from_)
                        subject = html.escape(msg.subject)
                        # 1. Используем твою функцию очистки (она уже есть выше)
                        clean_text = get_clean_body(msg)

                        # 2. Обязательно экранируем результат (защита от спецсимволов)
                        safe_text = html.escape(clean_text)

                        # 3. Обрезаем, если текст гигантский
                        if len(safe_text) > 3000:
                            safe_text = safe_text[:3000] + "\n... (текст обрезан)"

                        # Сборка сообщения
                        tg_message = (
                        f"НОВОЕ СООБЩЕНИЕ (ID {current_msg_uid})\n"
                        f"От: {sender}\n"
                        f"<b>Тема: {(subject or 'Без темы')} </b>\n"
                        f"{'-' * 20}\n"
                        f"<blockquote expandable>{safe_text}</blockquote>"
                        )
                        send_telegram(tg_message)
                        
                        for att in msg.attachments:
                            # att.content_type содержит тип файла
                            if 'image' in att.content_type:
                                send_telegram_photo(att.filename, att.payload)
                            else:
                            # ЛЮБОЙ другой файл отправляем как документ (PDF, архивы, текстовые и т.д.)
                                send_telegram_document(att.filename, att.payload)
                            time.sleep(1)
                    print (f"Последний ID сообщения {last_uid}")

        except Exception as e:
            print(f"\n Ошибка: {e}")
            time.sleep(5)
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        run_realtime_bot()
    except KeyboardInterrupt:
        print("\n Бот остановлен.")