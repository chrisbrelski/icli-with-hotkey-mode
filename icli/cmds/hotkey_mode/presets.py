"""
A class for reading preset settings for Hotkey Mode: either fixed amount or percent of available cash.
"""

import math

from dotenv import load_dotenv

from dataclasses import dataclass
from typing import TYPE_CHECKING

from loguru import logger

from icli.helpers import *


if TYPE_CHECKING:
    pass


@dataclass
class PresetReader:
    """Read preset values and make them available."""

    def __init__(self, state):
        load_dotenv(".env.icli")
        HOTKEY_MODE_DEFAULTS = dict(
            ICLI_HOTKEY_MODE_SIZING_CHOICE="amount",
            ICLI_HOTKEY_MODE_SIZING_AMT=100,
            ICLI_HOTKEY_MODE_SIZING_PERCENTAGE=10
        )

        # Use defaults if no values set in config file.
        HOTKEY_MODE_CONFIG = {**HOTKEY_MODE_DEFAULTS, **os.environ}

        self.ICLI_HOTKEY_MODE_SIZING_CHOICE: str = HOTKEY_MODE_CONFIG["ICLI_HOTKEY_MODE_SIZING_CHOICE"]
        self.ICLI_HOTKEY_MODE_SIZING_AMT: float = float(HOTKEY_MODE_CONFIG["ICLI_HOTKEY_MODE_SIZING_AMT"])
        self.ICLI_HOTKEY_MODE_SIZING_PERCENTAGE: float = float(HOTKEY_MODE_CONFIG["ICLI_HOTKEY_MODE_SIZING_PERCENTAGE"])

        if self.ICLI_HOTKEY_MODE_SIZING_CHOICE not in ["amount", "percentage"]:
            self.ICLI_HOTKEY_MODE_SIZING_CHOICE = "amount"

        logger.info("Hotkey Mode position sizing choice: {}", self.ICLI_HOTKEY_MODE_SIZING_CHOICE)
        logger.info("Hotkey Mode position sizing amount: {}", self.ICLI_HOTKEY_MODE_SIZING_AMT)
        logger.info("Hotkey Mode position sizing percentage: {}", self.ICLI_HOTKEY_MODE_SIZING_PERCENTAGE)

        if self.ICLI_HOTKEY_MODE_SIZING_CHOICE == "amount":
            self.presetOrderAmount = self.ICLI_HOTKEY_MODE_SIZING_AMT
            logger.info("Sizing by dollar amount: {}", self.presetOrderAmount)
        elif self.ICLI_HOTKEY_MODE_SIZING_CHOICE == "percentage":
            percentage = self.ICLI_HOTKEY_MODE_SIZING_PERCENTAGE / 100.0
            accountSize = state.accountStatus["TotalCashValue"]
            logger.info("Account size: {}", accountSize)
            sizingByPercentage = math.floor(percentage * accountSize)

            logger.info("Sizing by account percentage: {}", sizingByPercentage)

            self.presetOrderAmount = sizingByPercentage

    def getPresetOrderAmount(self):
        return self.presetOrderAmount
