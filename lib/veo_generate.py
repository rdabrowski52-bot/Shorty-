"""
Generowanie klipów Veo przez Gemini API (alternatywa dla ręcznego Flow).
Bierze pole "prompt" z każdego beatu w episode.json i zapisuje klip pod "clip".

Setup: pip install google-genai
export GEMINI_API_KEY=...            # Gemini API (płatny plan — Veo nie ma darmowego tieru)
albo Vertex AI:
export GOOGLE_GENAI_USE_VERTEXAI=true GOOGLE_CLOUD_PROJECT=... GOOGLE_CLOUD_LOCATION=us-central1

Veo rozlicza się za sekundę wyjścia — zawsze najpierw --dry-run.
Skrypt NIE składa odcinka: obejrzyj klipy, potem odpal lib.assemble_narrated.
"""
import argparse
import json
import os
import sys
import time

DEFAULT_MODEL = os.environ.get("VEO_MODEL", "veo-3.1-fast-generate-preview")
ASPECT_RATIO = "9:16"
DURATION_SECONDS = 8
POLL_INTERVAL_S = 10
TIMEOUT_S = 15 * 60
# Styl z NICHE.md — rzeczy, których Veo ma unikać.
NEGATIVE_PROMPT = (
    "on-screen text, subtitles, captions, watermark, logo, crowd, wide establishing shot, "
    "bright daylight, cartoon, low quality"
)


def _take_path(clip_path: str, take: int, takes: int) -> str:
    if takes == 1:
        return clip_path
    root, ext = os.path.splitext(clip_path)
    return f"{root}_take{take}{ext}"


def _generate_one(client, model: str, prompt: str, out_path: str, resolution: str) -> None:
    from google.genai import types

    operation = client.models.generate_videos(
        model=model,
        prompt=prompt,
        config=types.GenerateVideosConfig(
            aspect_ratio=ASPECT_RATIO,
            duration_seconds=DURATION_SECONDS,
            resolution=resolution,
            negative_prompt=NEGATIVE_PROMPT,
            number_of_videos=1,
        ),
    )
    started = time.monotonic()
    while not operation.done:
        if time.monotonic() - started > TIMEOUT_S:
            raise TimeoutError(f"Veo nie skończył w {TIMEOUT_S}s ({operation.name})")
        time.sleep(POLL_INTERVAL_S)
        operation = client.operations.get(operation)

    if operation.error:
        raise RuntimeError(f"Veo zwrócił błąd: {operation.error}")
    response = operation.response
    if not response or not response.generated_videos:
        reasons = getattr(response, "rai_media_filtered_reasons", None) if response else None
        raise RuntimeError(f"Veo nie zwrócił klipu (filtr bezpieczeństwa?): {reasons}")

    video = response.generated_videos[0].video
    if not video.video_bytes:
        client.files.download(file=video)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    video.save(out_path)


def generate_episode_clips(
    episode_json_path: str,
    model: str = DEFAULT_MODEL,
    beats: list[int] | None = None,
    takes: int = 1,
    resolution: str = "720p",
    force: bool = False,
    dry_run: bool = False,
) -> tuple[list[str], int]:
    """Zwraca (wygenerowane ścieżki, liczba nieudanych beatów)."""
    with open(episode_json_path) as f:
        episode = json.load(f)

    jobs = []
    for idx, beat in enumerate(episode["beats"], start=1):
        if beats and idx not in beats:
            continue
        if not beat.get("prompt"):
            print(f"[beat {idx}] brak pola 'prompt' — pomijam")
            continue
        for take in range(1, takes + 1):
            out_path = _take_path(beat["clip"], take, takes)
            if os.path.exists(out_path) and not force:
                print(f"[beat {idx}] {out_path} już istnieje — pomijam (--force nadpisuje)")
                continue
            jobs.append((idx, beat["prompt"], out_path))

    total_s = len(jobs) * DURATION_SECONDS
    print(f"Model: {model} | klipów do wygenerowania: {len(jobs)} | "
          f"łącznie {total_s}s wideo (koszt = {total_s}s × stawka modelu)")
    if dry_run:
        for idx, _, out_path in jobs:
            print(f"  [beat {idx}] -> {out_path}")
        return [], 0

    from google import genai
    client = genai.Client()

    done = []
    for idx, prompt, out_path in jobs:
        print(f"[beat {idx}] generuję -> {out_path} ...", flush=True)
        try:
            _generate_one(client, model, prompt, out_path, resolution)
        except Exception as e:  # jeden odrzucony beat nie może ubić reszty
            print(f"[beat {idx}] BŁĄD: {e}", file=sys.stderr)
            continue
        done.append(out_path)
        print(f"[beat {idx}] OK")

    print(f"Gotowe: {len(done)}/{len(jobs)}. Obejrzyj klipy przed złożeniem odcinka.")
    if takes > 1:
        print("Kilka wersji na beat: wybrany *_takeN skopiuj pod ścieżkę 'clip' z episode.json.")
    return done, len(jobs) - len(done)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode", required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help="np. veo-3.1-generate-preview (lepszy, droższy)")
    parser.add_argument("--beats", default="",
                        help="numery beatów od 1, np. '2,4' (domyślnie wszystkie)")
    parser.add_argument("--takes", type=int, default=1, help="ile wersji na beat")
    parser.add_argument("--resolution", default="720p", choices=["720p", "1080p"])
    parser.add_argument("--force", action="store_true", help="nadpisz istniejące klipy")
    parser.add_argument("--dry-run", action="store_true",
                        help="pokaż co i ile zostanie wygenerowane, bez wywołań API")
    args = parser.parse_args()

    selected = [int(b) for b in args.beats.split(",") if b.strip()] or None
    _, failed = generate_episode_clips(
        args.episode, args.model, selected, args.takes,
        args.resolution, args.force, args.dry_run,
    )
    sys.exit(1 if failed else 0)
