from telethon.errors import PhoneNumberBannedError, PasswordHashInvalidError, UsernameInvalidError
from telethon.types import DocumentAttributeFilename, InputMediaUploadedPhoto
from telethon.sync import TelegramClient, events
import os
import re

from config import (API_ID,
                    API_HASH,
                    PHONE_NUMBER,
                    CHANNELS_COPY,
                    CHANNEL_PASTE,
                    DEVICE_MODEL,
                    SYSTEM_VERSION,
                    AUTO_DELETE_LINKS,
                    FORWARDS)

logo = """
█▀▀ █▀█ █▀█ █▄█ ▄▄ █▀█ ▄▀█ █▀ ▀█▀ █▀▀   █▄▄ █▀█ ▀█▀|ᵇʸ ᵈᵉˡᵃᶠᵃᵘˡᵗ
█▄▄ █▄█ █▀▀ ░█░ ░░ █▀▀ █▀█ ▄█ ░█░ ██▄   █▄█ █▄█ ░█░"""

last_id_message = []

def gd_print(value):
    green_color = '\033[32m'
    reset_color = '\033[0m'
    result = f"\n>{green_color} {value} {reset_color}\n"
    print(result)

def bd_print(value):
    red_color = '\033[31m'
    reset_color = '\033[0m'
    result = f"\n>{red_color} {value} {reset_color}\n"
    print(result)

async def check_caption(caption): # Проверка текста на наличие ссылок и работа с ними
    if AUTO_DELETE_LINKS is False:
        return caption
    elif AUTO_DELETE_LINKS is True:
        return re.sub(r'<a\s[^>]*>.*?</a>', '', caption)
    elif AUTO_DELETE_LINKS is None:
        return re.sub(r'<a\s[^>]*>(.*?)</a>', r'\1', caption)
    elif AUTO_DELETE_LINKS not in [True, False, None]:
        return re.sub(r'<a\s+(?:[^>]*?\s+)?href="([^"]*)"(?:[^>]*)>(.*?)</a>', rf'<a href="{AUTO_DELETE_LINKS}">\2</a>', caption)

client = TelegramClient(
    session = f"tg_{PHONE_NUMBER}",
    api_id = API_ID,
    api_hash = API_HASH,
    device_model = DEVICE_MODEL,
    system_version = SYSTEM_VERSION
) # Создание клиента

@client.on(events.Album(CHANNELS_COPY)) # Альбомы не поддерживают по дефолту 'forward', поэтому придётся обрабатывать это отдельно.
async def handler(event):
    """
    Обработка альбомов
    """
    if FORWARDS is True:
        if event.messages[0].fwd_from:
            pass
        else:
            return
    elif FORWARDS is False:
        if event.messages[0].fwd_from:
            return

    media = []
    caption = event.messages[0].text
    force_document = False
    id = event.messages[0].id
    if id in last_id_message:
        last_id_message.clear()
        return # Album почему-то иногда получает ивент дважды на одно сообщение.
    last_id_message.append(id)

    caption = await check_caption(caption)

    gd_print(f"Получили альбом из {len(event)} сообщений.")

    for group_message in event.messages: # Да, spoiler для альбомов в теории можно реализовать, однако сделать это не так просто, как кажется. Плюсом занимало бы много времени на обработку.
        if group_message.photo:
            media.append(await client.download_media(group_message, f"temp_pics/{group_message.id}.png"))
        elif group_message.video:
            media.append(await client.download_media(group_message, f"temp_pics/{group_message.id}.mp4"))
        elif group_message.document:
            file_name = next((x.file_name for x in group_message.document.attributes if isinstance(x, DocumentAttributeFilename)), None)
            media.append(await client.download_media(group_message, f"temp_pics/{file_name}"))
            force_document = True
        else:
            return bd_print("Неизвестный тип сообщения")

    await client.send_file(CHANNEL_PASTE, media, caption=caption, force_document=force_document)
    gd_print(f"Скопировали и успешно отправили альбом из {len(event)} сообщений.")

    for file in media:
        os.remove(file) # использование временной папки оказалось самым удобным способом.


@client.on(events.NewMessage(CHANNELS_COPY, forwards=FORWARDS))
async def copy(event):
    """
    Обработка сообщений
    """
    if event.message.grouped_id is not None:
        return
    
    id = event.message.id
    caption = event.message.text
    spoiler = False
    web_preview = False
    
    try:
        if event.message.media.__dict__['spoiler'] is True:
            spoiler = True
    except AttributeError:
        pass
    except KeyError:
        pass

    try:
        if event.message.media.webpage.__dict__['url'] is not None:
            web_preview = True
    except AttributeError:
        pass
    except KeyError:
        pass

    gd_print(f"Получили сообщение {id}.")

    caption = await check_caption(caption)

    if event.message.photo and not web_preview:
        await client.download_media(event.message, f"temp_pics/pics_{id}.png")
        await client.send_file(CHANNEL_PASTE, InputMediaUploadedPhoto(await client.upload_file(f"temp_pics/pics_{id}.png"), spoiler=spoiler), caption=caption)
        os.remove(f"temp_pics/pics_{id}.png")

    elif event.message.video: 
        await client.download_media(event.message, f"temp_pics/pics_{id}.mp4")
        await client.send_file(CHANNEL_PASTE, f"temp_pics/pics_{id}.mp4", caption=caption, video_note=True) # video_note позволяет отправлять кружки в виде кружков, однако из-за этого иногда GIF может ошибочно отправляться как кружок. Используйте video_note = False на своё усмотрение.
        os.remove(f"temp_pics/pics_{id}.mp4")

    elif event.message.document:
        file_name = next((x.file_name for x in event.message.document.attributes if isinstance(x, DocumentAttributeFilename)), None)
        if event.message.document.mime_type == "audio/ogg":
            path = await client.download_media(event.message, f"temp_pics/{id}")
            await client.send_file(CHANNEL_PASTE, path, voice_note=True)
            os.remove(path)
            return
        await client.download_media(event.message, f"temp_pics/{file_name}")
        await client.send_file(CHANNEL_PASTE, f"temp_pics/{file_name}", caption=caption, force_document=True)
        os.remove(f"temp_pics/{file_name}")

    else:
        try:
            await client.send_message(CHANNEL_PASTE, caption)
        except Exception as e:
            bd_print(f"Ошибка при отправке сообщения: {e}")
            return

    gd_print(f"Скопировали и успешно отправили сообщение {id}.")




if __name__ == "__main__":
    try:
        client.start(phone=PHONE_NUMBER)
        os.system('cls' if os.name == 'nt' else 'clear')
        print(logo)
        gd_print(f"Успешно вошли в аккаунт {PHONE_NUMBER}.")
        client.parse_mode = "html"

        client.run_until_disconnected()
        gd_print(f"Сессия {PHONE_NUMBER} завершена.")
    except PhoneNumberBannedError:
        bd_print(f"Аккаунт {PHONE_NUMBER} заблокирован.")
    except PasswordHashInvalidError:
        bd_print(f"Неверный пароль для аккаунта {PHONE_NUMBER}.")
    except UsernameInvalidError:
        pass
    except Exception as e:
        bd_print(f"Неизвестная ошибка: {e}")
