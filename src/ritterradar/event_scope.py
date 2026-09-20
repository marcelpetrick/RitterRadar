# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared display/ingestion policy for the supported event themes.

Specialist calendars supply the theme context. Fyndling also syndicates general
museum programmes, so its titles must identify a supported theme or themed fair.
Keep excluded records in storage; applying the policy on reads also covers old crawls.
"""

import re

_CANCELLED = re.compile(r"^\W*(?:abgesagt|entfällt|cancelled|canceled)\b", re.IGNORECASE)
_OTHER_ERA = re.compile(
    r"römer(?:fest|tage|lager|markt)\b|römisch|steinzeit|pfahlbau|\b20\.\s*jahrhundert"
    r"|sci[ -]?fi|science[ -]fiction|nerd[ -]expo|antik[ -]?meile",
    re.IGNORECASE,
)
_THEME = re.compile(
    r"mittelalter|m[eé]di[aeé]+val|ritter|renaissance|wikinger|viking|nordmann"
    r"|fantasy|phantasie|\blarp\b|elfia|annotopia|\bmps\b|weihnacht|advent|rauh?nacht"
    r"|burgfest|burgspektakel|burgbelebung|burgmannen|schlossfest|schlossspektakel"
    r"|lebendige[nrs]?\s+(?:burg|schloss)|historisch\w*\s+(?:markt|fest|treiben)"
    r"|hansefest|heerlager|spectaculum|spektakulum|spektakel|schinderhannes"
    r"|sehusafest|roswitha|pfifferdaj|tempus|anno\s*\d|wums|küchenmeisterey",
    re.IGNORECASE,
)
_GENERAL_PROGRAMME = re.compile(
    r"workshop|spielkurs|\b(?:kurs|führung):|museum|mitmach-mittwoch|pfahlbauten",
    re.IGNORECASE,
)


def exclusion_reason(name: str, source_name: str) -> str | None:
    """Explain a definite scope exclusion, or return None for eligible events."""
    if _CANCELLED.search(name):
        return "cancelled"
    if _OTHER_ERA.search(name):
        return "outside supported themes"
    if _GENERAL_PROGRAMME.search(name) and not _THEME.search(name):
        return "general museum or workshop programme"
    if source_name == "Fyndling.de" and not _THEME.search(name):
        return "no supported theme in broad-directory title"
    return None
