"""Spider to scrape the Incels Wiki and archive pages locally."""

import os
import re
from urllib.parse import urljoin
from datetime import datetime
import scrapy
import requests


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
        self.outlink_pattern = re.compile(r'\/w\/(?!File)(?!Category)(?!Editing_rules)[^#\t\n\r]+')

    name = 'incelswiki'
    allowed_domains = ['incels.wiki']
    with open('start_urls.txt', 'r') as f:
        start_urls = [url.strip() for url in f.readlines()]
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
        'AUTOTHROTTLE_ENABLED': True,
        'DEPTH_LIMIT': 1,
        'REDIRECT_ENABLED': True,
        'LOGSTATS_INTERVAL': 300,
        'LOG_LEVEL': 'INFO'
    }

    def parse(self, response):
        """Parse the response from the Incels Wiki and extract nodes and edges."""
        # Update archives
        self.save_to_local_archive(response)
        self.save_to_wayback(response.url)

        # Extract the title and outlinks from the response
        title = response.css('#firstHeading span::text').get()
        outlinks = response.css('#mw-content-text a::attr(href)').getall()

        # Yield the node details
        # yield {'id': response.url, 'label': title if title else 'No title'}
        yield NodeItem(id=response.url, label=title if title else 'No title')

        # Yield the first edge details
        # first_outlink = self.extract_first_outlink(response)
        # if not first_outlink:
        #     self.logger.warning(f'{title} ---> {first_outlink}')
        # else:
        #     self.logger.info(f'{title} ---> {first_outlink}')
        # yield {
        #     'source': response.url,
        #     'target': urljoin(response.url, first_outlink)
        # }

        # Crawl valid internal links in the body
        first_outlink_yielded = False
        for href in outlinks:
            # Only follow internal wiki article links (not files, categories, etc.)
            if self.outlink_pattern.match(href):
                target_url = urljoin(response.url, href)

                yield EdgeItem(source=response.url, target=target_url)

                if not first_outlink_yielded:
                    # Yield the first outlink as an edge
                    # yield {
                    #     'source': response.url,
                    #     'target': target_url
                    # }
                    yield FirstEdgeItem(source=response.url, target=target_url)
                    first_outlink_yielded = True
                    
                    # Only follow the first outlink
                    self.logger.info(f'{title} ---> {href}')
                    yield scrapy.Request(target_url, callback=self.parse)
        
        if not first_outlink_yielded:
            self.logger.warning(f'{title} ---> None')
            # yield {
            #             'source': response.url,
            #             'target': None
            #         }

        # # body_links = [ x for x in body_links if ':' not in x ]
        # for href in outlinks:
        #     # Filter out links that contain a colon (e.g., namespace links)
        #     if ':' in href:
        #         outlinks.remove(href)
        #     elif '#' in href:
        #         # Strip anchor tags from links
        #         outlinks[outlinks.index(href)] = href.split('#')[0]

        # for href in outlinks:
        #     # target_url = urljoin(response.url, href)

        #     # # Yield the first edge details
        #     # if i == 0:
        #     #     yield {'source': response.url, 'target': target_url}

        #     # Request the target URL to continue crawling
        #     if self.outlink_pattern.match(href):
        #         yield scrapy.Request(urljoin(response.url, href),
        #                              callback=self.parse)

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

    def save_to_local_archive(self, response):
        """Save the response body to a local archive."""
        # Generate a filename based on the page title
        filename = response.url.split('/')[-1]
        filename = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_',
                          filename).strip()  # Replace invalid characters
        filename_timestamp = datetime.now().strftime('%Y%m%d-%H%M')

        # Create a directory for the archive if it doesn't exist
        directory = f'archive/{filename}'
        os.makedirs(directory, exist_ok=True)

        # Save the response body to a file
        if response.status == 200:
            with open(f'{directory}/{filename_timestamp}.html', 'wb+') as f:
                f.write(response.body)
                self.logger.debug(f'Saved {f.name}')
    
    def save_to_wayback(self, url):
        """Save the response to the Wayback Machine."""
        # Wayback Machine API endpoint
        wayback_api = "https://web.archive.org/save/"

        # Send a request to the Wayback Machine to save the URL
        self.logger.debug(f'Saving {url} to Wayback Machine...')
        try:
            response = requests.get(wayback_api + url)
            
            # Raise an error for bad responses
            response.raise_for_status()  
            
            self.logger.debug(f"Submitted {url} to Wayback Machine.")
        except Exception as e:
            self.logger.error(f"Unable to archive page to Wayback Machine.")
            self.logger.debug(f'Exception: {e}')

    # def extract_first_outlink(self, response):
    #     """Extract the first outlink from the main content text."""
    #     for href in response.css('#mw-content-text a::attr(href)').getall():
    #         re_match = self.outlink_pattern.match(href)
    #         # if self.outlink_pattern.match(href) and not href.startswith('https'):
    #         if re_match:
    #             # self.logger.warning(re_match)
    #             return re_match.group(0)
