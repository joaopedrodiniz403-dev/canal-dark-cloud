import tempfile
import unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import Mock
from nuvem.research import collect,parse,feed_url,safe_link

NOW=datetime(2026,11,8,12,tzinfo=timezone.utc)
FEED={'id':'news','url':'https://news.google.com/rss/search?q=FiveM'}
CONFIG={'terms':['FiveM','GTA RP'],'max_age_days':7,'feeds':[FEED]}


def rss(title='FiveM: novidade no GTA RP',date='Sun, 08 Nov 2026 10:00:00 GMT',link='https://publisher.example/story'):
    return f'''<rss><channel><item><title>{title}</title><link>{link}</link><pubDate>{date}</pubDate><source url="https://publisher.example">Publisher</source></item></channel></rss>'''.encode()


class ResearchTests(unittest.TestCase):
    def test_relevant_headline_has_evidence_but_never_reuse_rights(self):
        items,counts=parse(rss(),FEED,NOW,CONFIG['terms'],7)
        self.assertEqual(len(items),1)
        item=items[0]
        self.assertEqual(item['matched_terms'],['FiveM','GTA RP'])
        self.assertFalse(item['reuse_rights_verified'])
        self.assertFalse(item['production_eligible'])
        self.assertFalse(item['evidence'][0]['article_content_verified'])
        self.assertEqual(item['evidence'][0]['published_at'],'2026-11-08T10:00:00+00:00')
        self.assertLessEqual(item['research_score'],100)

    def test_old_future_and_missing_or_unzoned_date_excluded(self):
        cases=[('Sun, 01 Nov 2020 10:00:00 GMT','old'),
               ('Sun, 15 Nov 2026 10:00:00 GMT','future'),('not a date','invalid'),
               ('Sun, 08 Nov 2026 10:00:00','invalid')]
        for date,reason in cases:
            items,counts=parse(rss(date=date),FEED,NOW,CONFIG['terms'],7)
            self.assertEqual(items,[])
            self.assertEqual(counts[reason],1)

    def test_irrelevant_and_partial_word_matches_excluded(self):
        for title in ('Receita de bolo','FiveMagazine publicou uma nota'):
            items,counts=parse(rss(title=title),FEED,NOW,CONFIG['terms'],7)
            self.assertFalse(items)
            self.assertEqual(counts['irrelevant'],1)

    def test_headline_html_is_data(self):
        items,_=parse(rss(title='&lt;b&gt;FiveM&lt;/b&gt; novidade'),FEED,NOW,CONFIG['terms'],7)
        self.assertEqual(items[0]['title'],'FiveM novidade')

    def test_entity_declarations_and_non_rss_rejected(self):
        for body in (b'<!DOCTYPE rss><rss/>',b'<feed/>',b'<rss>'):
            with self.assertRaises(ValueError): parse(body,FEED,NOW,CONFIG['terms'],7)

    def test_dedup_keeps_both_sources(self):
        with tempfile.TemporaryDirectory() as d:
            other={'id':'trends','url':'https://trends.google.com/trending/rss?geo=BR'}
            report=collect({**CONFIG,'feeds':[FEED,other]},Path(d),now=NOW,loader=lambda _:rss())
            self.assertEqual(report['status'],'OK')
            self.assertEqual(len(report['candidates']),1)
            self.assertEqual(len(report['candidates'][0]['evidence']),2)
            self.assertTrue((Path(d)/'research.json').exists())

    def test_feed_failure_is_partial_not_empty_success(self):
        with tempfile.TemporaryDirectory() as d:
            loader=Mock(side_effect=[rss(),RuntimeError('private raw exception')])
            config={**CONFIG,'feeds':[FEED,{'id':'trends','url':'https://trends.google.com/trending/rss?geo=BR'}]}
            report=collect(config,Path(d),now=NOW,loader=loader)
            self.assertEqual(report['status'],'PARTIAL')
            self.assertEqual(report['sources'][1]['reason'],'RESEARCH_SOURCE_FAILED')
            self.assertNotIn('private raw exception',str(report))

    def test_zero_matches_has_no_fallback_candidates(self):
        with tempfile.TemporaryDirectory() as d:
            report=collect(CONFIG,Path(d),now=NOW,loader=lambda _:rss(title='Futebol hoje'))
            self.assertEqual(report['status'],'NO_RELEVANT_CANDIDATES')
            self.assertEqual(report['candidates'],[])

    def test_network_failure_is_failed_and_writes_report(self):
        with tempfile.TemporaryDirectory() as d:
            report=collect(CONFIG,Path(d),now=NOW,loader=Mock(side_effect=RuntimeError('RESEARCH_NETWORK_UNAVAILABLE')))
            self.assertEqual(report['status'],'FAILED')
            self.assertTrue((Path(d)/'research.json').exists())

    def test_feed_url_policy_and_unsafe_links(self):
        for url in ('http://news.google.com/rss/search','https://example.com/rss',
                    'https://news.google.com:8443/rss/search','https://news.google.com/not-rss'):
            with self.assertRaises(ValueError): feed_url(url)
        for link in ('javascript:alert(1)','https://user:pass@example.com/a','https://example.com/a\nmalicious'):
            self.assertIsNone(safe_link(link))
        self.assertIn('%29',safe_link('https://example.com/a)'))
