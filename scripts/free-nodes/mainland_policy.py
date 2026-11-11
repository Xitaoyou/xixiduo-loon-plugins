"""Mainland selection with bounded published-node retesting and country coverage."""
from collections import Counter
from datetime import datetime, timedelta, timezone
import statistics

PROFILE = 'guangzhou-100m-v2-baseline-3x4MiB-total-time'
MIN_DOWNLOAD_MBPS = 5
MIN_BASELINE_MBPS = 10
BASELINE_MAX_RATIO = 3
PREFERRED_COUNTRIES = ('US', 'JP', 'SG', 'HK', 'TW', 'GB', 'DE', 'IT')


def valid_baseline(before, after):
    a, b = before.get('median_mbps'), after.get('median_mbps')
    return (type(a) in (int, float) and type(b) in (int, float)
            and a >= MIN_BASELINE_MBPS and b >= MIN_BASELINE_MBPS
            and max(a, b) / min(a, b) <= BASELINE_MAX_RATIO)


def eligible(n):
    latency = n.get('basic_latency_ms')
    return (n.get('status') == 'alive' and type(latency) in (int, float)
            and 0 < latency <= (2500 if n.get('country') in PREFERRED_COUNTRIES else 1500) and n.get('measurement_profile') == PROFILE)


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
        samples = state['history'][n['id']][-7:]
        speeds = [h['speed'] for h in samples if h['ok'] and h.get('speed') is not None]
        # One sample per Beijing day; recent failures matter more than old successes.
        weights = list(range(1, len(samples) + 1))
        success = sum(w for w, h in zip(weights, samples) if h['ok']) / sum(weights)
        prior_selected = sum(h.get('selected', False) and h['ok'] for h in samples[:-1])
        bonus = .25 * min(prior_selected / 5, 1) * success
        effective = n['basic_latency_ms'] * (1 + .5 * (1-success) - bonus)
        n.update(selection_tier='latency', conservative_mbps=min(speeds) if speeds else None,
                 observation_rounds=len(samples), stable=len(samples) >= 3 and all(h['ok'] for h in samples[-3:]),
                 recent_selected_days=prior_selected, recent_success_rate=round(success, 4),
                 stability_bonus=round(bonus, 4), stability_rank_ms=round(effective, 2))
    key = stability_key
    counts, exits, chosen = Counter(), set(), []
    def add(n, tier):
        exit_key = n.get('exit_ip') or n['id']
        if exit_key in exits or len(chosen) >= 30:
            return False
        numbers = state['numbers'].setdefault(n['country'], {})
        if n['id'] not in numbers:
            numbers[n['id']] = max(numbers.values(), default=0) + 1
        n['serial'] = numbers[n['id']]
        n['selection_tier'] = tier
        chosen.append(n)
        counts[n['country']] += 1
        exits.add(exit_key)
        return True
    # Reserve one qualified exit per common country before the global low-latency fill.
    quality_key = lambda n: (-n.get('quality', {}).get('grade', 1), *key(n))
    for country in PREFERRED_COUNTRIES:
        normal = [n for n in candidates if n['country'] == country and n['basic_latency_ms'] <= 1500]
        options = normal or [n for n in candidates if n['country'] == country]
        for n in sorted(options, key=quality_key):
            if add(n, 'latency' if n['basic_latency_ms'] <= 1500 else 'country_fallback'):
                break
    for n in sorted(candidates, key=key):
        if n['basic_latency_ms'] <= 1500:
            add(n, 'latency')
    for n in chosen:
        state['history'][n['id']][-1]['selected'] = True
    return chosen


def stability_key(n):
    return (n.get('stability_rank_ms', n['basic_latency_ms']),
            -n.get('quality', {}).get('grade', 1),
            -(n.get('download_mbps') or 0), n['id'])


def recommendations(nodes):
    from enrich import pick_two
    nodes = [n for n in nodes if eligible(n) and n.get('exit_ip')]
    latency = lambda n: (n['basic_latency_ms'], n['id'])
    speed = lambda n: (-(n.get('download_mbps') or 0), *latency(n))
    service = lambda n, key: n.get('ai', {}).get('services', {}).get(key, {}).get('passed') is True
    dual = pick_two([n for n in nodes if service(n, 'ChatGPT') and service(n, 'Gemini')], stability_key)
    return dict(ai=dual, clean_ip=[],
                gpt=[] if dual else pick_two([n for n in nodes if service(n, 'ChatGPT')], stability_key)[:1],
                gemini=[] if dual else pick_two([n for n in nodes if service(n, 'Gemini')], stability_key)[:1],
                daily=pick_two(nodes, latency)[:1],
                media=pick_two([n for n in nodes if n['media']['all_passed']], speed)[:1],
                download=pick_two([n for n in nodes if n.get('download_mbps')], speed))
