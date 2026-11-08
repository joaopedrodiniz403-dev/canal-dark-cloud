"""Read-only editorial research from public RSS; never acquires media or grants rights."""
import argparse
import hashlib
import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from .engine import save

MAX_FEED_BYTES = 2 * 1024**2
ALLOWED_FEED_HOSTS = {'news.google.com', 'trends.google.com'}


class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []
    def handle_data(self, data):
        self.parts.append(data)


def plain(text):
    parser = TextOnly(); parser.feed((text or '')[:4000])
    return ' '.join(unescape(' '.join(parser.parts)).split())[:500]


def normalized(text):
    value = unicodedata.normalize('NFKD', text.casefold())
    value = ''.join(x for x in value if not unicodedata.combining(x))
    return ' '.join(re.sub(r'[^\w]+', ' ', value).split())


def safe_link(url):
    try:
        if not isinstance(url,str) or any(ord(c)<=32 or ord(c)==127 for c in url):
            return None
        p = urllib.parse.urlsplit(url)
        if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password or p.port not in (None,80,443):
            return None
        return urllib.parse.quote(urllib.parse.urlunsplit((p.scheme,p.netloc,p.path,p.query,'')),safe=':/?&=+%~!$;,.-_')
    except ValueError:
        return None


def feed_url(url):
    link = safe_link(url)
    p = urllib.parse.urlsplit(link or '')
    if p.scheme != 'https' or p.hostname not in ALLOWED_FEED_HOSTS or p.port not in (None,443) or p.path not in ('/rss/search','/trending/rss'):
        raise ValueError('RESEARCH_FEED_URL_REJECTED')
    return link


class FeedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        feed_url(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def fetch(url):
    url = feed_url(url)
    opener = urllib.request.build_opener(FeedRedirect())
    for attempt in range(3):
        try:
            request = urllib.request.Request(url,headers={'User-Agent':'NuvemEscuraResearch/1','Accept':'application/rss+xml, application/xml'})
            with opener.open(request,timeout=20) as response:
                feed_url(response.geturl())
                data = response.read(MAX_FEED_BYTES+1)
                if len(data)>MAX_FEED_BYTES:
                    raise ValueError('RESEARCH_FEED_TOO_LARGE')
                return data
        except urllib.error.HTTPError as error:
            if error.code not in (429,500,502,503,504) or attempt==2:
                raise RuntimeError('RESEARCH_HTTP_'+str(error.code)) from None
            retry = error.headers.get('Retry-After','') if error.headers else ''
            if retry.isdigit() and int(retry)>10:
                raise RuntimeError('RESEARCH_RETRY_LATER') from None
            delay = int(retry) if retry.isdigit() else 2**attempt
        except (urllib.error.URLError,TimeoutError):
            if attempt==2:
                raise RuntimeError('RESEARCH_NETWORK_UNAVAILABLE') from None
            delay = 2**attempt
        time.sleep(delay)


def parse(data, source, now, terms, max_age_days):
    if len(data)>MAX_FEED_BYTES or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('RESEARCH_XML_REJECTED')
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        raise ValueError('RESEARCH_XML_INVALID') from None
    if root.tag != 'rss' or root.find('channel') is None:
        raise ValueError('RESEARCH_RSS_REQUIRED')
    items, counts = [], {'seen':0,'irrelevant':0,'invalid':0,'old':0,'future':0}
    for item in root.findall('./channel/item')[:200]:
        counts['seen'] += 1
        title = plain(item.findtext('title'))
        link = safe_link((item.findtext('link') or '').strip())
        matches = [term for term in terms if (' '+normalized(term)+' ') in (' '+normalized(title)+' ')]
        if not matches:
            counts['irrelevant'] += 1; continue
        try:
            published = parsedate_to_datetime(item.findtext('pubDate') or '')
            if published.tzinfo is None:
                raise ValueError()
            published = published.astimezone(timezone.utc)
        except (ValueError,TypeError,OverflowError):
            counts['invalid'] += 1; continue
        if not title or not link:
            counts['invalid'] += 1; continue
        if published > now+timedelta(minutes=10):
            counts['future'] += 1; continue
        if now-published > timedelta(days=max_age_days):
            counts['old'] += 1; continue
        publisher = item.find('source')
        evidence = {'feed_id':source['id'],'feed_url':source['url'],
                    'item_url':link,'published_at':published.isoformat(),'retrieved_at':now.isoformat(),
                    'publisher':plain(publisher.text) if publisher is not None else None,
                    'publisher_url':safe_link(publisher.get('url','')) if publisher is not None else None,
                    'article_content_verified':False}
        age_hours = max(0,(now-published).total_seconds()/3600)
        relevance = min(60,20*len(matches))
        freshness = round(40*max(0,1-age_hours/(max_age_days*24)),2)
        items.append({'id':hashlib.sha256(normalized(title).encode()).hexdigest()[:20],
                      'title':title,'matched_terms':matches,'research_score':round(relevance+freshness,2),
                      'score_components':{'keyword_relevance':relevance,'freshness':freshness},
                      'score_kind':'research_priority_not_virality_prediction',
                      'evidence':[evidence],'reuse_rights_verified':False,'production_eligible':False,
                      'editorial_review_required':True})
    return items,counts


def collect(config, output, *, now=None, loader=fetch):
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    terms = config.get('terms',[])
    age = config.get('max_age_days',7)
    feeds = config.get('feeds',[])
    if (not isinstance(terms,list) or not terms or len(terms)>50 or
        not all(isinstance(t,str) and normalized(t) and len(t)<=80 for t in terms) or
        isinstance(age,bool) or not isinstance(age,int) or not 1<=age<=30 or
        not isinstance(feeds,list) or not 1<=len(feeds)<=5 or
        not all(isinstance(f,dict) for f in feeds) or
        len({f.get('id') for f in feeds})!=len(feeds)):
        raise ValueError('RESEARCH_CONFIG_INVALID')
    report = {'schema':1,'generated_at':now.isoformat(),'sources':[],'candidates':[],
              'publication_enabled':False,'media_download_enabled':False,
              'limitations':['Headlines and feed dates only; article content not verified',
                            'Public availability grants no reuse rights',
                            'No YouTube views, retention or virality prediction']}
    unique = {}
    for source in feeds:
        record = {'id':source.get('id'),'status':'FAILED'}
        report['sources'].append(record)
        try:
            if not re.fullmatch(r'[a-z0-9-]{1,64}',source.get('id','')):
                raise ValueError('RESEARCH_SOURCE_ID_INVALID')
            url = feed_url(source['url'])
            raw = loader(url)
            items,counts = parse(raw,source,now,terms,age)
            record.update(status='FETCHED',url=url,content_sha256=hashlib.sha256(raw).hexdigest(),counts=counts)
            for item in items:
                previous = unique.get(item['id'])
                if previous is None:
                    unique[item['id']] = item
                else:
                    previous['evidence'].extend(item['evidence'])
                    if item['research_score']>previous['research_score']:
                        previous.update(research_score=item['research_score'],score_components=item['score_components'])
        except Exception as error:
            known = str(error)
            record['reason'] = known if re.fullmatch(r'RESEARCH_[A-Z0-9_]+',known) else 'RESEARCH_SOURCE_FAILED'
    report['candidates'] = sorted(unique.values(),key=lambda x:(-x['research_score'],x['id']))
    successful = sum(x['status']=='FETCHED' for x in report['sources'])
    report['status'] = 'FAILED' if not successful else 'PARTIAL' if successful<len(feeds) else 'OK' if unique else 'NO_RELEVANT_CANDIDATES'
    save(Path(output)/'research.json',report)
    def md(text):
        return re.sub(r'([\\`*_{}\[\]<>])',r'\\\1',text)
    lines = ['# Pesquisa Nuvem Escura','',f"Estado: {report['status']}",'',
             'Pautas para apuração; nenhuma autorização de reutilização ou aprovação de publicação.','']
    for item in report['candidates']:
        lines += [f"- {md(item['title'])}"]
        for evidence in item['evidence']:
            lines += [f"  - [Fonte RSS]({evidence['item_url']}) — data declarada: {evidence['published_at']}"]
    (Path(output)/'RESEARCH.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=Path('agent/research.json'))
    parser.add_argument('--output',type=Path,default=Path('output/research'))
    args = parser.parse_args()
    report = collect(json.loads(args.config.read_text()),args.output)
    print(json.dumps({'status':report['status'],'candidates':len(report['candidates']),
                      'sources':report['sources']},ensure_ascii=False,indent=2))
    if report['status'] in ('FAILED','PARTIAL'):
        raise SystemExit(1)


if __name__=='__main__':
    main()
