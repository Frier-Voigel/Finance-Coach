"""Plain-language answers to 'what is X?' money questions. Fixed text: no LLM, no numbers, never a recommendation."""
from __future__ import annotations

import re

_ASK = re.compile(r"^\s*(?:what(?:'s| is| are)|whats|explain|how (?:do|does)|define|tell me about)\b")
_PERSONAL = re.compile(r"\b(my|mine|our|i have)\b")  # 'what is my emergency fund' is a status question, not a definition

GLOSSARY: list[tuple[str, str]] = [
    (r"index funds?", "An index fund is a mutual fund (or ETF) that simply copies a market index instead of having a manager pick "
     "investments. That usually means lower fees and wide diversification, but its value still rises and falls with the market."),
    (r"\betfs?\b|exchange[- ]traded", "An ETF (exchange-traded fund) is a basket of investments that trades on a stock exchange like a share. "
     "Many ETFs copy an index. You pay a small yearly fee and the price moves during the day."),
    (r"mutual funds?", "A mutual fund pools money from many people and a fund manager invests it in a mix of shares, bonds or both. "
     "You own units of the fund. Returns are not guaranteed, and fees (the expense ratio) reduce what you keep."),
    (r"\bsips?\b|systematic investment", "A SIP (systematic investment plan) invests a fixed amount at regular intervals, usually monthly. "
     "It builds a habit and spreads your buying across different market prices. It is a way of paying in, not a type of investment."),
    (r"emergency fund", "An emergency fund is cash set aside for surprises such as a job loss or a medical bill, commonly "
     "three to six months of essential expenses. It is kept somewhere safe and easy to reach, not invested for growth."),
    (r"compound(?:ing| interest)", "Compounding means earning returns on your earlier returns as well as on your original money. "
     "Over long periods it makes growth speed up, which is why starting early and staying invested matters."),
    (r"inflation", "Inflation is the general rise in prices over time, so the same rupee buys less each year. "
     "Savings that earn less than inflation lose buying power."),
    (r"diversif", "Diversification means spreading money across different kinds of investments so one bad result hurts less. "
     "It lowers risk but does not remove it."),
    (r"expense ratio", "The expense ratio is the yearly fee a fund charges, as a percentage of what you have invested in it. "
     "A small difference compounds into a big one over many years."),
    (r"\bstocks?\b|\bshares?\b|equit(?:y|ies)", "A share (or stock) is a small piece of ownership in a company. Its price can swing a lot, "
     "and you can lose money. Spreading across many companies lowers the risk from any single one."),
    (r"\bbonds?\b|debt funds?", "A bond is a loan you give to a government or company in return for regular interest and your money back "
     "at the end. It is usually steadier than shares, but it still carries risks such as default and changing interest rates."),
    (r"credit score|cibil", "A credit score is a number that summarises how reliably you repay borrowed money. "
     "Paying on time, using a small share of your limit and keeping old accounts open usually help it."),
    (r"fixed deposit|\bfds?\b", "A fixed deposit (FD) locks your money with a bank for a set period at a set interest rate. "
     "It is predictable and low-risk, though breaking it early usually costs you, and interest is taxable."),
]
NOTE = "This is general education, not a recommendation of any product."


def explain(text: str) -> str | None:
    """A glossary answer if `text` asks what a money term is, else None."""
    low = text.lower().strip().rstrip("?.! ")
    if not _ASK.match(low) or _PERSONAL.search(low):
        return None
    for pattern, answer in GLOSSARY:
        if re.search(pattern, low):
            return f"{answer} {NOTE}"
    return None
