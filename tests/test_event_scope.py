# SPDX-License-Identifier: GPL-3.0-or-later
"""September 2026 examples from live directory results."""

import pytest

from ritterradar.event_scope import exclusion_reason


@pytest.mark.parametrize(
    "name",
    [
        "ABGESAGT 38. Mittelalterliche Markt mit Ritterturnier",
        "Römerfest Carnuntum",
        "XIV. Römertage",
        "Kinderferien 2026 - Abenteuer Pfahlbauten",
        "P.R.I.M. VI – SciFi-LARP 2026",
        "NEXUS - Nerd Expo",
        "Potsdamer Antik-Meile",
        "Spielkurs Passau - Workshop Drehleier Dudelsack Bal Folk",
    ],
)
def test_explicitly_unrelated_or_cancelled_events_are_excluded(name):
    assert exclusion_reason(name, "Specialist calendar") is not None


@pytest.mark.parametrize(
    "name",
    [
        "Mähen mit der Sense",
        "Muster des Monats: Völlig verdreht - Zopfmuster stricken",
        "Das Pastorat zu Zeiten von Pastor Schafmeister zu Beginn des 20. Jahrhunderts",
        "Mitmach-Mittwoch am Labor",
        "Führung: Wiese, Wasser, Waldrand - Artenvielfalt damals, heute und zuhause",
    ],
)
def test_general_museum_programmes_are_not_medieval_markets(name):
    assert exclusion_reason(name, "Fyndling.de") is not None


@pytest.mark.parametrize(
    "name",
    [
        "Mittelaltermarkt Schloss Lenzburg",
        "Elfia Arcen 2026",
        "Renaissancefest",
        "Wikingerfest",
        "3. Eisenbacher Rauhnachtsmarkt",
        "Historisches Markttreiben",
        "Burgbelebung",
        "Festival-Mediaval",
        "Retro MPS Borken",
        "Fantasy LARP",
        "Fête Médiévale Estavayer 1470",
        "Mittelalterlicher Weihnachtsmarkt am Römer",
    ],
)
def test_supported_themes_remain_visible(name):
    assert exclusion_reason(name, "Fyndling.de") is None
