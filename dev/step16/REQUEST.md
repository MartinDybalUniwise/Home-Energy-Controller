# GoodWe Integration Refactor – Request

HEC musí být jediný aktivní controller/writer FVE. SDG bude pouze reader/logger.

Potřebujeme:
1. Centrální `GoodWeManager` s lock/mutex, retry, read-back verification
2. Refaktor `FTEReader` – primárně přes knihovnu GoodWe
3. Nový `FTEWriter` s idempotentními příkazy
4. `SDGHistoryReader` pro import historických dat z SDG
5. Plně konfigurovatelná cesta k SDG datům
6. Web diagnostika a configurace

Bez kolizí mezi SDG reader a HEC writer. SDG neřídí FVE.
