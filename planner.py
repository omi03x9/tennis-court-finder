"""Plan uninterrupted use within one facility, preferring fewer court changes."""
from functools import lru_cache
from sources import hhmm


def plan_facility(courts, start, end):
    available = []
    for index, court in enumerate(courts):
        for s in court['slots']:
            if s['available'] and s['end'] > start and s['start'] < end:
                available.append((index, s['start'], s['end']))

    @lru_cache(None)
    def solve(position, last_court):
        if position >= end:
            return (0, 0, 0), ()
        best = None
        for ci, bs, be in available:
            if not bs <= position < be:
                continue
            # Switch at a public reservation boundary, or inside a covering slot.
            stop = min(be, end)
            following = solve(stop, ci)
            if following is None:
                continue
            score, path = following
            change = int(last_court != -1 and last_court != ci)
            extra = max(0, position - bs) + max(0, be - end)
            score = (score[0] + change, score[1] + extra, score[2] + 1)
            candidate = score, ((ci, bs, be, position, stop),) + path
            if best is None or candidate[0] < best[0]:
                best = candidate
        return best

    answer = solve(start, -1)
    if answer is None:
        return None
    score, path = answer
    segments = []
    for ci, bs, be, use_start, use_end in path:
        name = courts[ci]['court']
        # Merge consecutive public slots on the same court.
        if segments and segments[-1]['court'] == name and segments[-1]['useEndMinutes'] == use_start:
            previous = segments[-1]
            previous['useEndMinutes'] = use_end
            previous['bookingEndMinutes'] = max(previous['bookingEndMinutes'], be)
        else:
            segments.append({'court': name, 'useStartMinutes': use_start,
                'useEndMinutes': use_end, 'bookingStartMinutes': bs, 'bookingEndMinutes': be})
    for segment in segments:
        segment.update(useStart=hhmm(segment['useStartMinutes']), useEnd=hhmm(segment['useEndMinutes']),
            bookingStart=hhmm(segment['bookingStartMinutes']), bookingEnd=hhmm(segment['bookingEndMinutes']))
        if courts[0]['city'] == 'abiko':
            # The official maximum is 3 hours per reservation. Separate adjacent reservations.
            segment['bookingUnits'] = [
                {'start': hhmm(t), 'end': hhmm(min(t + 180, segment['bookingEndMinutes']))}
                for t in range(segment['bookingStartMinutes'], segment['bookingEndMinutes'], 180)]
        else:
            segment['bookingUnits'] = [{'start': segment['bookingStart'], 'end': segment['bookingEnd']}]
    return {'city': courts[0]['city'], 'facility': courts[0]['facility'],
            'sourceUrl': courts[0]['sourceUrl'], 'changes': score[0], 'extraMinutes': score[1],
            'segments': segments, 'notes': sorted({c['note'] for c in courts if c['note']})}


def plan_results(source_results, start, end):
    groups = {}
    for result in source_results:
        for court in result['courts']:
            groups.setdefault((court['city'], court['facility']), []).append(court)
    plans = []
    for courts in groups.values():
        continuous = [plan_facility([court], start, end) for court in courts]
        continuous = sorted((p for p in continuous if p), key=lambda p: p['extraMinutes'])
        best = continuous[0] if continuous else plan_facility(courts, start, end)
        if best:
            best['alternatives'] = [{'segments': p['segments'], 'extraMinutes': p['extraMinutes']}
                                    for p in continuous[1:]]
            plans.append(best)
    return sorted((p for p in plans if p is not None),
                  key=lambda p: (p['changes'], p['extraMinutes'], p['facility']))
