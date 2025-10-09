import argparse
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


RUSSIAN_STOPWORDS: set[str] = {
    "и",
    "в",
    "во",
    "не",
    "что",
    "он",
    "на",
    "я",
    "с",
    "со",
    "как",
    "а",
    "то",
    "все",
    "она",
    "так",
    "его",
    "но",
    "да",
    "ты",
    "к",
    "у",
    "же",
    "вы",
    "за",
    "бы",
    "по",
    "только",
    "ее",
    "мне",
    "было",
    "вот",
    "от",
    "меня",
    "еще",
    "нет",
    "о",
    "из",
    "ему",
    "теперь",
    "когда",
    "даже",
    "ну",
    "вдруг",
    "ли",
    "если",
    "уже",
    "или",
    "ни",
    "быть",
    "был",
    "него",
    "до",
    "вас",
    "нибудь",
    "опять",
    "уж",
    "вам",
    "они",
    "тут",
    "где",
    "есть",
    "надо",
    "ней",
    "для",
    "мы",
    "тебя",
    "их",
    "чем",
    "была",
    "сам",
    "чтоб",
    "без",
    "будто",
    "чего",
    "раз",
    "тоже",
    "себя",
    "свои",
    "при",
    "ужас",
    "это",
    "будет",
    # доп. разговорные/служебные
    "здравствуйте",
    "привет",
    "добрый",
    "доброго",
    "дня",
    "день",
    "вечер",
    "пожалуйста",
    "пожалуйcта",
    "спасибо",
    "пж",
    "пжлст",
    "подскажите",
    "подскажите",
    "подскажите",
    "подскажите",
    "скажите",
    "можно",
    "нужно",
    "нужен",
    "нужна",
    "давайте",
    "коллеги",
    "всем",
    "кто",
    "что",
    "где",
    "когда",
    "завтра",
    "сегодня",
    "вчера",
}

DOMAIN_STOPWORDS: set[str] = {
    "пвз",
    "озон",
    "ozon",
    "вб",
    "wb",
    "wildberries",
    "вайлдберриз",
    "wbpvz",
    "ozonpvz",
    "ozonapvz",
    "ссылка",
    "https",
    "http",
    "me",
    "ru",
    "vod",
    "cdnvideo",
}

TOKEN_RE = re.compile(r"[a-zA-Zа-яА-Я0-9ёЁ]+", re.UNICODE)


def normalize_token(token: str) -> str:
    t = token.lower()
    replacements = {
        "oзон": "озон",
        "озоn": "озон",
        "ozoн": "озон",
        "вб": "вайлдберриз",
        "wb": "вайлдберриз",
        "wildberries": "вайлдберриз",
        "озon": "озон",
    }
    return replacements.get(t, t)


def extract_text_from_message(message: dict) -> str:
    text = message.get("text")
    if isinstance(text, str):
        return text
    if isinstance(text, list):
        parts: List[str] = []
        for item in text:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                # Telegram export can have dicts like {"type": "link", "text": "..."}
                itext = item.get("text")
                if isinstance(itext, str):
                    parts.append(itext)
        return " ".join(parts)
    return ""


def tokenize(text: str) -> List[str]:
    tokens = [normalize_token(m.group(0)) for m in TOKEN_RE.finditer(text.lower())]
    filtered = [t for t in tokens if len(t) >= 2 and t not in RUSSIAN_STOPWORDS and t not in DOMAIN_STOPWORDS]
    return filtered


def generate_ngrams(tokens: List[str], n: int) -> Iterable[Tuple[str, ...]]:
    return (tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1))


def count_ngrams(messages_tokens: Iterable[List[str]], n_values: Tuple[int, ...] = (1, 2, 3)) -> Dict[int, Counter]:
    counters: Dict[int, Counter] = {n: Counter() for n in n_values}
    for tokens in messages_tokens:
        for n in n_values:
            counters[n].update(generate_ngrams(tokens, n))
    return counters


def get_top(counter: Counter, top_k: int, min_freq: int) -> List[Tuple[str, int]]:
    items: List[Tuple[str, int]] = []
    for gram, cnt in counter.most_common():
        if cnt < min_freq:
            break
        gram_text = " ".join(gram) if isinstance(gram, tuple) else str(gram)
        items.append((gram_text, cnt))
        if len(items) >= top_k:
            break
    return items


@dataclass
class Topic:
    name: str
    keywords: List[str]
    top_ngrams: List[Tuple[str, int]]
    examples: List[str]


TOPIC_SEEDS: List[Tuple[str, List[str]]] = [
    ("Оплата и ставки", ["ставк", "оплат", "выплат", "прем", "доплат", "час"]),
    ("Невыходы и подмены", ["невыход", "подмен", "замен", "срыв", "форс"]),
    ("Штрафы и претензии", ["штраф", "претенз", "акт", "наруш", "требован", "провер"]),
    ("График и нагрузка", ["график", "смен", "нагруз", "день", "ноч", "выходн", "вахт", "метро", "район"]),
    ("Платформы и бренды", ["озон", "вайлдберриз", "ozon", "wb"]),
]


def assign_topics(
    top_ngrams: List[Tuple[str, int]],
    messages: List[str],
    max_examples: int,
) -> List[Topic]:
    topics: List[Topic] = []
    for name, seeds in TOPIC_SEEDS:
        matched = [(g, c) for g, c in top_ngrams if any(s in g for s in seeds)]
        examples: List[str] = []
        if matched:
            seed_union = seeds
            for msg in messages:
                lm = msg.lower()
                if any(s in lm for s in seed_union):
                    examples.append(truncate_example(msg))
                    if len(examples) >= max_examples:
                        break
        topics.append(Topic(name=name, keywords=seeds, top_ngrams=matched[:10], examples=examples))
    # Остальное
    used = {g for t in topics for g, _ in t.top_ngrams}
    other = [(g, c) for g, c in top_ngrams if g not in used][:10]
    if other:
        other_examples: List[str] = []
        for msg in messages:
            lm = msg.lower()
            if any(g in lm for g, _ in other):
                other_examples.append(truncate_example(msg))
                if len(other_examples) >= max_examples:
                    break
        topics.append(Topic(name="Прочие темы", keywords=[], top_ngrams=other, examples=other_examples))
    return topics


def truncate_example(text: str, max_len: int = 220) -> str:
    t = re.sub(r"\s+", " ", text).strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def load_messages(json_path: Path, max_messages: Optional[int]) -> List[str]:
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    messages_raw = data.get("messages", [])
    texts: List[str] = []
    for i, m in enumerate(messages_raw):
        text = extract_text_from_message(m)
        if text:
            texts.append(text)
        if max_messages is not None and len(texts) >= max_messages:
            break
    return texts


def analyze_chat(input_dir: Path, output_dir: Path, top_k: int, min_freq: int, max_examples: int, max_messages: Optional[int]) -> None:
    json_path = input_dir / "result.json"
    if not json_path.exists():
        raise FileNotFoundError(f"No result.json in {input_dir}")

    texts = load_messages(json_path, max_messages)
    tokens_per_msg = [tokenize(t) for t in texts]
    ngram_counters = count_ngrams(tokens_per_msg, (1, 2, 3))

    top_uni = get_top(ngram_counters[1], top_k=top_k, min_freq=min_freq)
    top_bi = get_top(ngram_counters[2], top_k=top_k, min_freq=max(2, min_freq))
    top_tri = get_top(ngram_counters[3], top_k=top_k, min_freq=max(2, min_freq))

    merged: List[Tuple[str, int]] = sorted(top_bi + top_tri + top_uni, key=lambda x: x[1], reverse=True)
    topics = assign_topics(merged, texts, max_examples=max_examples)

    output_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "messages_processed": len(texts),
        "top_unigrams": top_uni,
        "top_bigrams": top_bi,
        "top_trigrams": top_tri,
        "topics": [
            {
                "name": t.name,
                "keywords": t.keywords,
                "top_ngrams": t.top_ngrams,
                "examples": t.examples,
            }
            for t in topics
        ],
    }
    with (output_dir / "topics.json").open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # Markdown summary
    lines: List[str] = []
    lines.append(f"# Темы и кластеры — {input_dir.name}")
    lines.append("")
    lines.append(f"Сообщений обработано: {len(texts)}")
    lines.append("")
    for t in topics:
        lines.append(f"## {t.name}")
        if t.keywords:
            lines.append(f"Ключевые слова: {', '.join(t.keywords)}")
        if t.top_ngrams:
            lines.append("Топ n-грамм:")
            for g, c in t.top_ngrams[:10]:
                lines.append(f"- {g} — {c}")
        if t.examples:
            lines.append("Примеры:")
            for ex in t.examples[:5]:
                lines.append(f"- {ex}")
        lines.append("")
    with (output_dir / "summary.md").open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def compute_pmi(tokens_per_msg: List[List[str]], window: int = 4, min_count: int = 20) -> Dict[Tuple[str, str], float]:
    """Simplified PMI over a sliding window to expand topic seeds.
    Returns pair->PMI for pairs meeting min_count.
    """
    from math import log

    total_tokens = sum(len(t) for t in tokens_per_msg)
    if total_tokens == 0:
        return {}
    freq: Counter = Counter()
    pair_freq: Counter = Counter()
    for tokens in tokens_per_msg:
        L = len(tokens)
        for i, w in enumerate(tokens):
            freq[w] += 1
            j_end = min(L, i + window)
            for j in range(i + 1, j_end):
                a, b = tokens[i], tokens[j]
                if a == b:
                    continue
                if a > b:
                    a, b = b, a
                pair_freq[(a, b)] += 1
    pmi: Dict[Tuple[str, str], float] = {}
    total_pairs = sum(pair_freq.values()) or 1
    for (a, b), c_ab in pair_freq.items():
        if c_ab < min_count:
            continue
        p_a = freq[a] / total_tokens
        p_b = freq[b] / total_tokens
        p_ab = c_ab / total_pairs
        score = log(p_ab / (p_a * p_b) + 1e-12)
        pmi[(a, b)] = score
    return pmi


def expand_seeds_with_pmi(tokens_per_msg: List[List[str]], base_seeds: List[Tuple[str, List[str]]], per_topic: int = 6) -> List[Tuple[str, List[str]]]:
    pmi = compute_pmi(tokens_per_msg)
    by_word: Dict[str, List[Tuple[str, float]]] = defaultdict(list)
    for (a, b), score in pmi.items():
        by_word[a].append((b, score))
        by_word[b].append((a, score))
    expanded: List[Tuple[str, List[str]]] = []
    for name, seeds in base_seeds:
        candidates: Counter = Counter()
        for s in seeds:
            for w, score in by_word.get(s, []):
                if w in seeds:
                    continue
                # Upweight domain-relevant suffixes
                weight = 1.0
                if any(sfx in w for sfx in ("смен", "штраф", "претенз", "ставк", "выплат", "график", "замен")):
                    weight = 1.2
                candidates[w] += score * weight
        top_new = [w for w, _ in candidates.most_common(per_topic)]
        expanded.append((name, list(dict.fromkeys(seeds + top_new))))
    return expanded


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze Telegram chat exports (result.json) and produce simple topics.")
    parser.add_argument("--input-dir", type=str, required=True, help="Path to chat directory containing result.json")
    parser.add_argument("--output-dir", type=str, required=True, help="Directory to write results")
    parser.add_argument("--top-k", type=int, default=200, help="Top n-grams per order")
    parser.add_argument("--min-freq", type=int, default=5, help="Minimum frequency threshold")
    parser.add_argument("--max-examples", type=int, default=10, help="Examples per topic")
    parser.add_argument("--max-messages", type=int, default=20000, help="Max messages to process (for speed)")
    args = parser.parse_args()

    analyze_chat(
        input_dir=Path(args.input_dir),
        output_dir=Path(args.output_dir),
        top_k=args.top_k,
        min_freq=args.min_freq,
        max_examples=args.max_examples,
        max_messages=args.max_messages,
    )


if __name__ == "__main__":
    main()


