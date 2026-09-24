"""
Assembler dla "The Last 3 Seconds": klipy z Veo/Flow (ręcznie), auto voiceover
(Google TTS) per beat, długość klipu dopasowana do audio, napisy wypalane.
"""
import json
import os
import subprocess
import tempfile
import textwrap

from lib.tts_google import synthesize

TARGET_W, TARGET_H = 1080, 1920
MUSIC_VOLUME = 0.12

CAPTION_FONT_SIZE = 54
CAPTION_BOX_BORDER = 20
CAPTION_WRAP_CHARS = 26  # ~26 znaków przy 54px mieści się w 1080 z marginesem
CAPTION_LINE_STEP = CAPTION_FONT_SIZE + 2 * CAPTION_BOX_BORDER  # boxy linii się stykają
CAPTION_BOTTOM_OFFSET = 350

# Nadpisz zmienną środowiskową SHORTY_FONT, jeśli żaden z tych nie istnieje.
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def _audio_duration(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "json", path],
        capture_output=True, text=True, check=True,
    )
    return float(json.loads(out.stdout)["format"]["duration"])


def _escape_drawtext(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "’")
        .replace(",", "\\,")
    )


def _find_font() -> str:
    env_font = os.environ.get("SHORTY_FONT")
    if env_font:
        if not os.path.isfile(env_font):
            raise FileNotFoundError(f"SHORTY_FONT wskazuje na nieistniejący plik: {env_font}")
        return env_font
    for path in FONT_CANDIDATES:
        if os.path.isfile(path):
            return path
    raise FileNotFoundError(
        "Nie znaleziono fontu do napisów. Ustaw SHORTY_FONT=/sciezka/do/fontu.ttf"
    )


def _caption_filters(text: str, font_path: str) -> str:
    # drawtext nie łamie linii sam — każda linia to osobny, wyśrodkowany drawtext.
    # Ostatnia linia siedzi na h-CAPTION_BOTTOM_OFFSET, kolejne rosną w górę.
    font = _escape_drawtext(font_path.replace("\\", "/"))
    lines = textwrap.wrap(text, CAPTION_WRAP_CHARS) or [""]
    filters = []
    for i, line in enumerate(lines):
        offset = CAPTION_BOTTOM_OFFSET + (len(lines) - 1 - i) * CAPTION_LINE_STEP
        filters.append(
            f"drawtext=fontfile='{font}':text='{_escape_drawtext(line)}':"
            f"fontcolor=white:fontsize={CAPTION_FONT_SIZE}:"
            f"box=1:boxcolor=black@0.45:boxborderw={CAPTION_BOX_BORDER}:"
            f"x=(w-text_w)/2:y=h-{offset}"
        )
    return ",".join(filters)


def _prep_beat(beat: dict, idx: int, tmp_dir: str, font_path: str) -> str:
    audio_path = os.path.join(tmp_dir, f"beat{idx}.mp3")
    synthesize(beat["text"], audio_path)
    dur = _audio_duration(audio_path)

    vf = (
        f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=increase,"
        f"crop={TARGET_W}:{TARGET_H},"
        + _caption_filters(beat["text"], font_path)
    )

    video_path = os.path.join(tmp_dir, f"beat{idx}.mp4")
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", beat["clip"],
            "-i", audio_path,
            "-t", str(dur),
            "-vf", vf,
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            video_path,
        ],
        check=True, capture_output=True,
    )
    return video_path


def assemble_episode(episode_json_path: str, out_path: str) -> str:
    with open(episode_json_path) as f:
        episode = json.load(f)

    font_path = _find_font()
    tmp_dir = tempfile.mkdtemp()
    beat_videos = [
        _prep_beat(b, i, tmp_dir, font_path) for i, b in enumerate(episode["beats"])
    ]

    concat_list = os.path.join(tmp_dir, "concat.txt")
    with open(concat_list, "w") as f:
        for v in beat_videos:
            f.write(f"file '{v}'\n")

    no_music_path = os.path.join(tmp_dir, "no_music.mp4")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
         "-c", "copy", no_music_path],
        check=True, capture_output=True,
    )

    music = episode.get("music")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    if music:
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", no_music_path,
                "-stream_loop", "-1", "-i", music,
                "-filter_complex",
                f"[1:a]volume={MUSIC_VOLUME}[bg];[0:a][bg]amix=inputs=2:duration=first:normalize=0[aout]",
                "-map", "0:v:0", "-map", "[aout]",
                "-c:v", "copy", "-c:a", "aac", "-shortest",
                out_path,
            ],
            check=True, capture_output=True,
        )
    else:
        subprocess.run(["ffmpeg", "-y", "-i", no_music_path, "-c", "copy", out_path],
                        check=True, capture_output=True)

    return out_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode", required=True)
    parser.add_argument("--out", default="./output/episode.mp4")
    args = parser.parse_args()
    assemble_episode(args.episode, args.out)
    print(f"Gotowe: {args.out}")
