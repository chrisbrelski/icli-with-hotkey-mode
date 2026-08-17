"""
Class to get stock price quotes using the unofficial Webull API.
Reference: https://pypi.org/project/webull/
"""

import os.path

from loguru import logger
from webull import webull


class WebullClient:
    """Client for the Unofficial Webull API for quote data if no data subscription present."""

    def __init__(self):
        self.lastPrice = None
        self.wb = webull()

    async def loginIfNeeded(self):
        if not os.path.isfile("./did.bin"):
            logger.info("Webull Unofficial API login required...")
            email = input("Email address: ")
            password = input("Password: ")
            self.wb.login(email, password)

    async def getQuote(self, ticker, refresh=False):
        # Try cached version first unless fresh requested.
        # This is to prevent reading from Webull twice inside the launched Buy command.
        if self.lastPrice is not None and refresh == False:
            return self.lastPrice

        try:
            stockData = self.wb.get_quote(ticker) 
        except ValueError as e:
            logger.error("Exception reading from Webull API: {}", e)

        if "pPrice" in stockData:
            # Current price field in some data samples.
            lastPrice = stockData["pPrice"]
        elif "close" in stockData:
            # Current Close of the current candle, i.e. last price.
            lastPrice = stockData["close"]
        else:
            # May happen if the data format is changed.
            logger.error("Price field missing in Webull data received.")
            raise ValueError("price field missing in Webull data result")

        self.lastPrice = float(lastPrice)

        return self.lastPrice
