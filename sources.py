"""Public availability only. No login or reservation endpoints are called."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone, timedelta
import http.cookiejar
import json
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from lxml import html

JST = timezone(timedelta(hours=9))
SOURCES = {
    'kashiwa': ('柏市', 'https://shisetsu-reservation.city.kashiwa.lg.jp/'),
    'nagareyama': ('流山市', 'https://web136.rsv.ws-scs.jp/nagare/web/'),
    'abiko': ('我孫子市', 'https://www.cm1.eprs.jp/yoyaku-chiba/ew/'),
}


def normalized(text):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', text)).strip()


def minutes(value):
    value = normalized(str(value))
    if ':' in value:
        hour, minute = map(int, value.split(':'))
    else:
        number = int(value)
        hour, minute = divmod(number, 100)
    if not (0 <= hour <= 24 and 0 <= minute < 60) or (hour == 24 and minute):
        raise ValueError('時刻が不正です')
    return hour * 60 + minute


def hhmm(value):
    return f'{value // 60:02d}:{value % 60:02d}'


class SourceError(RuntimeError):
    pass


class Client:
    def __init__(self, root, encoding, deadline):
        self.root, self.encoding, self.deadline = root, encoding, deadline
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.last_request = 0.0

    def get(self, path='', data=None):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise SourceError('照会に時間がかかっています。再度お試しください。')
        pause = max(0, .12 - (time.monotonic() - self.last_request))
        if pause:
            time.sleep(pause)
        url = urllib.parse.urljoin(self.root, path)
        # URLs and actions are fixed in adapters; never take an upstream URL from input.
        if urllib.parse.urlparse(url).netloc != urllib.parse.urlparse(self.root).netloc:
            raise SourceError('照会先が変わりました')
        body = None if data is None else urllib.parse.urlencode(
            data, doseq=True, encoding=self.encoding).encode('ascii')
        request = urllib.request.Request(url, data=body, headers={
            'User-Agent': 'TennisCourtFinder/0.1 (public availability lookup)',
            'Referer': self.root,
        })
        self.last_request = time.monotonic()
        with self.opener.open(request, timeout=min(15, remaining)) as response:
            text = response.read(4_000_000).decode(self.encoding)
        if 'Incapsula incident ID' in text or 'Request unsuccessful' in text:
            raise SourceError('予約サイトが照会を受け付けませんでした')
        return text

    def page(self, path='', data=None):
        return html.fromstring(self.get(path, data))


def court(city, facility, name, slots, note=''):
    return {'city': city, 'facility': facility, 'court': normalized(name),
            'slots': slots, 'note': note, 'sourceUrl': SOURCES[city][1]}


def slot(start, end, status):
    return {'start': start, 'end': end, 'available': status == '空き', 'status': status}


def js_args(value):
    return re.findall(r"'([^']*)'", value or '')


def parse_kashiwa_day(doc):
    tables = doc.xpath('//table[@class="table-style"]')
    if not tables:
        raise SourceError('時間別の空き状況を確認できませんでした')
    rows = tables[0].xpath('./tr | ./tbody/tr')
    if not rows or len(rows) % 2:
        raise SourceError('時間枠の形式が変わりました')
    slots = []
    for pair in range(0, len(rows), 2):
        headers = rows[pair].xpath('./td | ./th')
        cells = rows[pair + 1].xpath('./td | ./th')
        if len(headers) != len(cells):
            raise SourceError('時間枠と空き表示が一致しません')
        for header, cell in zip(headers, cells):
            label = normalized(header.text_content()).replace(' ', '')
            if not label:
                continue
            match = re.fullmatch(r'(\d{1,2}:\d{2})-(\d{1,2}:\d{2})', label)
            if not match:
                raise SourceError('時間枠を読み取れませんでした')
            status = normalized(cell.text_content())
            slots.append(slot(minutes(match[1]), minutes(match[2]), '空き' if status == '○' else status))
    return slots


def kashiwa(day, deadline):
    client = Client(SOURCES['kashiwa'][1], 'utf-8', deadline)
    client.get()
    client.page('index.php', {'op': 'sentaku'})
    client.page('index.php', {'op': 'jyouken'})
    doc = client.page('index.php', {'op': 'kensaku_koma', 'UseYM': day.strftime('%Y%m'),
        'UseDay': str(day.day), 'Type': '01', 'Mokuteki01': '008', 'ShisetsuCode': '0'})
    headings = doc.xpath('//h3/text()')
    if not any('ソフトテニス' in h for h in headings):
        raise SourceError('ソフトテニスの検索条件を確認できませんでした')
    areas = doc.xpath('//div[@class="koma-area"]')
    if not areas:
        raise SourceError('指定日のコート一覧が公開されていません')
    results, errors = [], []
    for area in areas:
        names = area.xpath('./h3/text()')
        if not names:
            raise SourceError('施設名を確認できませんでした')
        facility = normalized(names[0])
        for cell in area.xpath('.//td[@class="name"]'):
            name = normalized(cell.text_content())
            if not any(term in name for term in ['庭球', 'テニス']):
                continue
            try:
                links = cell.xpath('./a/@href')
                if not links:
                    results.append(court('kashiwa', facility, name, [], '利用休止・公開期間外等です。公式画面をご確認ください。'))
                    continue
                query = urllib.parse.parse_qs(urllib.parse.urlparse(links[0]).query)
                if query.get('op') != ['daily'] or query.get('UseDate') != [day.strftime('%Y%m%d')]:
                    raise SourceError('指定日の照会先を確認できませんでした')
                daily = client.page(links[0])
                slots = parse_kashiwa_day(daily)
                results.append(court('kashiwa', facility, name, slots,
                    '柏市の空き表示は市内在住・在勤・在学等の利用条件です。'))
            except Exception as error:
                errors.append(f'{facility} {name}：{friendly_error(error)}')
                if time.monotonic() >= deadline:
                    return results, errors
    if not results and not errors:
        raise SourceError('テニスコートを確認できませんでした')
    return results, errors


def nagareyama(day, deadline):
    client = Client(SOURCES['nagareyama'][1], 'cp932', deadline)
    client.get()
    doc = client.page('rsvWOpeInstSrchVacantAction.do', {
        'displayNo': 'pawab2000', 'displayNoFrm': 'pawab2000',
        'selectAreaBcd': '122203_0', 'selectIcd': '0',
        'selectPpsClPpscd': '100_100120', 'daystart': day.isoformat(),
        'days': '1', 'dayofweekClearFlg': '1', 'timezoneClearFlg': '1'})
    facilities = {o.get('value'): normalized(o.text_content())
                  for o in doc.xpath('//select[@id="mansion-select"]/option')}
    rooms = [(o.get('value'), normalized(o.text_content()))
             for o in doc.xpath('//select[@id="facility-select"]/option') if o.get('value') != '0']
    if not facilities or not rooms:
        raise SourceError('ソフトテニスの対象施設を確認できませんでした')
    results, errors = [], []
    for code, name in rooms:
        facility_code = code[:4]
        facility = facilities.get(facility_code)
        if not facility:
            raise SourceError('コートと施設の対応を確認できませんでした')
        try:
            raw = json.loads(client.get('rsvWOpeInstSrchVacantAjaxAction.do', {
                'displayNo': 'prwrc2000', 'useDay': day.strftime('%Y%m%d'),
                'bldCd': facility_code, 'instCd': code,
                'transVacantMode': '1', 'clearFlag': '0'}))
            if 'ErrManager' in raw or 'result' not in raw:
                raise SourceError('時間別の空き状況を確認できませんでした')
            slots = []
            for row in raw['result']:
                for item in row['timeResult']:
                    if str(item['useDay']) == day.strftime('%Y%m%d'):
                        slots.append(slot(minutes(item['startTime']), minutes(item['endTime']), item['alt']))
            if not slots:
                raise SourceError('指定日の時間枠が公開されていません')
            results.append(court('nagareyama', facility, name, slots))
        except Exception as error:
            errors.append(f'{facility} {name}：{friendly_error(error)}')
            if time.monotonic() >= deadline:
                break
    return results, errors


def abiko(day, deadline):
    client = Client(SOURCES['abiko'][1], 'cp932', deadline)
    client.get()
    client.page('rsvWTransInstSrchVacantAction.do', {'displayNo': 'pawab2000'})
    client.page('rsvWTransInstSrchPpsdAction.do', {'displayNo': 'prwaa1000', 'conditionMode': '2'})
    client.page('rsvWTransInstSrchPpsAction.do', {'displayNo': 'prwbb5000', 'selectPpsdCd': '110'})
    client.page('rsvPrwia1000DispAction.do', {'displayNo': 'prwbb6000',
        'selectAreaCd': '0', 'selectPpsPpsdCd': '110', 'selectPpsCd': '110020',
        'selectMComCd': '0', 'selectPComCd': '0', 'selectCommunityPlaceCd': '0'})
    client.page('rsvPrwia1000NextAction.do', {'displayNo': 'prwia1000', 'selectedCommunityCd': 'A4'})
    client.page('rsvWTransInstSrchBuildAction.do', {'displayNo': 'prwbb1000', 'selectAreaCd': 'A410'})
    doc = client.page('rsvWTransInstSrchInstAction.do', {'displayNo': 'prwbb2000', 'selectBldCd': '0'})
    if doc.xpath('//input[@name="selectPpsCd"]/@value') != ['110020']:
        raise SourceError('ソフトテニスの検索条件を確認できませんでした')
    rooms = {}
    for link in doc.xpath('//a[contains(@href,"sendInstNo")]'):
        text = normalized(link.text_content())
        args = js_args(link.get('href'))
        if 'テニス' in text and args:
            parts = text.split(' ', 1)
            if len(parts) == 2:
                rooms[int(args[-1])] = parts
    if not rooms:
        raise SourceError('我孫子市のテニスコート一覧を確認できませんでした')
    client.page('rsvWTransInstSrchDayWeekAction.do', {'displayNo': 'prwbb3000', 'selectInstNo': '0'})
    y, m, d = str(day.year), str(day.month), str(day.day)
    client.page('rsvWInstSrchVacantAction.do', {
        'displayNo': 'prwbb4000', 'selectYY': y, 'selectMM': m, 'selectDD': d,
        'dispYY': y, 'dispMM': m, 'dispDD': d, 'submmitMode': '0',
        'transVacantMode': '7', 'dispWeekNum': '0', 'dispWeek': ['0'] * 8})
    results, errors = [], []
    for index, (facility, name) in rooms.items():
        try:
            doc = client.page('rsvWInstSrchVacantAction.do', {
                'displayNo': 'prwcb1000', 'transVacantMode': '6', 'srchSelectInstNo': str(index)})
            names = [normalized(a.text_content()) for a in doc.xpath('//a[@target="_blank"]')]
            if normalized(facility + ' ' + name) not in names:
                raise SourceError('コートの表示が検索条件と一致しません')
            tables = doc.xpath('//table[@border="2"]')
            table = next((t for t in tables if t.xpath('./tr[1]/td') and
                          any(re.search(r'\d{2}/\d{2}', cell.text_content())
                              for cell in t.xpath('./tr[1]/td'))), None)
            if table is None:
                raise SourceError('時間別の空き状況を確認できませんでした')
            rows = table.xpath('./tr')
            if len(rows) < 2:
                raise SourceError('時間別表示の形式が変わりました')
            headers = rows[0].xpath('./td')
            target = day.strftime('%m/%d')
            position = next((i for i, h in enumerate(headers) if target in h.text_content()), None)
            if position is None:
                raise SourceError('指定日の時間枠が公開されていません')
            for row in rows[1:]:
                cells = row.xpath('./td')
                if len(cells) != len(headers):
                    raise SourceError('時間枠と日付が一致しません')
                row_name = normalized(cells[0].text_content()) if not normalized(headers[0].text_content()) else name
                if 'テニス' not in row_name:
                    raise SourceError('コート名を確認できませんでした')
                slots = []
                for image in cells[position].xpath('.//img'):
                    text = normalized(image.tail or '')
                    match = re.fullmatch(r'(\d{2}:\d{2})-(\d{2}:\d{2})', text)
                    if not match:
                        raise SourceError('時間枠を読み取れませんでした')
                    start, end = minutes(match[1]), minutes(match[2])
                    status = image.get('alt', '')
                    if start % 60 or end % 60:
                        raise SourceError('定時以外の時間枠が表示されています')
                    for hour in range(start, end, 60):
                        slots.append(slot(hour, min(hour + 60, end), status))
                if not slots:
                    raise SourceError('指定日の時間枠を確認できませんでした')
                results.append(court('abiko', facility, row_name, slots,
                    '我孫子市のテニス予約は1枠1〜3時間です。利用資格・予約できる枠数は公式サイトでご確認ください。'))
        except Exception as error:
            errors.append(f'{facility} {name}：{friendly_error(error)}')
            if time.monotonic() >= deadline:
                break
    return results, errors


def friendly_error(error):
    return str(error) if isinstance(error, SourceError) else '予約サイトから情報を取得できませんでした'


ADAPTERS = {'kashiwa': kashiwa, 'nagareyama': nagareyama, 'abiko': abiko}


def fetch_city(city, day):
    begin = time.monotonic()
    try:
        courts, errors = ADAPTERS[city](day, begin + 100)
        return {'id': city, 'name': SOURCES[city][0], 'courts': courts,
                'errors': errors, 'status': 'partial' if errors else 'ok',
                'checkedAt': datetime.now(JST).isoformat(timespec='seconds'),
                'seconds': round(time.monotonic() - begin, 1)}
    except Exception as error:
        return {'id': city, 'name': SOURCES[city][0], 'courts': [],
                'errors': [friendly_error(error)], 'status': 'error',
                'checkedAt': datetime.now(JST).isoformat(timespec='seconds'),
                'seconds': round(time.monotonic() - begin, 1)}
