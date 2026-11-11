"""Mainland daily selection; history never expands today's source set."""
from collections import Counter
from datetime import datetime, timedelta, timezone
import statistics

PROFILE = 'guangzhou-100m-v2-baseline-3x4MiB-total-time'
MIN_DOWNLOAD_MBPS = 5
MIN_BASELINE_MBPS = 10
BASELINE_MAX_RATIO = 3


def valid_baseline(before, after):
    a, b = before.get('median_mbps'), after.get('median_mbps')
    return (type(a) in (int, float) and type(b) in (int, float)
            and a >= MIN_BASELINE_MBPS and b >= MIN_BASELINE_MBPS
            and max(a, b) / min(a, b) <= BASELINE_MAX_RATIO)


def eligible(n):
    latency = n.get('basic_latency_ms')
    return (n.get('status') == 'alive' and type(latency) in (int, float)
            and 0 < latency < 1200 and n.get('measurement_profile') == PROFILE)


latency_eligible = eligible


def update_history(previous, results, at, cycle):
    """Keep metric-only history, with one observation per Beijing calendar day."""
    cutoff = datetime.fromisoformat(at) - timedelta(days=7)
    day = datetime.fromisoformat(at).astimezone(timezone(timedelta(hours=8))).date().isoformat()
    history = {}
    for n in results:
        old = previous.get('history', {}).get(n['id'], [])
        # A failed lookup must not erase a known exit's failed-day evidence.
        exit_ip = n.get('exit_ip') or (old[-1].get('exit') if old else None)
        old = [h for h in old if datetime.fromisoformat(h['at']) >= cutoff
               and h.get('profile') == PROFILE and h.get('exit') == exit_ip
               and h.get('day') != day]
        old.append(dict(at=at, day=day, cycle=cycle, profile=PROFILE,
                        exit=exit_ip, ok=eligible(n),
                        speed=n.get('download_mbps'), latency=n.get('basic_latency_ms')))
        history[n['id']] = old[-7:]
    return dict(history=history, numbers=previous.get('numbers', {}))


def choose(state, results):
    candidates = [n for n in results if eligible(n)]
    for n in candidates:
        samples = state['history'][n['id']][-3:]
        speeds = [h['speed'] for h in samples if h['ok'] and h.get('speed') is not None]
        n.update(selection_tier='latency', conservative_mbps=min(speeds) if speeds else None,
                 observation_rounds=len(samples), stable=len(samples) >= 3 and all(h['ok'] for h in samples))
    key = lambda n: (n['basic_latency_ms'], -(n.get('download_mbps') or 0), n['id'])
    counts, exits, chosen = Counter(), set(), []
    for n in sorted(candidates, key=key):
        exit_key = n.get('exit_ip') or n['id']
        if exit_key in exits:
            continue
        numbers = state['numbers'].setdefault(n['country'], {})
        if n['id'] not in numbers:
            numbers[n['id']] = max(numbers.values(), default=0) + 1
        n['serial'] = numbers[n['id']]
        chosen.append(n)
        counts[n['country']] += 1
        exits.add(exit_key)
        if len(chosen) == 30:
            break
    return chosen


def recommendations(nodes):
    from enrich import pick_two
    nodes = [n for n in nodes if eligible(n) and n.get('exit_ip')]
    latency = lambda n: (n['basic_latency_ms'], n['id'])
    speed = lambda n: (-(n.get('download_mbps') or 0), *latency(n))
    service = lambda n, key: n.get('ai', {}).get('services', {}).get(key, {}).get('passed') is True
    dual = pick_two([n for n in nodes if service(n, 'ChatGPT') and service(n, 'Gemini')], latency)
    return dict(ai=dual, clean_ip=[],
                gpt=[] if dual else pick_two([n for n in nodes if service(n, 'ChatGPT')], latency)[:1],
                gemini=[] if dual else pick_two([n for n in nodes if service(n, 'Gemini')], latency)[:1],
                daily=pick_two(nodes, latency)[:1],
                media=pick_two([n for n in nodes if n['media']['all_passed']], speed)[:1],
                download=pick_two([n for n in nodes if n.get('download_mbps')], speed))
