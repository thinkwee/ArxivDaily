import os
import logging
from parse_paper import parse
from send_notion import send
from logging import handlers
import sys
import argparse
from datetime import datetime, timedelta

# Create argument parser
parser = argparse.ArgumentParser(description='Parse arxiv papers with keyword filtering')
parser.add_argument('keyword', help='Keyword to filter papers')
parser.add_argument('--month', type=int, help='Month to parse (1-12)')
parser.add_argument('--year', type=int, help='Year to parse')

# Parse arguments
args = parser.parse_args()
keyword = args.keyword
specified_month = args.month
specified_year = args.year

# Validate month if provided
if specified_month is not None and (specified_month < 1 or specified_month > 12):
    print("Month must be between 1 and 12")
    sys.exit(1)

# Validate year if provided
current_year = datetime.now().year
if specified_year is not None and (specified_year < 1991 or specified_year > current_year):
    print(f"Year must be between 1991 and {current_year}")
    sys.exit(1)

class Logger(object):
    level_relations = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'crit': logging.CRITICAL
    }

    def __init__(self,
                 filename,
                 level='info',
                 when='D',
                 backCount=100,
                 fmt='%(asctime)s - %(levelname)s: %(message)s'):
        self.logger = logging.getLogger(filename)
        format_str = logging.Formatter(fmt)
        self.logger.setLevel(self.level_relations.get(level))
        sh = logging.StreamHandler()
        sh.setFormatter(format_str)
        th = handlers.TimedRotatingFileHandler(filename=filename,
                                               when=when,
                                               backupCount=backCount,
                                               encoding='utf-8')
        th.setFormatter(format_str)
        self.logger.addHandler(sh)
        self.logger.addHandler(th)


project_path = current_directory = os.getcwd()
logger = Logger(os.path.join(project_path, 'logs', 'PaperDailyExpress.log')).logger

database_id = os.environ['database_id']


def create_title(text):
    content_json = {
        'children': [{
            'object': 'block',
            'type': 'heading_1',
            'heading_1': {
                'text': [{
                    'type': 'text',
                    'text': {
                        'content': "{} Paper Daily Express".format(keyword),
                    },
                },],
            },
        }, {
            'object': 'block',
            'type': 'paragraph',
            'paragraph': {
                'text': [{
                    'type': 'text',
                    'text': {
                        'content': text,
                    },
                },],
            },
        }]
    }
    return content_json


def add_top(content_json, name, contents, titles):
    if len(titles) == 0:
        return content_json
    content_json["children"].append({
        'object': 'block',
        'type': 'heading_1',
        'heading_1': {
            'text': [{
                'type': 'text',
                'text': {
                    'content': name + " Latest 3 {} Related Paper Details".format(keyword),
                },
            },],
        },
    })

    for title, content in zip(titles, contents):
        content_json['children'].append({
            'object': 'block',
            'type': 'heading_2',
            'heading_2': {
                'rich_text': [{
                    'type': 'text',
                    'text': {
                        'content': title,
                    },
                    'annotations': {
                        'bold': True
                    }
                },],
            },
        })
        content_json['children'].append({
            'object': 'block',
            'type': 'paragraph',
            'paragraph': {
                'text': [{
                    'type': 'text',
                    'text': {
                        'content': content,
                    },
                },],
            },
        })
    return content_json


def add_complete_titles(content_json, contents):
    content_json['children'].append({
        'object': 'block',
        'type': 'heading_1',
        'heading_1': {
            'text': [{
                'type': 'text',
                'text': {
                    'content': "Complete {} Paper List".format(keyword),
                },
            },],
        },
    })
    for content in contents:
        content = content[:2000]
        content_json['children'].append({
            'object': 'block',
            'type': 'paragraph',
            'paragraph': {
                'text': [{
                    'type': 'text',
                    'text': {
                        'content': content,
                    },
                },],
            },
        })

    return content_json


def get_content(link):
    name = "Unknown"
    try:
        name = link.split("/")[4]
    except Exception as e:
        logger.error(f"Error extracting name from link: {str(e)}")
    
    logger.info(name)
    num = 0
    group = []
    
    try:
        num, group = parse(logger, link, keyword)
    except Exception as e:
        logger.error(f"Error parsing {link}: {str(e)}")
    
    contents = []
    titles = []
    
    try:
        for item in group[:3]:
            try:
                msg = ""
                msg += "Authors:\n" + item[1] + "\n\n"
                # Create properly formatted hyperlink for Notion
                arxiv_url = item[2]
                msg += f"Arxiv Link:\n{arxiv_url}\n\n"
                msg += "Submission Time:\n" + item[3] + "\n\n"
                msg += item[4] + "\n"
                msg += "-" * 10 + "\n\n"
                contents.append(msg)
                title = item[0].lstrip("Title: ").strip()
                titles.append(title)
            except Exception as e:
                logger.error(f"Error creating content for paper: {str(e)}")
                continue
    except Exception as e:
        logger.error(f"Error processing group: {str(e)}")

    try:
        if len(group) == 0:
            msg_all = ""
        else:
            msg_all = "\n【Complete " + name + " {} Paper List】\n\n".format(keyword)
            for idx, item in enumerate(group):
                try:
                    title = item[0].lstrip("Title:").strip()
                    arxiv_url = item[2]
                    # Create hyperlink format for Notion
                    msg_all += f"- Title: {title}\n"
                    msg_all += f"- Arxiv Link: {arxiv_url}\n\n"
                except Exception as e:
                    logger.error(f"Error adding paper to complete list: {str(e)}")
                    continue
    except Exception as e:
        logger.error(f"Error creating message all: {str(e)}")
        msg_all = ""
    
    # Ensure content length is limited to prevent API issues
    contents = [item[:2000] for item in contents]
    return num, contents, titles, msg_all, name, group


# Base URLs for different categories
base_categories = [
    "cs.CL", "cs.CV", "cs.CY", "cs.HC", "cs.IR", 
    "cs.LG", "cs.MA", "cs.SE", "cs.NE", "cs.AI"
]

# Generate links based on date parameters or use past 30 days as default
links = []
if specified_month is not None and specified_year is not None:
    # Format the date range
    date_param = f"{specified_year}{specified_month:02d}"
    
    # ArXiv date format for specific month: YYMM
    for category in base_categories:
        links.append(f"https://arxiv.org/list/{category}/{date_param}?skip=0&show=2000")
    
    time_period = f"{specified_month}/{specified_year}"
    logger.info(f"Parsing papers from {time_period}")
else:
    # Use the past 30 days (not just last calendar month)
    # For ArXiv, we need to use "pastweek" parameter
    # and can't directly specify a custom date range of 30 days
    # So we'll use "pastweek" but request more papers
    for category in base_categories:
        links.append(f"https://arxiv.org/list/{category}/pastweek?skip=0&show=2000")
    
    # Calculate the date range for display purposes
    today = datetime.now()
    thirty_days_ago = today - timedelta(days=30)
    time_period = f"the past 30 days ({thirty_days_ago.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')})"
    logger.info(f"Parsing papers from {time_period}")

all_response = []
msg_opening = ""
count_read = 0

for link in links:
    num, contents, titles, msg_all, name, group = get_content(link)
    all_response.append([num, contents, titles, msg_all, name, group])
    msg_opening += f"Parse {time_period}'s {num} {name} Arxiv papers, in which there are {len(group)} papers related to {keyword}\n"
    count_read += len(group)

content_json = create_title(msg_opening)

# First add complete titles at the top (after the title)
content_json = add_complete_titles(content_json, [item[3] for item in all_response])

# Then add the detailed paper sections
for num, contents, titles, msg_all, name, group in all_response:
    content_json = add_top(content_json, name, contents, titles)

nums_related = [len(item[-1]) for item in all_response]
page_id = send(logger, content_json, nums_related)
logger.info(page_id)
