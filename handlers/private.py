from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, Voice

from helpers.filters import command, other_filters2
from helpers.decorators import errors, authorized_users_only
from helpers.errors import DurationLimitError
from helpers.gets import get_url, get_file_name

import os

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
                f"Videos mas largos que {DURATION_LIMIT} no están permitidos, la duración del video dado es {audio.duration / 60} minutos"
            )

        file_name = get_file_name(audio)
        file_path = await converter.convert(
            (await message.reply_to_message.download(file_name))
            if not os.path.isfile(os.path.join("downloads", file_name)) else file_name
        )
    elif url:
        file_path = await converter.convert(youtube.download(url))
    else:
        return await message.reply_text("No hay nada para reproducir")

    if CHAT_ID in callsmusic.pytgcalls.active_calls:
        await message.reply_text(f"Encolado en la posición {await callsmusic.queues.put(CHAT_ID, file_path=file_path)}!")
        print("iteam agregado a la cola")
    else:
        callsmusic.pytgcalls.join_group_call(CHAT_ID, file_path)
        await message.reply_text("Reproduciendo...")
        print("Reproduccion Iniciada")



@Client.on_message(command("clean") & other_filters2)
@errors
@authorized_users_only
async def clean(client, message: Message):
    folder = "/downloads"
    count = 0
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        os.unlink(file_path)
        count += 1
    await message.reply_text("eliminados " + {count} + " archivos")
    print("eliminados " + {count} + " archivos")

@Client.on_message(command("pause") & other_filters2)
@errors
@authorized_users_only
async def pause(_, message: Message):
    if (
            CHAT_ID not in callsmusic.pytgcalls.active_calls
    ) or (
            callsmusic.pytgcalls.active_calls[CHAT_ID] == 'paused'
    ):
        await message.reply_text("No se está reproduciendo nada!")
    else:
        callsmusic.pytgcalls.pause_stream(CHAT_ID)
        await message.reply_text("Pausado!")


@Client.on_message(command("resume") & other_filters2)
@errors
@authorized_users_only
async def resume(_, message: Message):
    if (
            CHAT_ID not in callsmusic.pytgcalls.active_calls
    ) or (
            callsmusic.pytgcalls.active_calls[CHAT_ID] == 'playing'
    ):
        await message.reply_text("No hay nada pausado!")
    else:
        callsmusic.pytgcalls.resume_stream(CHAT_ID)
        await message.reply_text("Resumido!")


@Client.on_message(command("stop") & other_filters2)
@errors
@authorized_users_only
async def stop(_, message: Message):
    if CHAT_ID not in callsmusic.pytgcalls.active_calls:
        await message.reply_text("No se está transmitiendo!")
    else:
        try:
            callsmusic.queues.clear(CHAT_ID)
        except QueueEmpty:
            pass

        callsmusic.pytgcalls.leave_group_call(CHAT_ID)
        await message.reply_text("Streaming detenido!")


@Client.on_message(command("skip") & other_filters2)
@errors
@authorized_users_only
async def skip(_, message: Message):
    if CHAT_ID not in callsmusic.pytgcalls.active_calls:
        await message.reply_text("No hay nada en la cola!")
    else:
        callsmusic.queues.task_done(CHAT_ID)

        if callsmusic.queues.is_empty(CHAT_ID):
            callsmusic.pytgcalls.leave_group_call(CHAT_ID)
        else:
            callsmusic.pytgcalls.change_stream(
                CHAT_ID,
                callsmusic.queues.get(CHAT_ID)["file_path"]
            )

        await message.reply_text("Saltado al siguiente item!")


@Client.on_message(command("kill") & other_filters2)
@errors
@authorized_users_only
async def killbot(_, message):
    await message.reply_text("__**Reiniciando Dyno!__**")
    quit()