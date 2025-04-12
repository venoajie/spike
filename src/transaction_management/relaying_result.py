#!/usr/bin/python3
# -*- coding: utf-8 -*-

# built ins
import asyncio

# installed
from loguru import logger as log

# user defined formula

from messaging import (
    get_published_messages,
    telegram_bot as tlgrm,
)
from utilities import string_modification as str_mod, system_tools


async def relaying_result(
    client_redis: object,
    config_app: list,
    redis_channels: list,
) -> None:
    """ """

    try:

        # connecting to redis pubsub
        pubsub: object = client_redis.pubsub()

        abnormal_trading_notices_channel: str = redis_channels["abnormal_trading_notices"]

        # prepare channels placeholders
        channels = [
            abnormal_trading_notices_channel,
        ]

        # subscribe to channels
        [await pubsub.subscribe(o) for o in channels]

        while True:

            try:

                message_byte = await pubsub.get_message()

                params = await get_published_messages.get_redis_message(message_byte)

                data = params["data"]

                message_channel = params["channel"]

                if abnormal_trading_notices_channel in message_channel:

                    log.error(data)


            except Exception as error:
                
                log.error(error)
                log.info(params)

                await tlgrm.telegram_bot_sendtext(
                    f"cancelling active orders - {error}",
                    "general_error",
                )

                system_tools.parse_error_message(error)

                continue

            finally:
                await asyncio.sleep(0.001)

    except Exception as error:
        
        log.error(error)
        
        await tlgrm.telegram_bot_sendtext(
            f"cancelling active orders - {error}",
            "general_error",
        )

        system_tools.parse_error_message(error)


async def sending_telegram(
    data: list,
) -> None:
    
    pass
