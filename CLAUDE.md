# Auto-Short Pipeline — instrukcja dla Claude Code

PRZECZYTAJ NAJPIERW `NICHE.md` — brief formatu/niszy "The Last 3 Seconds".
Każda propozycja tematu/skryptu/promptu musi być z nim spójna.

## Workflow gdy user mówi "zrób mi temat/odcinek"
1. Research (web search) — temat spełniający kryteria z NICHE.md. Zweryfikuj
   fakty, nie zmyślaj szczegółów historycznych.
2. Napisz skrypt w beatach (struktura w NICHE.md).
3. Dla każdego beatu osobny prompt do Veo, ZAWSZE po angielsku, w bloku kodu.
4. Zapisz wszystko do episode.json (wzór: episode_example.json).
5. Klipy: albo user generuje je ręcznie w Flow (brak API) i wrzuca do clips/,
   albo (jeśli ma GEMINI_API_KEY) Veo przez Gemini API:
   python3 -m lib.veo_generate --episode episode.json --dry-run   # najpierw koszt
   python3 -m lib.veo_generate --episode episode.json
   Każdy beat w episode.json potrzebuje wtedy pola "prompt". Nie generuj bez
   zgody usera (płatne per sekunda) i daj mu obejrzeć klipy przed składaniem.
6. Uruchom: python3 -m lib.assemble_narrated --episode episode.json --out output/nazwa.mp4
7. Sprawdź ffprobe'em długość finalnego pliku.

Flow (Veo UI) nie ma API — automatyzacja idzie wyłącznie przez Gemini API (lib/veo_generate.py).
