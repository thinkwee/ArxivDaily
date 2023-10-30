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

database_id = os.environ['database_id']

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
                        'content': name + " Latest 3 {} Related Paper Details".format(keyword),
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
                        'content': "Complete {} Paper List".format(keyword),
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
    num, group = get_search(logger, link, cat, keyword)
    contents = []
    titles = []
    for item in group[:3]:
        msg = ""
        msg += "Author: " + item[1] + "\n"
        msg += "Arxiv Link: " + item[2] + "\n"
        msg += "Submission Time: " + str(item[3]) + "\n"
        msg += item[4]+ "\n"
        msg += "-" * 10 + "\n\n"
        contents.append(msg)
        titles.append(item[0].lstrip("Title: "))

    if len(group) == 0:
        msg_all = [""]
    else:
        msg_all = ["【Complete " + name + " {} Paper List】".format(keyword)]
        msg = ""
        for idx, item in enumerate(group):
            msg += str(idx + 1) + ") Title: " + item[0].lstrip("Title:") + "\n"
            msg += "    Arxiv Link: " + item[2] + "\n\n"
            if (idx + 1) % 10 == 0:
                msg_all.append(msg)
                msg = ""
    contents = [item[:2000] for item in contents]
    return num, contents, titles, msg_all, name, group

links = [
    "cs.CL", "cs.CV",
    "cs.CY", "cs.HC",
    "cs.IR", "cs.LG",
    "cs.MA", "cs.SE",
    "cs.NE", "cs.AI"
]

all_response = []
msg_opening = ""
count_read = 0
for link in links:
    num, contents, titles, msg_all, name, group = get_content(link)
    all_response.append([num, contents, titles, msg_all, name, group])
    msg_opening += "Parse latest " + str(num) + " " + name + " Arxiv papers, in which there are " + str(len(group)) + " papers related to {}\n".format(keyword)
    count_read += len(group)

content_json = create_title(msg_opening)
for num, contents, titles, msg_all, name, group in all_response:
    content_json = add_top(content_json, name, contents, titles)

content_json = add_complete_titles(content_json, [item[3] for item in all_response])

nums_related = [len(item[-1]) for item in all_response]
page_id = send(cat, logger, content_json, nums_related)
logger.info(page_id)
