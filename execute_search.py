import os
from search import get_search
import logging
from send_notion import send
from logging import handlers
import sys

cat = sys.argv[1]
keyword = sys.argv[2]

class Logger(object):
    level_relations = {
        'debug':logging.DEBUG,
        'info':logging.INFO,
        'warning':logging.WARNING,
        'error':logging.ERROR,
        'crit':logging.CRITICAL
    }

    def __init__(self, filename, level='info', when='D', backCount=100, fmt='%(asctime)s - %(levelname)s: %(message)s'):
        self.logger = logging.getLogger(filename)
        format_str = logging.Formatter(fmt)
        self.logger.setLevel(self.level_relations.get(level))
        sh = logging.StreamHandler()
        sh.setFormatter(format_str) 
        th = handlers.TimedRotatingFileHandler(filename=filename,when=when,backupCount=backCount,encoding='utf-8')  
        th.setFormatter(format_str)
        self.logger.addHandler(sh)
        self.logger.addHandler(th)

name = "search_" + cat
project_path = current_directory = os.getcwd()
logger = Logger(os.path.join(project_path, 'logs','PaperDailyExpress_' + name + '.log')).logger

# Fix: Add try-except block to safely get environment variable
try:
    database_id = os.environ['database_id']
except KeyError:
    logger.error("Environment variable 'database_id' not found")
    database_id = ""  # Provide a default value or handle appropriately

def create_title(text):
    content_json = {
        'children': [{
            'object': 'block',
            'type': 'heading_1',
            'heading_1': {
                'text': [
                    {
                        'type': 'text',
                        'text': {
                            'content': "{} Paper Daily Express".format(keyword),
                        },
                    },
                ],
            },
        }, {
            'object': 'block',
            'type': 'paragraph',
            'paragraph': {
                'text': [
                    {
                        'type': 'text',
                        'text': {
                            'content': text,
                        },
                    },
                ],
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
            'text': [
                {
                    'type': 'text',
                    'text': {
                        'content': name + " Latest 3 " + keyword + " Related Paper Details",
                    },
                },
            ],
        },
    })

    for title, content in zip(titles, contents):
        content_json['children'].append({
            'object': 'block',
            'type': 'heading_2',
            'heading_2': {
                'text': [
                    {
                        'type': 'text',
                        'text': {
                            'content': title,
                        },
                    },
                ],
            },
        })
        content_json['children'].append({
            'object': 'block',
            'type': 'paragraph',
            'paragraph': {
                'text': [
                    {
                        'type': 'text',
                        'text': {
                            'content': content,
                        },
                    },
                ],
            },
        })
    return content_json


def add_complete_titles(content_json, contents):
    content_json['children'].append({
        'object': 'block',
        'type': 'heading_1',
        'heading_1': {
            'text': [
                {
                    'type': 'text',
                    'text': {
                        'content': "Complete " + keyword + " Paper List",
                    },
                },
            ],
        },
    })
    for content in contents:
        for item in content:
            content_json['children'].append({
                'object': 'block',
                'type': 'paragraph',
                'paragraph': {
                    'text': [
                        {
                            'type': 'text',
                            'text': {
                                'content': item,
                            },
                        },
                    ],
                },
            })

    return content_json


def get_content(link):
    name = link
    logger.info(name)
    num = 0
    group = []
    
    try:
        num, group = get_search(logger, link, cat, keyword)
    except Exception as e:
        logger.error(f"Error in get_search for {link}: {str(e)}")
    
    contents = []
    titles = []
    
    try:
        for item in group[:3]:
            msg = ""
            try:
                msg += "Author: " + (item[1] if len(item) > 1 else "Unknown") + "\n"
                msg += "Arxiv Link: " + (item[2] if len(item) > 2 else "#") + "\n"
                msg += "Submission Time: " + str(item[3] if len(item) > 3 else "N/A") + "\n"
                msg += (item[4] if len(item) > 4 else "") + "\n"
                msg += "-" * 10 + "\n\n"
                contents.append(msg)
                titles.append(item[0].lstrip("Title: ") if len(item) > 0 else "Unknown Title")
            except Exception as e:
                logger.error(f"Error formatting paper content: {str(e)}")
                continue
    except Exception as e:
        logger.error(f"Error processing group: {str(e)}")

    try:
        if len(group) == 0:
            msg_all = [""]
        else:
            msg_all = ["【Complete " + name + " " + keyword + " Paper List】"]
            msg = ""
            for idx, item in enumerate(group):
                try:
                    if len(item) > 0:
                        msg += str(idx + 1) + ") Title: " + item[0].lstrip("Title:") + "\n"
                        if len(item) > 2:
                            msg += "    Arxiv Link: " + item[2] + "\n\n"
                        else:
                            msg += "    Arxiv Link: N/A\n\n"
                    
                    if (idx + 1) % 10 == 0:
                        msg_all.append(msg)
                        msg = ""
                except Exception as e:
                    logger.error(f"Error adding paper to complete list: {str(e)}")
                    continue
            if msg:  # Add remaining items if any
                msg_all.append(msg)
    except Exception as e:
        logger.error(f"Error creating message all: {str(e)}")
        msg_all = [""]
    
    # Ensure content length is limited to prevent API issues
    contents = [item[:2000] for item in contents]
    
    return num, contents, titles, msg_all, name, group

links = [
    "cs.CL", "cs.CV",
    "cs.CY", "cs.HC",
    "cs.IR", "cs.LG",
    "cs.MA", "cs.SE",
    "cs.NE", "cs.AI"
]

try:
    all_response = []
    msg_opening = ""
    count_read = 0
    for link in links:
        num, contents, titles, msg_all, name, group = get_content(link)
        all_response.append([num, contents, titles, msg_all, name, group])
        msg_opening += "Parse latest " + str(num) + " " + name + " Arxiv papers, in which there are " + str(len(group)) + " papers related to " + keyword + "\n"
        count_read += len(group)

    content_json = create_title(msg_opening)
    for num, contents, titles, msg_all, name, group in all_response:
        content_json = add_top(content_json, name, contents, titles)

    content_json = add_complete_titles(content_json, [item[3] for item in all_response])

    nums_related = [len(item[-1]) for item in all_response]
    page_id = send(cat, logger, content_json, nums_related, database_id)  # Pass database_id to send function
    logger.info(page_id)
except Exception as e:
    logger.error(f"Error in main execution flow: {str(e)}")
