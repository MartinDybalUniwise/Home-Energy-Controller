# GoodWe Integration Refactor – Request

## Objective

Implement the approved GoodWe integration boundary so HEC is the only active
controller/writer and SDG remains a reader/logger. This step authorizes the
implementation phase for the previously approved design, with no physical-device
writes or controller activation before explicit human and hardware verification.

HEC musí být jediný aktivní controller/writer FVE. SDG zůstává pouze
reader/logger, diagnostika a historické importy.

Potřebujeme:
1. Centrální `GoodWeManager` s lock/mutex, retry, read-back verification
2. Refaktor `FTEReader` – primárně přes knihovnu GoodWe
3. Nový `FTEWriter` s idempotentními příkazy
4. Všechny controller komponenty, reader i writer, musí při běhu vypisovat stav do terminálu
5. `SDGHistoryReader` pro import historických dat z SDG
6. Plně konfigurovatelná cesta k SDG datům
7. Web diagnostika a configurace

Bez kolizí mezi SDG reader a HEC writer. SDG neřídí FVE.
