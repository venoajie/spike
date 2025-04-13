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

        tlgrm_id = config.main_dotenv("telegram-binance")
        TOKEN = tlgrm_id["bot_token"]
        chat_id = tlgrm_id["bot_chatid"]

        bot = telegram.Bot(token=TOKEN)

        exchange = ccxt.binance()

        while True:

            try:

                message_byte = await pubsub.get_message()

                params = await get_published_messages.get_redis_message(message_byte)

                data = params["data"]

                message_channel = params["channel"]

                if abnormal_trading_notices_channel in message_channel:
                    
                    noticeType = data["noticeType"]
                    symbol = data["symbol"]
                    eventType = data["eventType"]
                    period = data["period"]
                    priceChange = data["priceChange"]
                    
                    log.info(data)
                                
                    if "MINUTE" in period:
                    
                        tf_int = str_mod.extract_integers_from_text(period)
                        timeframe = (f"{tf_int}m")
                        limit = 9
                            
                        if "VOLUME" in noticeType:

                            if "HIGH" in period:
                                    
                                main = (f"{symbol} experienced HIGHER volume than average\n")
                                extra_info = (f"TF: {timeframe}, price change: {priceChange}\n")
                                wording = (f"{main} {extra_info} {datetime}")
                            
                                await bot.send_message(
                                    text=wording,
                                    chat_id=chat_id,
                                    )    
                            
                        else:
                                
                                is_fluctuated = await def compute_price_changes_result(exchange, symbol, timeframe, limit)
                                
                                if is_fluctuated:
                                    
                                    log.warning (f"{symbol} {movement}")
                                    
                                    await bot.send_message(
                                        text=movement,
                                        chat_id=chat_id,
                                        )    


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
        
        system_tools.parse_error_message(error)
        
        await tlgrm.telegram_bot_sendtext(
            f"relaying_result - {error}",
            "general_error",
        )


async def sending_telegram(data: list) -> None:
    
    """
    noticeType = [
        PRICE_BREAKTHROUGH, 
        PRICE_CHANGE, 
        PRICE_FLUCTUATION,
        VOLUME_PRICE
        ]
        
    eventType = [
        DOWN_BREAKTHROUGH,
        RISE_AGAIN,
        DROP_BACK,
        UP_BREAKTHROUGH,
        UP_2,
        UP_1,
        DOWN_1,
        DOWN_2,
        HIGH_VOLUME_RISE_3, 
        HIGH_VOLUME_RISE_2,
        HIGH_VOLUME_RISE_1,
        ]

    period = [
        WEEK_1,
        DAY_1,
        MONTH_1,
        MINUTE_5,
        HOUR_2
        ]
        
    example:
        {
            'type': 'VOLUME_PRICE', 
            'symbol': 'LISTAUSDT', 
            'event': 'HIGH_VOLUME_RISE_1', 
            'price change': 0.10529986, 
            'period': 'MINUTE_15'
            }

    
    """
    
    pass

        
async def compute_price_changes_result(
    exchange: str, 
    symbol: str, 
    timeframe: str, 
    limit: int,
    ) ->str:
        
    """ 
    
    """
    
    wording = ""
    
    ohlcv = await get_ohlcv(exchange,symbol, timeframe, limit)
            
    ticker = await get_ticker(exchange,symbol)
    
    if len(ohlcv):
        last_candle = ohlcv[limit-1]
        datetime = ticker["datetime"]
        last = ticker["last"]
        open = (last_candle[1])
        close = (last_candle[3])
        
        delta_close = close - open  
        delta_close_pct = abs(((delta_close/open)))

        delta_current = last - open  
        delta_current_pct = abs(round((delta_current/open),2))
        
        THRESHOLD = 3/100
        
        if delta_close_pct >= THRESHOLD:
                
            if delta_close > 0:
                move = "HIGHER"   
            if delta_close < 0:
                move = "LOWER"   
    
            main = (f"{symbol} closing is {round(delta_close_pct*100,2)}%  {move} than its opening \n")
            extra_info = (f"TF: {timeframe}, Open: {open}, Close: {close}, Current: {last}\n")
            wording = (f"{main} {extra_info} {datetime}")
        
        
        if delta_current_pct >= THRESHOLD:
                
            if delta_current > 0:
                move = "HIGHER"   
            if delta_current < 0:
                move = "LOWER"   
            
            main = (f"{symbol} current price is {round(delta_current_pct*100,2)}%  {move} than its opening \n")
            extra_info = (f"TF: {timeframe}, Open: {open}, Current: {last}\n")
            wording = (f"{main} {extra_info} {datetime}")
        
    
    await exchange.close()
    
    return wording  


async def get_ohlcv(
    exchange: str, 
    symbol: str, 
    timeframe: str, 
    limit: int,
    since: int = None,
    ) -> dict:

    return await exchange.fetch_ohlcv(
        symbol, 
        timeframe, 
        since,
        limit,
        )  


async def get_ticker(
    exchange: str, 
    symbol: str, 
    ) -> dict:
        
    """ 
    example: {
        'symbol': 'HARD/USDT', 
        'timestamp': 1744501380384, 
        'datetime': '2025-04-12T23:43:00.384Z', 
        'high': 0.0319, 
        'low': 0.0202,
        'bid': 0.0224, 
        'bidVolume': 2176.0, 
        'ask': 0.0226, 
        'askVolume': 4170.0, 
        'vwap': 0.02514621, 
        'open': 0.0319, 
        'close': 0.0226,
        'last': 0.0226, 
        'previousClose': 0.0318, 
        'change': -0.0093, 
        'percentage': -29.154, 
        'average': 0.0272, 
        'baseVolume': 25033279.0, 
        'quoteVolume': 629492.088,
        'markPrice': None, 
        'indexPrice': None,
        'info': {
            'symbol': 'HARDUSDT', 
            'priceChange': '-0.00930000', 
            'priceChangePercent': '-29.154',
            'weightedAvgPrice': '0.02514621',
            'prevClosePrice': '0.03180000', 
            'lastPrice': '0.02260000', 
            'lastQty': '2252.00000000', 
            'bidPrice': '0.02240000', 
            'bidQty': '2176.00000000', 
            'askPrice': '0.02260000', 
            'askQty': '4170.00000000', 
            'openPrice': '0.03190000', 
            'highPrice': '0.03190000', 
            'lowPrice': '0.02020000', 
            'volume': '25033279.00000000', 
            'quoteVolume': '629492.08800000', 
            'openTime': 1744414980384, 
            'closeTime': 1744501380384,
            'firstId': 41880405, 
            'lastId': 41897290, 
            'count': 16886
            }
            }
    
    """
        
    return await exchange.fetch_ticker(symbol)