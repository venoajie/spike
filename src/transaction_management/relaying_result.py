#!/usr/bin/python3
# -*- coding: utf-8 -*-

# built ins
import asyncio
import telegram
import os
import sys
from asyncio import run, gather

# -----------------------------------------------------------------------------

this_folder = os.path.dirname(os.path.abspath(__file__))
root_folder = os.path.dirname(os.path.dirname(this_folder))
sys.path.append(root_folder + '/python')
sys.path.append(this_folder)

# -----------------------------------------------------------------------------

import ccxt.async_support as ccxt  # noqa: E402

# -----------------------------------------------------------------------------

# installed
from loguru import logger as log

# user defined formula
from configuration import config


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

                    await sending_telegram(data)

            except Exception as error:
                
                await tlgrm.telegram_bot_sendtext(
                    f"relaying_result - {error}",
                    "general_error",
                )

                system_tools.parse_error_message(error)

                continue

            finally:
                await asyncio.sleep(0.001)

    except Exception as error:
        
        log.error(error)
        
        await tlgrm.telegram_bot_sendtext(
            f"relaying_result - {error}",
            "general_error",
        )

        system_tools.parse_error_message(error)


async def sending_telegram(
    data: list,
) -> None:
    
    """
    noticeType = [
        PRICE_BREAKTHROUGH, 
        PRICE_CHANGE, 
        PRICE_FLUCTUATION
        ]
        
    eventType = [
        DOWN_BREAKTHROUGH,
        RISE_AGAIN,
        DROP_BACK,
        UP_BREAKTHROUGH,
        UP_2,
        UP_1,
        DOWN_1,
        DOWN_2
        ]

    period = [
        WEEK_1,
        DAY_1,
        MONTH_1,
        MINUTE_5,
        HOUR_2
        ]

    
    """

    tlgrm_id = config.main_dotenv("telegram-binance")
    TOKEN = tlgrm_id["bot_token"]
    chat_id = tlgrm_id["bot_chatid"]

    bot = telegram.Bot(token=TOKEN)
    
    message = {}
    noticeType = data["noticeType"]
    symbol = data["symbol"]
    eventType = data["eventType"]
    priceChange = data["priceChange"]
    period = data["period"]
    sendTimestamp = data["sendTimestamp"]
    baseAsset = data["baseAsset"]
    quotaAsset = data["quotaAsset"]
    
    exchange = ccxt.binance()
    timeframe = '5m'
    limit = 9
    
    if "MINUTE" in period:
        
        movement = await fetch_ohlcv(exchange, symbol, timeframe, limit)
        
        message.update(
            {
                "type": noticeType,
                "symbol": symbol,
                "event": eventType,
                "price change": priceChange,
                "period": period,
            }
        )
        
        log.info(message)
        
        await bot.send_message(text=message, chat_id=chat_id)
        
        await bot.send_message(text=movement, chat_id=chat_id)    
    
async def fetch_ohlcv(exchange, symbol, timeframe, limit):
    since = None
    
    ohlcv = await exchange.fetch_ohlcv(symbol, timeframe, since, limit)
    ticker = await exchange.fetch_ticker(symbol)
    await exchange.close()
    
    if len(ohlcv):
        first_candle = ohlcv[0]
        datetime = exchange.iso8601(first_candle[0])
        open = (first_candle[1])
        close = (first_candle[3])
        
        delta = open - close
        delta_pct = delta/open
        
        

        log.debug(first_candle)
        log.warning(f"open: {open}, close: {close} delta: {delta}, delta_pct: {delta_pct}")

        wording = (f"at {datetime} coin {symbol} has changed {delta_pct}% in the last {timeframe}")
        log.error (wording)
        log.error (f"ticker {ticker}")
        return wording  
