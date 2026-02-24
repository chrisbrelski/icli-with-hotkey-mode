"""Command: hotkey_mode

Category: Hotkey Mode
"""

import asyncio
import math
import sys
import tty
import termios

from dataclasses import dataclass
from typing import TYPE_CHECKING

from loguru import logger

from icli.cmds.base import IOp, command
from icli.cmds.hotkey_mode.presets import PresetReader
from icli.helpers import contractForName, Decimal, PriceOrQuantity

from icli.webullclient import WebullClient


if TYPE_CHECKING:
    pass

# Terminal color control.
class TermColor:
  GREEN = "\033[92m"
  MAGENTA = "\033[95m"
  RESTORE = "\033[m"
  YELLOW = "\033[33m"
  WHITE = "\033[37m"


@command(names=["hotkey_mode"])
@dataclass
class IOpRID(IOp):
    """Run the Hotkey Mode command"""

    def argmap(self):
        return []

    async def run(self):
        if self.state.hotkeyModeTicker is None:
            tickerSymbol = input("Ticker: ").upper()
            self.state.hotkeyModeTicker = tickerSymbol
        else:
            tickerSymbol = self.state.hotkeyModeTicker

        await self.runoplive("add", tickerSymbol)

        logger.info("Starting Hotkey Mode ...")
        logger.warning("Make sure no existing orders are live in TWS.")
        logger.info("A: Buy. S: Sell Half. D: Close. X: Aggressive Close. Q: Quit.")
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)

        self.presetReader = PresetReader(self.state)
        self.state.webullClient = WebullClient()

        if self.state.noDataSubWebullMode == True:
            await self.state.webullClient.loginIfNeeded()

        self.DATA_REFRESH_DELAY = 1.33 # For sleep calls: help refresh of position data.

        # Keypress wait loop.
        ch = None
        while ch != "q":

            color = TermColor.MAGENTA
            colorEnd = TermColor.WHITE
            logger.info("[" + color + "{}" + colorEnd + "] Awaiting keypress.", tickerSymbol)

            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1) # One character.
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)

            if ch == "a":
                logger.info("Key: a. Buy.")

                dollarAmount = self.presetReader.getPresetOrderAmount()

                price = await self.state.webullClient.getQuote(tickerSymbol, refresh=True)
                logger.info("Got Webull Quote: {}", price)

                numShares = math.floor(dollarAmount / price)
                logger.info("Buying {} shares of {}...", numShares, tickerSymbol)

                algo = "LMT"
                buyArgs = f"{tickerSymbol} {numShares} {algo}"

                await self.runoplive("buy", buyArgs)

                await asyncio.sleep(self.DATA_REFRESH_DELAY) # Helps refresh of position data.

                # Wait for the order to fill to update position reference.
                openTrades = self.ib.openTrades()
                logger.info("Buying: Open Trades: {}", openTrades)
                while len(openTrades) != 0:
                    await asyncio.sleep(self.DATA_REFRESH_DELAY)
                    openTrades = self.ib.openTrades()

            elif ch == "s":
                logger.info("Key: s. Sell Half.")

                positions = self.state.contractsForPosition(tickerSymbol, None)
                contract = contractForName(positions[0][0].symbol)
                foundQuantity = positions[0][1]

                numSharesToSell = math.floor(foundQuantity / 2)
                if numSharesToSell <= 0:
                    logger.error("Cannot sell half of {}, Close the position", foundQuantity)
                    continue

                await self.launchSellOrder(tickerSymbol, contract, numSharesToSell)

                await asyncio.sleep(self.DATA_REFRESH_DELAY) # Helps refresh of position data.

            elif ch == "d":
                logger.info("Key: d. Close Position.")

                positions = self.state.contractsForPosition(tickerSymbol, None)
                contract = contractForName(positions[0][0].symbol)
                totalQuantity = positions[0][1]

                await self.launchSellOrder(tickerSymbol, contract, totalQuantity)

                self.state.hotkeyModeTicker = None # Reset to start on new tickers.
                return False # Exit hotkey mode.

            elif ch == "x":
                logger.info("Key: x. Aggressive Close (adjust until done).")

                positions = self.state.contractsForPosition(tickerSymbol, None)
                contract = contractForName(positions[0][0].symbol)
                totalQuantity = positions[0][1]

                # Buy command with Negative quantity means Sell.
                algo = "LMT"
                numShares = -1 * totalQuantity
                sellArgs = f"{tickerSymbol} {numShares} {algo}"

                await self.runoplive("buy", sellArgs) # Sell since negative quantity in args.

                self.state.hotkeyModeTicker = None # Reset to start on new tickers.
                return False # Exit hotkey mode.

            elif ch == "q":
                logger.info("End hotkey mode.")
                self.state.hotkeyModeTicker = None # Reset to start on new tickers.
                return False # Ends the whole command, back to menu.

            else:
                logger.info("Key not mapped. No action.")

    async def launchSellOrder(self, tickerSymbol, contract, quantity):
        isLong = False # For Sell orders.
        orderType = "LMT"

        # Ensure current price is read, not cached.
        # TODO: make sure not to sell more than position, as this will go Short.
        price = await self.state.webullClient.getQuote(tickerSymbol, refresh=True)
        logger.info("Got Webull Quote: {}", price)

        (contract,) = await self.state.qualify(contract)

        fullSellRecord = await self.state.placeOrderForContract(
            tickerSymbol,
            isLong,
            contract,
            PriceOrQuantity(quantity, is_quantity=True),
            Decimal(str(price)),
            orderType,
        )

        logger.info("Sell order record: {}", fullSellRecord)

        # Wait for the order to fill to update position reference.
        openTrades = self.ib.openTrades()
        logger.info("Selling: Open Trades: {}", openTrades)
        while len(openTrades) != 0:
            await asyncio.sleep(self.DATA_REFRESH_DELAY)
            openTrades = self.ib.openTrades()
