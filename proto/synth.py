"""漫才の台本（proto/<名前>.txt）から、声を作って間を入れて 1 本の音声にする試作。

    python proto/synth.py proto/hacker.txt                  # Chirp 3: HD（いま使える方）
    python proto/synth.py proto/hacker.txt --backend gemini # Gemini-TTS（Agent Platform API を有効にしてから）
    python proto/synth.py proto/hacker.txt --backend voicevox # VOICEVOX（アプリを起動しておく。声は voices.json の voicevox）

できるもの：build/<名前>/<名前>_<backend>.mp3（と .wav）、timeline.txt（何秒に誰が何を言うか）
キーは BlackFairyTales の .env の GOOGLE_TTS_API_KEY を借りる（試作のあいだだけ）。
"""
import argparse
import array
import base64
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "build" / "cache" / "tts"
RATE = 24000
FPS = 30  # 動画のコマ数（口パクのタイムラインもこの刻み）
BFT = Path("Z:/git/BlackFairyTales")  # 先に作った童話の動画。読み間違いのリストと数え方の読みを共有する
ENV_FILES = [ROOT / ".env", BFT / ".env"]
GEMINI_MODEL = "gemini-2.5-pro-tts"

LINE_RE = re.compile(r"^(AB|A|B)(!{1,3})?(?:\(([-+]?\d+(?:\.\d+)?)\))?:\s*(.+)$")
LOOK_RE = re.compile(r"^\(見つめ合う\s+(\d+(?:\.\d+)?)\)$")
QUOTE_RE = re.compile(r"「([^」]*)」@(\w+)\s*")
RUBY_RE = re.compile(r"\{([^|}]*)\|([^}]*)\}")
TAG_RE = re.compile(r"\[pause(?: short| long)?\]")


def env_key(name):
    if os.environ.get(name):
        return os.environ[name]
    for f in ENV_FILES:
        if f.exists():
            for line in f.read_text(encoding="utf-8-sig").splitlines():
                if line.startswith(name + "="):
                    return line.split("=", 1)[1].strip()
    raise SystemExit(f"{name} が見つからない")


def ffmpeg():
    found = shutil.which("ffmpeg")
    if found:
        return found
    hits = sorted(glob.glob(str(Path(os.environ["LOCALAPPDATA"]) / "Microsoft/WinGet/Packages/Gyan.FFmpeg*/*/bin/ffmpeg.exe")))
    if hits:
        return hits[-1]
    raise SystemExit("ffmpeg が見つからない")


# ---------- 台本 ----------

def display(text):
    return TAG_RE.sub("", RUBY_RE.sub(r"\1", text)).strip()


def spoken(text):
    return RUBY_RE.sub(r"\2", text).strip()


def parse(path):
    """(コンビ, 行の一覧, 題名など)。行は (話し手, 前の間, [(読む文, スタイル, 表示の文), ...], 表示の文, 叩く強さ)。
    「(見つめ合う 1.2)」の行は ("LOOK", 秒, [], "", False)。"""
    combo, lines, meta = "male", [], {}
    for raw in Path(path).read_text(encoding="utf-8-sig").splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        if raw.startswith("combo:"):
            combo = raw.split(":", 1)[1].strip()
            continue
        if raw.startswith(("title:", "theme:", "thumb:", "short:")):  # 題名とお題（タイトル画面）、サムネイルの文句（／で 3 案、｜で改行）、ショートの区間（秒-秒）
            key, value = raw.split(":", 1)
            meta[key] = value.strip()
            continue
        look = LOOK_RE.match(raw)
        if look:
            lines.append(("LOOK", float(look.group(1)), [], "", False))
            continue
        m = LINE_RE.match(raw)
        if not m:
            raise SystemExit(f"読めない行: {raw}")
        who, hit, gap, body = m.group(1), len(m.group(2) or ""), m.group(3), m.group(4)  # hit は叩く強さ（0＝叩かない、1〜3）
        segs, pos = [], 0
        for q in QUOTE_RE.finditer(body):
            if body[pos:q.start()].strip():
                segs.append((spoken(body[pos:q.start()]), None, display(body[pos:q.start()])))
            segs.append((spoken(q.group(1)), q.group(2), f"「{display(q.group(1))}」"))
            pos = q.end()
        if body[pos:].strip():
            segs.append((spoken(body[pos:]), None, display(body[pos:])))
        shown = QUOTE_RE.sub(lambda q: f"「{q.group(1)}」", body)
        lines.append((who, None if gap is None else float(gap), segs, display(shown), hit))
    return combo, lines, meta


# ---------- 読み ----------

_READINGS = {}


def reading(text, cfg, backend="chirp"):
    """読み上げにだけ使う読み替え（字幕は変わらない）。BlackFairyTales の tools/config.json の readings.ja（共通のリスト）、
    voices.json の readings（漫才だけのもの）、VOICEVOX のときは voices.json の voicevox.readings（VOICEVOX だけのもの）を、
    長い言葉から順に置き換え、数え方（「4つ」→「よっつ」など）もかなにする。読み間違いを見つけたら、共通のリストのほうに足す。"""
    if backend not in _READINGS:
        shared = json.loads((BFT / "tools" / "config.json").read_text(encoding="utf-8-sig"))["readings"]["ja"]
        merged = {**shared, **cfg.get("readings", {})}
        if backend == "voicevox":
            merged.update(cfg.get("voicevox", {}).get("readings", {}))
        _READINGS[backend] = sorted(((k, v) for k, v in merged.items() if not k.startswith("_")), key=lambda kv: -len(kv[0]))
    for word, read in _READINGS[backend]:
        text = text.replace(word, read)
    return bft_build().read_counters(text)


def bft_build():
    """BlackFairyTales の tools/build.py（数え方の読み read_counters を借りる）。"""
    import importlib.util
    import sys
    if "bft_build" not in sys.modules:
        if str(BFT / "tools") not in sys.path:   # build.py が同じフォルダのモジュール（runlock など）を読むため
            sys.path.append(str(BFT / "tools"))
        spec = importlib.util.spec_from_file_location("bft_build", BFT / "tools" / "build.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules["bft_build"] = mod
    return sys.modules["bft_build"]


# ---------- 声 ----------

def settings(cfg, combo, speaker, style, backend="chirp"):
    if backend == "voicevox":
        return vv_settings(cfg, combo, speaker, style)
    base = cfg["combos"][combo][speaker]
    st = cfg["styles"][style] if style else {}
    own = "voice" in st  # 別の声に替えるスタイル（自動音声など）は、話し手の速さ・高さを引き継がない
    return {
        "voice": st.get("voice", base["voice"]),
        "gemini_voice": st.get("gemini_voice", base["gemini_voice"]),
        "speed": st.get("speed", 1.0) * (1.0 if own else base.get("speed", 1.0)),
        "pitch": st.get("pitch", 1.0) * (1.0 if own else base.get("pitch", 1.0)),
        "af": st.get("af", ""),
        "gain_db": st.get("gain_db", 0) + (0 if own else base.get("gain_db", 0)),
        "prompt": "。".join(p for p in [base.get("prompt") if not own else "", st.get("prompt", "")] if p),
    }


def vv_settings(cfg, combo, speaker, style):
    """VOICEVOX の声。キャラ名とスタイル名（null ならそのキャラの最初のスタイル）で選び、
    速さ（speedScale）・高さ（pitchScale、0 が元の高さ）・抑揚（intonationScale）を変える。
    「」のスタイルに character があれば別のキャラ（話し手の速さなどは引き継がない）、なければ話し手の声のまま変える。"""
    vv = cfg["voicevox"]
    base = vv["combos"][combo][speaker]
    st = vv["styles"].get(style, {}) if style else {}
    own = "character" in st
    pick = st if own else base
    return {
        "voice": f"{pick['character']}（{pick.get('style') or '最初のスタイル'}）",
        "character": pick["character"], "style": pick.get("style"),
        "speed": st.get("speed", 1.0) * (1.0 if own else base.get("speed", 1.0)),
        "vv_pitch": st.get("pitch", 0.0) + (0.0 if own else base.get("pitch", 0.0)),
        "intonation": st.get("intonation", 1.0) * (1.0 if own else base.get("intonation", 1.0)),
        "pitch": 1.0,   # ffmpeg では高さを変えない（VOICEVOX の pitchScale で変える）
        "af": st.get("af", ""),
        "gain_db": st.get("gain_db", 0) + (0 if own else base.get("gain_db", 0)),
        "prompt": "",
    }


_VV_SPEAKERS = None


def vv_url():
    return os.environ.get("VOICEVOX_URL", "http://127.0.0.1:50021")


def vv_request(path, body=None):
    req = urllib.request.Request(vv_url() + path, data=None if body is None else json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST" if body is not None or "?" in path else "GET")
    try:
        with urllib.request.urlopen(req, timeout=120) as res:
            return res.read()
    except urllib.error.URLError as e:
        raise SystemExit(f"VOICEVOX につながらない（{vv_url()}）。アプリを起動しておく：{e}")


def vv_speakers():
    """VOICEVOX のキャラとスタイルの一覧 {キャラ名: [(スタイル名, ID), ...]}。"""
    global _VV_SPEAKERS
    if _VV_SPEAKERS is None:
        data = json.loads(vv_request("/speakers"))
        _VV_SPEAKERS = {sp["name"]: [(st["name"], st["id"]) for st in sp["styles"]] for sp in data}
    return _VV_SPEAKERS


def vv_style_id(character, style=None):
    speakers = vv_speakers()
    norm = lambda n: re.sub(r"\s", "", n)
    match = [n for n in speakers if norm(n) == norm(character)]
    if not match:
        raise SystemExit(f"VOICEVOX にキャラ「{character}」がない。入っているのは：{'、'.join(speakers)}")
    styles = speakers[match[0]]
    if style is None:
        return styles[0][1]
    for name, sid in styles:
        if name == style:
            return sid
    raise SystemExit(f"「{character}」にスタイル「{style}」がない。あるのは：{'、'.join(n for n, _ in styles)}")


def vv_synth(text, s):
    """VOICEVOX で読む。間のマークアップは読点にする（VOICEVOX は読点で間をとる）。"""
    import urllib.parse
    text = text.replace("[pause short]", "、").replace("[pause long]", "、、、").replace("[pause]", "、、")
    sid = vv_style_id(s["character"], s["style"])
    query = json.loads(vv_request(f"/audio_query?text={urllib.parse.quote(text)}&speaker={sid}"))
    query.update({"speedScale": s["speed"], "pitchScale": s["vv_pitch"], "intonationScale": s["intonation"],
                  "outputSamplingRate": RATE, "outputStereo": False})
    return vv_request(f"/synthesis?speaker={sid}", query)


def post(body):
    req = urllib.request.Request("https://texttospeech.googleapis.com/v1/text:synthesize",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json",
                                          "x-goog-api-key": env_key("GOOGLE_TTS_API_KEY")})
    try:
        with urllib.request.urlopen(req, timeout=180) as res:
            return base64.b64decode(json.loads(res.read())["audioContent"])
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Google TTS のエラー {e.code}: {e.read().decode('utf-8', 'replace')[:400]}")


def synth_raw(text, s, backend):
    """TTS の生の音（WAV のバイト列）。同じ内容はキャッシュから返す。"""
    if backend == "voicevox":
        key = json.dumps({"backend": "voicevox", "text": text, **{k: s[k] for k in ("character", "style", "speed", "vv_pitch", "intonation")}},
                         ensure_ascii=False, sort_keys=True)
        cached = CACHE / f"{hashlib.sha1(key.encode('utf-8')).hexdigest()}.wav"
        if not cached.exists():
            print(f"  tts voicevox {s['voice']}: {text[:30]}")
            CACHE.mkdir(parents=True, exist_ok=True)
            cached.write_bytes(vv_synth(text, s))
        return cached
    if backend == "gemini":
        gem_text = (text.replace("[pause short]", "[short pause]").replace("[pause long]", "[long pause]")
                    .replace("[pause]", "[medium pause]"))
        body = {"input": {"prompt": s["prompt"], "text": gem_text} if s["prompt"] else {"text": gem_text},
                "voice": {"languageCode": "ja-JP", "name": s["gemini_voice"], "modelName": GEMINI_MODEL},
                "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": RATE}}
    else:
        field = "markup" if TAG_RE.search(text) else "text"
        body = {"input": {field: text},
                "voice": {"languageCode": "ja-JP", "name": s["voice"]},
                "audioConfig": {"audioEncoding": "LINEAR16", "sampleRateHertz": RATE, "speakingRate": s["speed"]}}
    h = hashlib.sha1(json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    cached = CACHE / f"{h}.wav"
    if not cached.exists():
        print(f"  tts {backend} {s['voice'] if backend != 'gemini' else s['gemini_voice']}: {text[:30]}")
        CACHE.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(post(body))
    return cached


def process(raw, out, s, backend):
    """前後の無音を切り、高さ・効果・音量をそろえる。"""
    trim = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.02,areverse,"
            "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.04,areverse")
    filters = [trim]
    if s["pitch"] != 1.0:
        filters.append(f"asetrate={RATE * s['pitch']:.0f},aresample={RATE},atempo={1 / s['pitch']:.4f}")
    if s["af"]:
        filters.append(s["af"])
    filters += ["loudnorm=I=-16:TP=-1.5:LRA=11", f"volume={s['gain_db']}dB",
                "alimiter=limit=0.89:level=disabled", f"aresample={RATE}"]  # 音量を上げても割れないよう -1dB で抑える
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", str(raw), "-af", ",".join(filters),
                    "-ac", "1", "-ar", str(RATE), "-sample_fmt", "s16", str(out)], check=True)


def emphasize(path, start, end, db):
    """start〜end 秒（マイナスは終わりからの秒）だけ音量を db 上げる。境目は 40ms でなめらかにつなぎ、
    上げたぶん割れないよう、最後に -1dB の割れ止めをかけ直す。"""
    import numpy as np
    with wave.open(str(path), "rb") as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64)
    dur = len(x) / RATE
    a, b = (start if start >= 0 else dur + start), (end if end >= 0 else dur + end)
    t = np.arange(len(x)) / RATE
    ramp = 0.04
    weight = np.clip(np.minimum((t - a) / ramp + 1, (b - t) / ramp + 1), 0, 1)
    x = x * (1 + (10 ** (db / 20) - 1) * weight)
    tmp = path.with_suffix(".emph.wav")
    with wave.open(str(tmp), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(x.clip(-32768, 32767).astype("<i2").tobytes())
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", str(tmp), "-af", "alimiter=limit=0.89:level=disabled",
                    "-ar", str(RATE), "-sample_fmt", "s16", str(path)], check=True)
    tmp.unlink()


def read_pcm(path):
    with wave.open(str(path), "rb") as w:
        a = array.array("h")
        a.frombytes(w.readframes(w.getnframes()))
        return a


# ---------- つなぐ ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--backend", default="chirp", choices=["chirp", "gemini", "voicevox"])
    ap.add_argument("--voices", help="voices.json の代わりに使う声の設定（聴き比べ用）")
    ap.add_argument("--name", help="出力の名前（build/<名前>/。省くと台本の名前）")
    args = ap.parse_args()
    cfg = json.loads(Path(args.voices or Path(__file__).parent / "voices.json").read_text(encoding="utf-8-sig"))
    name = args.name or Path(args.script).stem
    out_dir = ROOT / "build" / name
    seg_dir = out_dir / f"seg_{args.backend}"
    seg_dir.mkdir(parents=True, exist_ok=True)

    placed, timeline = [], []  # placed: (開始サンプル, pcm, 話し手)
    events = {"lines": [], "hits": [], "hit_levels": [], "looks": []}  # 動画用（秒）。hit_levels は hits と同じ順の叩く強さ（1〜3）
    look_from = None  # 見つめ合いが始まった時刻。次のセリフが終わるまで続ける
    prev_start, prev_end = 0, int(0.5 * RATE)
    combo, lines, meta = parse(args.script)
    if combo not in cfg["combos"]:
        raise SystemExit(f"voices.json の combos に '{combo}' がない")
    print(f"コンビ: {combo}")
    tk = cfg["combos"][combo]["tsukkomi"]
    for i, (who, gap, segs, shown, hit) in enumerate(lines):
        if who == "LOOK":  # 黙って見つめ合う。間だけ空けて、次のセリフまで相手を見る
            look_from = prev_end
            prev_start, prev_end = prev_end, prev_end + int(gap * RATE)
            continue
        if gap is None and look_from is not None:
            gap = 0.0
        if gap is None:  # ボケに返すツッコミは語尾にかぶせる。それ以外は少し間をあける
            gap = -cfg["reply_overlap"] if who == "B" and i > 0 and lines[i - 1][0] == "A" else cfg["default_gap"]
        if hit:  # 叩くツッコミ：頭に「ワッーーツ！」「えぐーー！」など（別の音声にして頭を大きく）、語尾も大きく、前のセリフの語尾にかぶせる
            segs = [(tk["prefix"], None, tk["prefix"])] + segs
            shown = f"{tk['prefix']} {shown}"
            gap = min(gap, -tk["overlap"])
        start = max(prev_start + int(0.3 * RATE), prev_end + int(gap * RATE))
        line_segs = []  # 吹き出し用：区切りごとの時刻と表示の字
        end = start
        for speaker in (["A", "B"] if who == "AB" else [who]):
            t = start
            for j, (text, style, disp) in enumerate(segs):
                s = settings(cfg, combo, speaker, style, args.backend)
                text = reading(text, cfg, args.backend)
                seg =seg_dir / f"{i:02d}_{speaker}_{j}.wav"
                process(synth_raw(text, s, args.backend), seg, s, args.backend)
                if hit and j == 0:
                    emphasize(seg, 0, tk["head_sec"], tk["head_db"])
                if hit and j == len(segs) - 1:
                    emphasize(seg, -tk["tail_sec"], -0.0, tk["tail_db"])
                pcm = read_pcm(seg)
                spoken_chars = len(TAG_RE.sub("", text))
                if len(pcm) / RATE > 2.0 and len(pcm) / RATE > 0.3 * spoken_chars:  # Chirp がまれに語尾を何秒も伸ばす
                    print(f"  ！ 長すぎる声 {seg.name}: {len(pcm) / RATE:.1f} 秒 / {spoken_chars} 文字「{text[:20]}」")
                if who == "AB":  # 2 人の声を重ねると割れるので、1 人ずつ 4dB 下げる
                    pcm = array.array("h", (int(v * 0.63) for v in pcm))
                placed.append((t, pcm, speaker))
                line_segs.append({"who": speaker, "start": round(t / RATE, 3), "end": round((t + len(pcm)) / RATE, 3),
                                  "text": disp, "style": style})
                t += len(pcm) + int(cfg["join_gap"] * RATE)
            end = max(end, t - int(cfg["join_gap"] * RATE))
        timeline.append(f"{start / RATE // 60:02.0f}:{start / RATE % 60:05.2f}  {who + '!' * hit:<4} {shown}")
        prev_start, prev_end = start, end
        events["lines"].append({"who": who, "start": round(start / RATE, 3), "end": round(end / RATE, 3), "hit": hit, "text": shown,
                                "segs": line_segs})
        if hit:
            events["hits"].append(round(start / RATE, 3))
            events["hit_levels"].append(hit)
        if look_from is not None:
            events["looks"].append([round(look_from / RATE, 3), round(end / RATE, 3)])
            look_from = None

    total = prev_end + int(1.0 * RATE)
    mix = array.array("i", bytes(4 * total))
    for t, pcm, _ in placed:
        for k, v in enumerate(pcm):
            mix[t + k] += v
    out = array.array("h", (max(-32768, min(32767, v)) for v in mix))
    wav = out_dir / f"{name}_{args.backend}.wav"
    raw = wav.with_suffix(".raw.wav")
    with wave.open(str(raw), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(out.tobytes())
    # セリフが重なったところで割れないよう、-1dB で抑える
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", str(raw), "-af", "alimiter=limit=0.89:level=disabled",
                    "-ar", str(RATE), str(wav)], check=True)
    raw.unlink()
    mp3 = wav.with_suffix(".mp3")
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", str(wav), "-b:a", "192k", str(mp3)], check=True)
    (out_dir / f"timeline_{args.backend}.txt").write_text("\n".join(timeline) + "\n", encoding="utf-8")
    # 口パク用：話し手ごとに、1 コマ（1/30 秒）ずつの声の大きさ（RMS、0〜1）
    import numpy as np
    hop = RATE // FPS
    mouth = {"A": np.zeros(total // hop + 1), "B": np.zeros(total // hop + 1)}
    for t, pcm, speaker in placed:
        x = np.frombuffer(pcm.tobytes(), dtype="<i2").astype(np.float64) / 32768
        n = len(x) // hop
        rms = np.sqrt(np.mean(x[:n * hop].reshape(n, hop) ** 2, axis=1))
        f0 = t // hop
        mouth[speaker][f0:f0 + n] = np.maximum(mouth[speaker][f0:f0 + n], rms)
    events.update({"combo": combo, "title": meta.get("title", ""), "theme": meta.get("theme", ""),
                   "thumb": [c.strip() for c in meta.get("thumb", "").split("／") if c.strip()], "short": meta.get("short", ""), "fps": FPS, "duration": round(total / RATE, 3), "audio": wav.name,
                   "mouth": {k: [round(float(v), 4) for v in arr] for k, arr in mouth.items()}})
    (out_dir / f"timeline_{args.backend}.json").write_text(json.dumps(events, ensure_ascii=False), encoding="utf-8")
    print("\n".join(timeline))
    print(f"\n長さ {total / RATE:.1f} 秒 → {mp3}")


if __name__ == "__main__":
    main()
