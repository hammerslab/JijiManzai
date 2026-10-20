"""ツッコミの効果音をプログラムで作る（素材を借りない）。

    python proto/gen_sfx.py

できるもの：assets/audio/slap.wav（バシッ。強め）、assets/audio/pashi.wav（パシッ。軽め）
"""
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RATE = 48000


def bandpass(x, lo, hi):
    """FFT で周波数を切り出す（短い音なので素朴な方法で足りる）。"""
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / RATE)
    spec[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(spec, len(x))


def slap(dur=0.28, crack_hz=(1200, 6000), crack_decay=0.035, thump_hz=140, thump_gain=0.9, seed=1):
    rng = np.random.default_rng(seed)
    t = np.arange(int(dur * RATE)) / RATE
    # 手が当たる「パン」：帯域を絞った雑音を一気に減衰させる
    crack = bandpass(rng.standard_normal(len(t)), *crack_hz) * np.exp(-t / crack_decay)
    # 体に響く「ドッ」：低い音を少しだけ下げながら減衰
    thump = np.sin(2 * np.pi * thump_hz * t * (1 - 0.35 * t / dur)) * np.exp(-t / 0.05) * thump_gain
    # 立ち上がりの「チッ」：ごく短い高い雑音
    click = bandpass(rng.standard_normal(len(t)), 4000, 12000) * np.exp(-t / 0.004) * 0.8
    # 部屋の響き：小さな遅れの反射を 3 つ
    x = crack + thump + click
    for delay, g in ((0.011, 0.35), (0.023, 0.2), (0.041, 0.12)):
        n = int(delay * RATE)
        x[n:] += x[:-n] * g
    attack = np.minimum(1, t / 0.0015)
    x = x * attack
    return x / np.max(np.abs(x)) * 0.89


def save(name, x):
    out = ROOT / "assets" / "audio" / name
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((x * 32767).astype("<i2").tobytes())
    print(out)


def applause(dur=4.0, peak=0.6, fade_in=0.4, seed=3):
    """拍手。短い「パチッ」をたくさん、ばらばらの時刻に鳴らす。頭で盛り上がって、だんだん減っていく。"""
    rng = np.random.default_rng(seed)
    n = int(dur * RATE)
    x = np.zeros(n + RATE)
    clap_len = int(0.03 * RATE)
    tc = np.arange(clap_len) / RATE
    t = 0.0
    while t < dur:
        density = 45 * min(1, t / fade_in + 0.2) * (1 - t / dur) ** 1.5 + 2   # 1 秒あたりの拍手の数
        t += rng.exponential(1 / density)
        lo = rng.uniform(600, 1500)
        clap = bandpass(rng.standard_normal(clap_len), lo, lo * 4) * np.exp(-tc / rng.uniform(0.006, 0.014))
        i = int(t * RATE)
        if i + clap_len > len(x):
            break
        x[i:i + clap_len] += clap * rng.uniform(0.3, 1.0)
    for delay, g in ((0.017, 0.4), (0.031, 0.3), (0.053, 0.2), (0.089, 0.12)):   # 客席の響き
        k = int(delay * RATE)
        x[k:] += x[:-k] * g
    x = x[:n]
    x *= np.minimum(1, np.arange(n) / (0.05 * RATE)) * np.minimum(1, (n - np.arange(n)) / (0.5 * RATE))
    return x / np.max(np.abs(x)) * peak


NOTE = {n: 440 * 2 ** ((i - 9) / 12) for i, n in enumerate("C C# D D# E F F# G G# A A# B".split())}


def tone(name, octave, length, kind="saw", decay=5.0, gain=1.0):
    f = NOTE[name] * 2 ** (octave - 4)
    t = np.arange(int(length * RATE)) / RATE
    if kind == "saw":     # 金管っぽい音（倍音を足して作る）
        w = sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, 9))
    elif kind == "square":
        w = sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, 12, 2))
    else:                 # ベース
        w = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)
    env = np.minimum(1, t / 0.01) * np.exp(-t * decay / length)
    return w * env * gain


def debayashi(bars=4, bpm=150):
    """出囃子（登場・退場の曲）。明るい 4 小節を、ベース・手拍子・金管っぽいメロディーで。最後は伸ばして終わる。"""
    beat = 60 / bpm
    n = int((bars * 4 + 2) * beat * RATE)
    x = np.zeros(n + RATE)

    def put(sig, at_beat):
        i = int(at_beat * beat * RATE)
        x[i:i + len(sig)] += sig[:len(x) - i]
    # メロディー（拍, 音, オクターブ, 長さ[拍]）
    melody = [(0, "C", 5, .5), (.5, "E", 5, .5), (1, "G", 5, 1), (2, "A", 5, .5), (2.5, "G", 5, .5), (3, "E", 5, 1),
              (4, "F", 5, .5), (4.5, "A", 5, .5), (5, "C", 6, 1), (6, "A", 5, .5), (6.5, "G", 5, .5), (7, "F", 5, 1),
              (8, "E", 5, .5), (8.5, "G", 5, .5), (9, "C", 6, .5), (9.5, "B", 5, .5), (10, "A", 5, .5), (10.5, "G", 5, .5), (11, "E", 5, 1),
              (12, "D", 5, .5), (12.5, "E", 5, .5), (13, "G", 5, .5), (13.5, "B", 5, .5), (14, "C", 6, 2.5)]
    for b, nm, o, ln in melody:
        put(tone(nm, o, ln * beat, "saw", 2.5, 0.22), b)
        put(tone(nm, o - 1, ln * beat, "square", 2.5, 0.08), b)
    bass = ["C", "C", "F", "F", "C", "C", "G", "G"]
    for i in range(16):
        put(tone(bass[i // 2], 2, beat * 0.9, "bass", 3, 0.5), i)
    put(tone("C", 2, beat * 2.5, "bass", 2, 0.5), 16)
    rng = np.random.default_rng(5)
    for i in range(16):
        if i % 2 == 1:   # 2 拍目と 4 拍目の手拍子
            clap = bandpass(rng.standard_normal(int(0.06 * RATE)), 900, 5000) * np.exp(-np.arange(int(0.06 * RATE)) / RATE / 0.012)
            put(clap * 0.5, i)
        kick_t = np.arange(int(0.15 * RATE)) / RATE
        put(np.sin(2 * np.pi * (120 - 300 * kick_t) * kick_t) * np.exp(-kick_t / 0.05) * 0.6, i)
    x = x[:n]
    x *= np.minimum(1, (n - np.arange(n)) / (0.3 * RATE))
    return x / np.max(np.abs(x)) * 0.8


if __name__ == "__main__":
    save("slap.wav", slap())
    save("pashi.wav", slap(dur=0.18, crack_hz=(2000, 8000), crack_decay=0.022, thump_hz=220, thump_gain=0.35, seed=2))
    save("applause.wav", applause())
    save("debayashi.wav", debayashi())
