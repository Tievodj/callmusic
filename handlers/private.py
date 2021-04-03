from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, Voice

from helpers.filters import command, other_filters2
from helpers.decorators import errors, authorized_users_only
from helpers.errors import DurationLimitError
from helpers.gets import get_url, get_file_name

from os import path

from asyncio.queues import QueueEmpty

import callsmusic

import converter
from downloaders import youtube

from config import DURATION_LIMIT, CHAT_ID















@Client.on_message(command("play") & other_filters2)
@errors
@authorized_users_only
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

    if CHAT_ID in callsmusic.pytgcalls.active_calls:
        await message.reply_text(f"Queued at position {await callsmusic.queues.put(CHAT_ID, file_path=file_path)}!")
    else:
        callsmusic.pytgcalls.join_group_call(CHAT_ID, file_path)
        await message.reply_text("Playing...")





@Client.on_message(command("pause") & other_filters2)
@errors
@authorized_users_only
async def pause(_, message: Message):
    if (
            CHAT_ID not in callsmusic.pytgcalls.active_calls
    ) or (
            callsmusic.pytgcalls.active_calls[CHAT_ID] == 'paused'
    ):
        await message.reply_text("Nothing is playing!")
    else:
        callsmusic.pytgcalls.pause_stream(CHAT_ID)
        await message.reply_text("Paused!")


@Client.on_message(command("resume") & other_filters2)
@errors
@authorized_users_only
async def resume(_, message: Message):
    if (
            CHAT_ID not in callsmusic.pytgcalls.active_calls
    ) or (
            callsmusic.pytgcalls.active_calls[CHAT_ID] == 'playing'
    ):
        await message.reply_text("Nothing is paused!")
    else:
        callsmusic.pytgcalls.resume_stream(CHAT_ID)
        await message.reply_text("Resumed!")


@Client.on_message(command("stop") & other_filters2)
@errors
@authorized_users_only
async def stop(_, message: Message):
    if CHAT_ID not in callsmusic.pytgcalls.active_calls:
        await message.reply_text("Nothing is streaming!")
    else:
        try:
            callsmusic.queues.clear(CHAT_ID)
        except QueueEmpty:
            pass

        callsmusic.pytgcalls.leave_group_call(CHAT_ID)
        await message.reply_text("Stopped streaming!")


@Client.on_message(command("skip") & other_filters2)
@errors
@authorized_users_only
async def skip(_, message: Message):
    if CHAT_ID not in callsmusic.pytgcalls.active_calls:
        await message.reply_text("Nothing is playing to skip!")
    else:
        callsmusic.queues.task_done(CHAT_ID)

        if callsmusic.queues.is_empty(CHAT_ID):
            callsmusic.pytgcalls.leave_group_call(CHAT_ID)
        else:
            callsmusic.pytgcalls.change_stream(
                CHAT_ID,
                callsmusic.queues.get(CHAT_ID)["file_path"]
            )

        await message.reply_text("Skipped the current song!")
