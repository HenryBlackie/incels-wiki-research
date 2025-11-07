"""Spider to scrape the Incels Wiki and archive pages locally."""

import os
import re
from urllib.parse import urljoin
from datetime import datetime
import scrapy
import requests
import random
import configparser
import subprocess


class NodeItem(scrapy.Item):
    """Item to represent a node in the graph."""
    id = scrapy.Field()
    label = scrapy.Field()


class FirstEdgeItem(scrapy.Item):
    """Item to represent the first edge in the graph."""
    source = scrapy.Field()
    target = scrapy.Field()


class EdgeItem(scrapy.Item):
    """Item to represent an edge in the graph."""
    source = scrapy.Field()
    target = scrapy.Field()


class IncelswikiSpider(scrapy.Spider):
    """Spider to scrape the Incels Wiki and archive pages locally."""

    def __init__(self):
        super().__init__()
        # Capture the timestamp once during initialization
        self.timestamp = datetime.now().strftime('%Y%m%d-%H%M')
        self.outlink_pattern = re.compile(
            r'\/w\/(?!File:)(?!Category:)(?!Editing_rules)(?!User:)(?!User_talk:)(?!Special:)(?!IncelWiki:)[^#\t\n\r]+'
        )

    # Load configuration
    config = configparser.ConfigParser()
    config.read('config.ini')
    local_archiving = config.getboolean('General',
                                        'LocalArchiving',
                                        fallback=True)
    wayback_machine = config.getboolean('General',
                                        'WaybackMachine',
                                        fallback=False)

    name = 'incelswiki'
    allowed_domains = ['incels.wiki']
    with open('start_urls.txt', 'r') as f:
        start_urls = [url.strip() for url in f.readlines()]
        random.shuffle(start_urls)
    custom_settings = {
        'FEEDS': {
            'feeds/nodes.csv': {
                'format': 'csv',
                'fields': ['id', 'label'],
                'item_classes': [NodeItem]
            },
            'feeds/first_edges.csv': {
                'format': 'csv',
                'fields': ['source', 'target'],
                'item_classes': [FirstEdgeItem]
            },
            'feeds/all_edges.csv': {
                'format': 'csv',
                'fields': ['source', 'target'],
                'item_classes': [EdgeItem]
            }
        },
        'AUTOTHROTTLE_ENABLED':
        True,
        'DEPTH_LIMIT':
        config.getint('Scrapy', 'DepthLimit', fallback=2),
        'REDIRECT_ENABLED':
        True,
        'LOGSTATS_INTERVAL':
        config.getint('Scrapy', 'LogStatsInterval', fallback=60),
        'LOG_LEVEL':
        config.get('Scrapy', 'LogLevel', fallback='INFO'),
    }

    def parse(self, response):
        self.logger.debug(f'Parsing {response.url}')
        """Parse the response from the Incels Wiki and extract nodes and edges."""
        # Update archives
        # if self.local_archiving:
        #     self.save_to_local_archive(response)
        # if self.wayback_machine:
        #     self.save_to_wayback(response.url)
        self.auto_archive(response.url)

        # Extract the title and outlinks from the response
        title = response.css('#firstHeading span::text').get()
        outlinks = response.css('#mw-content-text p a::attr(href), '
                                '#mw-content-text ul a::attr(href), '
                                '#mw-content-text ol a::attr(href), '
                                '.redirectText a::attr(href)').getall()
        other_outlinks = [
            href for href in response.css(
                '#mw-content-text a::attr(href)').getall()
            if href not in outlinks
        ]

        # Yield the node details
        yield NodeItem(id=response.url, label=title if title else 'No title')

        # Crawl valid internal links in the body
        first_outlink = True
        yielded_first = False
        for href in outlinks:
            # Only follow internal wiki article links (not files, categories, etc.)
            if self.outlink_pattern.match(href):
                target_url = urljoin(response.url, href)
                target_url = requests.get(
                    target_url, allow_redirects=True).url  # Resolve redirects

                yield EdgeItem(source=response.url, target=target_url)
                if not yielded_first:
                    yield FirstEdgeItem(source=response.url, target=target_url)
                    self.logger.info(f'{response.url} ---> {target_url}')
                    yielded_first = True

                yield scrapy.Request(target_url, callback=self.parse)

                # yield EdgeItem(source=response.url, target=target_url)

                # is_first = not yielded_first
                # yield scrapy.Request(target_url,
                #                      callback=self.edge_callback,
                #                      meta={
                #                          'source': response.url,
                #                          'first': is_first
                #                      })
                # if is_first:
                #     yielded_first = True

        # Crawl other outlinks that are not in the main content body
        for href in other_outlinks:
            # Only follow internal wiki article links (not files, categories, etc.)
            if self.outlink_pattern.match(href):
                # target_url = urljoin(response.url, href)

                # is_first = not yielded_first
                # yield scrapy.Request(target_url,
                #                      callback=self.edge_callback,
                #                      meta={
                #                          'source': response.url,
                #                          'first': is_first
                #                      })
                # if is_first:
                #     yielded_first = True

                target_url = urljoin(response.url, href)
                target_url = requests.get(
                    target_url, allow_redirects=True).url  # Resolve redirects

                yield EdgeItem(source=response.url, target=target_url)
                if not yielded_first:
                    yield FirstEdgeItem(source=response.url, target=target_url)
                    self.logger.info(f'{response.url} ---> {target_url}')
                    yielded_first = True

                yield scrapy.Request(target_url, callback=self.parse)

        # If no valid outlinks were found, log a warning
        if not yielded_first:
            self.logger.warning(f'{response.url} ---> None')

    # def edge_callback(self, response):
    #     source = response.meta['source']
    #     first = response.meta['first']

    #     # Use response.url as canonical target
    #     yield EdgeItem(source=source, target=response.url)
    #     if first:
    #         yield FirstEdgeItem(source=source, target=response.url)
    #         self.logger.info(f'{source} ---> {response.url}')

    def save_to_local_archive(self, response):
        """Save the response body to a local archive."""
        # Generate a filename based on the page title
        filename = response.url.split('/')[-1]
        filename = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_',
                          filename).strip()  # Replace invalid characters
        filename_timestamp = datetime.now().strftime('%Y%m%d-%H%M')

        # Create a directory for the archive if it doesn't exist
        directory = os.path.join('archive', filename, filename_timestamp)
        os.makedirs(directory, exist_ok=True)

        if response.status == 200:
            # Save the response HTML
            with open(f'{directory}/{filename}.html', 'wb+') as f:
                f.write(response.body)
                self.logger.debug(f'Saved {f.name}')

            # Save the main body images
            for img_url in response.css(
                    '#mw-content-text img::attr(src)').getall():
                img_url = urljoin(response.url, img_url)
                img_name = img_url.split('/')[-1]
                try:
                    img_response = requests.get(
                        img_url,
                        timeout=10,
                        headers={'User-Agent': 'Mozilla/5.0'})
                    img_response.raise_for_status()
                    with open(os.path.join(directory, img_name),
                              'wb') as img_file:
                        img_file.write(img_response.content)
                    self.logger.debug(f'Saved {img_name}.')
                except Exception as e:
                    self.logger.warning(f'Failed to save image {img_url}: {e}')

    def save_to_wayback(self, url):
        """Save the response to the Wayback Machine."""
        # Wayback Machine API endpoint
        wayback_api = "https://web.archive.org/save/"

        # Send a request to the Wayback Machine to save the URL
        self.logger.debug(f'Saving {url} to Wayback Machine...')
        try:
            response = requests.get(wayback_api + url,
                                    timeout=30,
                                    headers={'User-Agent': 'Mozilla/5.0'})

            # Raise an error for bad responses
            response.raise_for_status()

            self.logger.debug(f"Submitted {url} to Wayback Machine.")
        except Exception as e:
            self.logger.warning(
                f"Unable to archive {url.split('/')[-1]} to Wayback Machine.")
            self.logger.debug(f'Exception: {e}')

    def auto_archive(self, url):
        subprocess.run(['uv', 'run', 'auto-archiver', url],
                       stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)