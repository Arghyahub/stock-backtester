from enum import Enum


class UserType(str, Enum):
    ADMIN = "admin"
    GENERAL = "general"


class EquityType(str, Enum):
    INDEX = "index"
    STOCK = "stock"
    ETF = "etf"