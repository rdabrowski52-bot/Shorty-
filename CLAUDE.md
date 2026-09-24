# Auto-Short Pipeline — instrukcja dla Claude Code

PRZECZYTAJ NAJPIERW `NICHE.md` — brief formatu/niszy "The Last 3 Seconds".
Każda propozycja tematu/skryptu/promptu musi być z nim spójna.

## Workflow gdy user mówi "zrób mi temat/odcinek"
1. Research (web search) — temat spełniający kryteria z NICHE.md. Zweryfikuj
   fakty, nie zmyślaj szczegółów historycznych.
2. Napisz skrypt w beatach (struktura w NICHE.md).
3. Dla każdego beatu osobny prompt do Veo, ZAWSZE po angielsku, w bloku kodu.
4. Zapisz wszystko do episode.json (wzór: episode_example.json).
5. User generuje wideo ręcznie w Flow (brak API) i wrzuca do clips/, update
   ścieżek w episode.json.
6. Uruchom: python3 -m lib.assemble_narrated --episode episode.json --out output/nazwa.mp4
7. Sprawdź ffprobe'em długość finalnego pliku.

Flow (Veo UI) nie ma API — nie zakładaj automatycznego generowania wideo.
