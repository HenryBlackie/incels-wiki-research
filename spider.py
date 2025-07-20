"""Spider to scrape the Incels Wiki and archive pages locally."""

import os
import re
from urllib.parse import urljoin
from datetime import datetime
import scrapy


class IncelswikiSpider(scrapy.Spider):
    """Spider to scrape the Incels Wiki and archive pages locally."""

    def __init__(self):
        super().__init__()
        # Capture the timestamp once during initialization
        self.timestamp = datetime.now().strftime('%Y%m%d-%H%M')
        self.outlink_pattern = re.compile(r'\/w\/(?!File)(?!Category)(?!Editing_rules)[^#\t\n\r]+')

    name = 'incelswiki'
    allowed_domains = ['incels.wiki']
    start_urls = ['https://incels.wiki/w/Incel']
    custom_settings = {
        'FEEDS': {
            'feeds/nodes.csv': {
                'format': 'csv',
                'fields': ['id', 'label']
            },
            'feeds/edges.csv': {
                'format': 'csv',
                'fields': ['source', 'target']
            }
        },
        'AUTOTHROTTLE_ENABLED': True,
        'DEPTH_LIMIT': 3,
        'REDIRECT_ENABLED': True,
        'LOGSTATS_INTERVAL': 15,
        'LOG_LEVEL': 'INFO'
    }

    def parse(self, response):
        """Parse the response from the Incels Wiki and extract nodes and edges."""
        # Save response to local archive
        self.local_archive(response)

        # Extract the title and outlinks from the response
        title = response.css('#firstHeading>span::text').get()
        outlinks = response.css('#mw-content-text a::attr(href)').getall()

        # Yield the node details
        yield {'id': response.url, 'label': title if title else 'No title'}

        # Yield the first edge details
        first_outlink = self.extract_first_outlink(response)
        self.logger.info(f'{title} ---> {first_outlink}')
        yield {
            'source': response.url,
            'target': urljoin(response.url, first_outlink)
        }

        # # body_links = [ x for x in body_links if ':' not in x ]
        # for href in outlinks:
        #     # Filter out links that contain a colon (e.g., namespace links)
        #     if ':' in href:
        #         outlinks.remove(href)
        #     elif '#' in href:
        #         # Strip anchor tags from links
        #         outlinks[outlinks.index(href)] = href.split('#')[0]

        for href in outlinks:
            # target_url = urljoin(response.url, href)

            # # Yield the first edge details
            # if i == 0:
            #     yield {'source': response.url, 'target': target_url}

            # Request the target URL to continue crawling
            if self.outlink_pattern.match(href):
                yield scrapy.Request(urljoin(response.url, href),
                                     callback=self.parse)

        # for href in body_links:
        #     target_url = urljoin(response.url, href)

        #     yield {
        #         'source': response.url,
        #         'target': target_url
        #     }

        #     yield scrapy.Request(target_url, callback=self.parse)

        # Yield the first edge details
        # target_url = urljoin(response.url, body_links[0])
        # yield {
        #     'source': response.url,
        #     'target': target_url
        # }

        # yield scrapy.Request(target_url, callback=self.parse)

        # import csv
        # with open('nodes.csv', 'r') as infile, open('cleaned_nodes.csv', 'w') as outfile:
        #     for line in infile:
        #         if line.strip() != ',':
        #             outfile.write(line)
        # with open('edges.csv', 'r') as infile, open('cleaned_edges.csv', 'w') as outfile:
        #     for line in infile:
        #         if line.strip() != ',':
        #             outfile.write(line)

    def local_archive(self, response):
        """Save the response body to a local archive."""
        # Generate a filename based on the page title
        filename = response.url.split('/')[-1]
        filename = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_',
                          filename).strip()  # Replace invalid characters

        # Create a directory for the archive if it doesn't exist
        directory = f'archive/{self.timestamp}'
        os.makedirs(directory, exist_ok=True)

        # Save the response body to a file
        if response.status == 200:
            with open(f'{directory}/{filename}.html', 'wb+') as f:
                f.write(response.body)
                self.logger.debug(f'Saved {filename}.html to {directory}')

    def extract_first_outlink(self, response):
        """Extract the first outlink from the main content text."""
        for href in response.css('#mw-content-text a::attr(href)').getall():
            re_match = self.outlink_pattern.match(href)
            # if self.outlink_pattern.match(href) and not href.startswith('https'):
            if re_match:
                # self.logger.warning(re_match)
                return re_match.group(0)
