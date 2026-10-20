# Schválený malý krok

Klasifikace SMALL: lokální oprava tří zastaralých očekávání a synchronizace jednoho browser scénáře, bez nové funkce. Gate A: předchozí chat plán schválen uživatelem „souhlasím“.

| Krok | Činnost | Stav |
| --- | --- | --- |
| S01 | Ověřit kontrakty na aktuálním kódu a dokumentaci | PASS |
| S02 | Upravit testy a opravit null serializaci a aplikaci jazyka po úspěšném uložení | PASS |
| S03 | Spustit unit, reálné E2E, lint a SDD validaci | PASS |

Riziko: přizpůsobení testu chybě. Proto testovat konkrétní neinterferenci historie a živé telemetrie, registraci skutečné třídy i vypnutí příznakem. Jazyk ověřit uloženou odpovědí a novým načtením. Neskrývat selhání. Review a Human Gate před DONE, nasazením a restartem zůstávají nutné.

## Goal
Obnovit důvěryhodnou úplnou validaci Step26.

Zjištěná příčina: Number('') převáděl prázdné nullable int na 0; server odmítal goodwe/tng/ote override pod minimem 60. Jazyk se aplikoval i při neúspěchu. Oprava je omezena na serializaci nullable čísel a úspěšné dokončení formuláře, nikoli na limity controlleru. Doplněn CZ/EN changelog připravovaného vydání; žádný čas vydání není předstírán.
