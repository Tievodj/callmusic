from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, Voice

from helpers.filters import command, other_filters2
from helpers.decorators import errors
from helpers.errors import DurationLimitError
from helpers.gets import get_url, get_file_name

from os import path


import callsmusic

import converter
from downloaders import youtube

from config import DURATION_LIMIT, CHAT_ID





@Client.on_message(command("play") & other_filters2)
@errors
async def play(_, message: Message):
    audio = (message.reply_to_message.audio or message.reply_to_message.voice) if message.reply_to_message else None
    url = get_url(message)

    if audio:
        if round(audio.duration / 60) > DURATION_LIMIT:
            raise DurationLimitError(
                f"Videos longer than {DURATION_LIMIT} minute(s) aren't allowed, the provided video is {audio.duration / 60} minute(s)"
            )

        file_name = get_file_name(audio)
        file_path = await converter.convert(
            (await message.reply_to_message.download(file_name))
            if not path.isfile(path.join("downloads", file_name)) else file_name
        )
    elif url:
        file_path = await converter.convert(youtube.download(url))
    else:
        return await message.reply_text("You did not give me anything to play!")

    if {CHAT_ID} in callsmusic.pytgcalls.active_calls:
        await message.reply_text(f"Queued at position {await callsmusic.queues.put({CHAT_ID}, file_path=file_path)}!")
    else:
        callsmusic.pytgcalls.join_group_call({CHAT_ID}, file_path)
        await message.reply_text("Playing...")
