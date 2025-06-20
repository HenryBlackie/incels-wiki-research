import scrapy
import os
import re
from urllib.parse import urlparse, urljoin
from datetime import datetime


class IncelswikiSpider(scrapy.Spider):

    def __init__(self):
        # Capture the timestamp once during initialization
        self.timestamp = datetime.now().strftime("%Y%m%d-%H%M")

    name = 'incelswiki'
    allowed_domains = ['incels.wiki']
    start_urls = ['https://incels.wiki/w/Incel']
    custom_settings = {
        'FEEDS': {
            f'feeds/nodes.csv': {
                'format': 'csv',
                'fields': ['id', 'label']
            },
            f'feeds/edges.csv': {
                'format': 'csv',
                'fields': ['source', 'target']
            }
        },
        'AUTOTHROTTLE_ENABLED': True,
        'DEPTH_LIMIT': 3,
        'LOGSTATS_INTERVAL': 15,
        'LOG_LEVEL': 'INFO'
    }

    def parse(self, response):
        # Save response to local archive
        self.local_archive(response)

        title = response.css('#firstHeading>span::text').get()
        body_links = response.css('#mw-content-text').css(
            'a[href^="/w/"]:not(.image):not(.reference):not(.external):not(.new)'
        ).xpath('@href').getall()
        # body_links = [ x for x in body_links if ':' not in x ]
        for href in body_links:
            # Filter out links that contain a colon (e.g., namespace links)
            if ':' in href:
                body_links.remove(href)
            elif '#' in href:
                # Strip anchor tags from links
                body_links[body_links.index(href)] = href.split('#')[0]

        # Yield the node details
        yield {'id': response.url, 'label': title if title else 'No title'}

        for i, href in enumerate(body_links):
            target_url = urljoin(response.url, href)

            # Yield the first edge details
            if i == 0:
                yield {'source': response.url, 'target': target_url}

            # Request the target URL to continue crawling
            yield scrapy.Request(target_url, callback=self.parse)

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
                self.logger.info(f'Saved {filename}.html to {directory}')

    def remote_archive(self):
        pass
