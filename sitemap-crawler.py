#!/usr/bin/env python
# -*- coding: utf-8 -*-

import hashlib
import html
import os
import sys
from datetime import date
from urllib.parse import urlparse

import mysql.connector
import pandas as pd
import regex as re
import requests
import scrapy.crawler
from bs4 import BeautifulSoup as Soup
from dotenv import dotenv_values
from lxml import etree
from io import BytesIO, StringIO
from lxml.cssselect import CSSSelector

import namematch.lobbywatch
from namematch.namematcher import MatchFormat

config = {**dotenv_values(".env"), **os.environ}

req_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36',
    # 'Accept': 'text/html,application/xhtml+xml,application/xml,text/xml,text/html,text/plain,*/*',
    # 'accept-encoding': 'gzip, deflate, br',
    # 'Accept-Charset': 'utf-8',
    # 'pragma': 'no-cache',
}

patterns = {
    re.compile('(:?ü|ue)ber[-_]?uns', re.I | re.U): 4,
    re.compile('wer.?wir.?sind.?', re.I | re.U): 5,
    re.compile('beirat', re.I | re.U): 3,
    # re.compile('mitglied', re.I | re.U): 2,
    re.compile('gesch(:?ä|ae)fts(?:leitung|stelle)', re.I | re.U): 5,
    re.compile('vorstand\\b', re.I | re.U): 7,
    re.compile('team|sekretariat', re.I | re.U): 5,
    re.compile('stiftungsrat', re.I | re.U): 7,
    re.compile('pr(?:ä|ae)sidium', re.I | re.U): 7,
    re.compile('ausschuss', re.I | re.U): 5,
    re.compile('portrait', re.I | re.U): 3,
    re.compile('gremien|kommissionen|komitee', re.I | re.U): 3,
    re.compile('netzwerk', re.I | re.U): 2,
    re.compile('partner|partenaires', re.I | re.U): 2,
    re.compile('verein|verband', re.I | re.U): 3,
    re.compile('organisation', re.I | re.U): 3,
    re.compile('stiftung', re.I | re.U): 3,
    re.compile('kontakt|contact', re.I | re.U): 1,
}
anti_patterns = {
    re.compile(r'\bblog\b', re.I | re.U): -5,
    re.compile(r'\b(artikel|articoli|articles?|aktuell)\b', re.I | re.U): -5,
    re.compile(r'\b(publikation(?:en)?|publications?|pubblicazione)\b', re.I | re.U): -5,
    re.compile(r'\bevent\b', re.I | re.U): -5,
    re.compile(r'\b(?:medienmitteilungen|news)\b', re.I | re.U): -5,
}


# Pass the headers you want to retrieve from the xml such as ["loc", "lastmod"]
def parse_sitemap(url, headers):
    try:
        resp = requests.get(url, headers=req_headers, allow_redirects=True)
    except requests.exceptions.ConnectionError:
        return False

    # we didn't get a valid response, bail
    if 200 != resp.status_code:
        return False

    # BeautifulSoup to parse the document
    soup = Soup(resp.content, "xml")

    # find all the <url> tags in the document
    urls = soup.findAll('url')
    sitemapindex = soup.findAll('sitemapindex')
    if sitemapindex:
        sitemaps = sitemapindex[0].findAll('sitemap')
    else:
        sitemaps = soup.findAll('sitemap')

    new_list = ["Source"] + headers
    panda_out_total = pd.DataFrame([], columns=new_list)

    # links = soup.findAll('link')
    # if links:
    #     print('found links:', links)

    if not urls and not sitemaps:
        return False

    # Recursive call to the the function if sitemap contains sitemaps
    if sitemaps:
        for u in sitemaps:
            test = u.find('loc').string
            panda_recursive = parse_sitemap(test, headers)
            if isinstance(panda_recursive, pd.DataFrame):
                panda_out_total = panda_out_total.append(panda_recursive, ignore_index=True)

    # storage for later...
    out = []

    # Creates a hash of the parent sitemap
    hash_sitemap = hashlib.md5(str(url).encode('utf-8')).hexdigest()

    # Extract the keys we want
    for u in urls:
        values = [hash_sitemap]
        for head in headers:
            loc = u.find(head)
            if not loc:
                loc = "None"
            else:
                loc = loc.string
            values.append(loc.strip())
        out.append(values)

    # Create a dataframe
    panda_out = pd.DataFrame(out, columns=new_list)

    # If recursive then merge recursive dataframe
    if not panda_out_total.empty:
        panda_out = pd.concat([panda_out, panda_out_total], ignore_index=True)

    # returns the dataframe
    return panda_out


def locate_sitemap(base_url, encoding='utf-8'):
    try:
        sitemap_url = None
        url = base_url
        if not url.scheme:
            url = url._replace(scheme='https')
        if not url.netloc:
            url = url._replace(netloc=url.path)
            url = url._replace(path=None)

        url = url._replace(query=None)
        url = url._replace(fragment=None)

        url = url._replace(path='/robots.txt')
        resp = requests.get(url.geturl(), headers=req_headers, allow_redirects=True)
        if 200 == resp.status_code:
            for line in resp.content.decode(encoding).split('\n'):
                if line.startswith('Sitemap:'):
                    sitemap_url = urlparse(line.split(':', maxsplit=1)[1].strip())
                    break

        if sitemap_url is None:
            url = url._replace(path='/sitemap.xml')
            resp = requests.get(url.geturl(), headers=req_headers, allow_redirects=True)
            if 200 == resp.status_code:
                sitemap_url = urlparse(resp.url)
        if sitemap_url is None:
            url = url._replace(path='/sitemaps/sitemap.xml')
            resp = requests.get(url.geturl(), headers=req_headers, allow_redirects=True)
            if 200 == resp.status_code:
                sitemap_url = urlparse(resp.url)

        if sitemap_url is None and not base_url.hostname.startswith('www.'):
            return locate_sitemap(base_url._replace(netloc='www.' + base_url.netloc))

        return sitemap_url
    except UnicodeDecodeError:
        if encoding == 'utf-8':
            return locate_sitemap(base_url, encoding='latin-1')


class LobbySpider(scrapy.Spider):
    name = 'lobbyspider'
    href_selector = CSSSelector('a[href]')
    exclude_selector = CSSSelector('script, style')
    tags_re = re.compile(b'<[^>]+>')
    follow_links = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.start_urls = kwargs.get('start_urls')
        self.matchers = kwargs.get('matchers')
        self.follow_links = kwargs.get('follow_links')

    def parse(self, response, **kwargs):
        if response.url.endswith('pdf'):
            return

        print(response.url)
        try:
            tree = etree.parse(BytesIO(response.body), parser=etree.HTMLParser())
            for e in self.exclude_selector(tree):
                e.getparent().remove(e)
            text = etree.tostring(tree, encoding='UTF-8')
        except (ValueError, AttributeError):
            return

        text = self.tags_re.sub('', text)
        # text = html.unescape(text)
        # text = '\n'.join((line.rstrip() for line in text.splitlines() if line.strip() != ''))

        matches = []
        for matcher in self.matchers:
            for m in matcher.match_text(text, MatchFormat.FIRST_LAST_ONLY):
                matches.append(m.content(m.name.id[0].emoji))
        if matches:
            yield {'url': response.url, 'matches': matches}

        if self.follow_links:
            for e in self.href_selector(tree):
                href = e.get('href')
                if href.startswith('#'):
                    continue
                if href.startswith('/'):
                    yield scrapy.Request(response.urljoin(href), callback=self.parse)
                url = urlparse(href)
                if url.scheme in ('http', 'https') and url.hostname is not None and url.hostname.endswith('.ch'):
                    yield scrapy.Request(response.urljoin(href), callback=self.parse)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        site = "https://economiesuisse.ch/sitemap.xml"
    else:
        site = sys.argv[1]

    if not urlparse(site).scheme:
        site = "https://" + site
    top25 = [site]

    sitemap_url = locate_sitemap(urlparse(site))
    if sitemap_url is not None:
        resp = requests.get(sitemap_url.geturl(), headers=req_headers, allow_redirects=True)
        if resp.status_code != 200:
            sys.exit(0)

        print(f'sitemap: {sitemap_url.geturl()}')
        df = parse_sitemap(sitemap_url.geturl(), ["loc", "lastmod"])
        if df is not False:
            df = df.drop_duplicates()
            count = [0 for i in range(len(df.index))]
            df['count'] = count
            for index, row in df.iterrows():
                for p,w in anti_patterns.items():
                    if p.search(row['loc']):
                        df.loc[index, 'count'] += w
                for p, w in patterns.items():
                    if p.search(row['loc']):
                        df.loc[index, 'count'] += w
                        # row['matches'] = (row['matches'] if row['matches'] else 0) + 1
                        # print('\t', row['loc'], row['lastmod'], df.loc[index, 'count'])
            matches = df[df['count'] >= 0]
            top25 = df[df['count'] >= 0].sort_values(by=['count', 'lastmod'], ascending=False).head(25)['loc'].drop_duplicates().tolist()

    print(f'seed urls: {top25}')
    print()

    connection = mysql.connector.connect(
        host=config["DB_HOST"],
        database="lobbywatch_public",
        user=config['DB_USER'],
        password=config['DB_PASSWORD'],
        use_unicode=True
    )
    cursor = connection.cursor()
    matchers = namematch.lobbywatch.create_matchers_from_database(cursor, date.today())


    class ItemCollectorPipeline(object):
        def __init__(self):
            self.ids_seen = set()

        def process_item(self, item, spider):
            print(item)

    process = scrapy.crawler.CrawlerProcess({'LOG_LEVEL': 'WARN', 'ITEM_PIPELINES': {'__main__.ItemCollectorPipeline': 100}, 'ROBOTSTXT_OBEY': True})
    # logging.getLogger('scrapy').setLevel(logging.INFO)
    process.crawl(LobbySpider, start_urls=top25, matchers=matchers, follow_links=True)
    process.start()

