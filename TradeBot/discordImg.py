import discord
import os
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import asyncio


def sendImgs():
    # imgArr = os.listdir("images")
    client = discord.Client()

    async def sendMessage(dfile):
        channel = client.get_channel(972271652161347585)

        await channel.send(file=dfile)

    @client.event
    async def on_ready():
        print("Started")
        while True:
            imgArr = os.listdir("images/trades")
            for i in imgArr:
                img = Image.open(f"images/trades/{i}")
                bytes = BytesIO()
                img.save(bytes, format="JPEG")
                bytes.seek(0)
                dfile = discord.File(bytes, filename="image.jpeg")
                await sendMessage(dfile)
                await asyncio.sleep(2)
            await asyncio.sleep(60)