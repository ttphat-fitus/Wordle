import os
import json
import random


def load_vocab():
    base = os.path.dirname(__file__)
    path = os.path.join(base, 'data', 'vocabulary.json')
    if not os.path.exists(path):
        raise FileNotFoundError(f"Required vocabulary file not found: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, dict):
        words = [w.lower() for w in data.keys() if isinstance(w, str) and len(w) == 5 and w.isalpha()]
    elif isinstance(data, list):
        words = [w.lower() for w in data if isinstance(w, str) and len(w) == 5 and w.isalpha()]
    else:
        raise RuntimeError(f"Unexpected vocabulary format in {path}")
    if not words:
        raise RuntimeError(f"No valid 5-letter words found in {path}")
    return sorted(set(words))


_VOCAB_CACHE = None


def get_vocab(reload: bool = False):
    global _VOCAB_CACHE
    if reload or _VOCAB_CACHE is None:
        _VOCAB_CACHE = load_vocab()
    return _VOCAB_CACHE


def pick_daily_word(vocab):
    return random.choice(vocab)


class Judge:
    @staticmethod
    def evaluate(guess: str, answer: str):
        guess = guess.lower()
        answer = answer.lower()
        res = [0] * len(guess)
        remaining = {}
        for i, (g, a) in enumerate(zip(guess, answer)):
            if g == a:
                res[i] = 2
            else:
                remaining[a] = remaining.get(a, 0) + 1
        for i, g in enumerate(guess):
            if res[i] == 0 and remaining.get(g, 0) > 0:
                res[i] = 1
                remaining[g] -= 1
        return res
