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
    latency, speed = n.get('basic_latency_ms'), n.get('download_mbps')
    return (n.get('status') == 'alive' and latency is not None and 0 < latency <= 1000
            and speed is not None and speed >= MIN_DOWNLOAD_MBPS and n.get('exit_ip')
            and n.get('ai', {}).get('pass_count', 0) >= 2
            and n.get('quality', {}).get('grade', 0) >= 1
            and n.get('measurement_profile') == PROFILE)


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
    candidates = []
    for n in results:
        if not eligible(n):
            continue
        samples = state['history'][n['id']][-3:]
        # Once three daily samples exist, failures remain part of stability evidence.
        if len(samples) >= 3 and not all(s['ok'] for s in samples):
            continue
        n['conservative_mbps'] = min(s['speed'] for s in samples if s['ok'])
        n['observation_rounds'] = len(samples)
        n['stable'] = len(samples) >= 3
        n['selection_score'] = n['conservative_mbps']
        candidates.append(n)
    key = lambda n: (-n['quality']['grade'], n['quality'].get('risk_score')
                     if n['quality'].get('risk_score') is not None else 101,
                     n['basic_latency_ms'], -n['conservative_mbps'], n['id'])
    counts, exits, chosen = Counter(), set(), []
    for n in sorted(candidates, key=key):
        if n['exit_ip'] in exits or counts[n['country']] >= 4:
            continue
        numbers = state['numbers'].setdefault(n['country'], {})
        if n['id'] not in numbers:
            numbers[n['id']] = max(numbers.values(), default=0) + 1
        n['serial'] = numbers[n['id']]
        chosen.append(n)
        counts[n['country']] += 1
        exits.add(n['exit_ip'])
        if len(chosen) == 30:
            break
    return chosen


def recommendations(nodes):
    from enrich import pick_two, quality_key, clean_ip_best
    ai = lambda n: (-n['ai']['pass_count'], *quality_key(n['quality']),
                    n['basic_latency_ms'], -n['conservative_mbps'], n['id'])
    speed = lambda n: (-n['conservative_mbps'], n['basic_latency_ms'],
                       *quality_key(n['quality']), n['id'])
    return dict(ai=pick_two(nodes, ai),
                media=pick_two([n for n in nodes if n['media']['all_passed']], speed),
                download=pick_two(nodes, speed), clean_ip=clean_ip_best(nodes))
