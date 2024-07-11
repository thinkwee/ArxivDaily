import os
import logging
from parse_paper import parse
from send_notion import send
from logging import handlers
import sys

keyword = sys.argv[1]


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
    name = link.split("/")[4]
    logger.info(name)
    num, group = parse(logger, link, keyword)
    contents = []
    titles = []
    for item in group[:3]:
        msg = ""
        msg += "Authors:\n" + item[1] + "\n\n"
        msg += "Arxiv Link:\n" + item[2] + "\n\n"
        msg += "Submission Time:\n" + item[3] + "\n\n"
        msg += item[4] + "\n"
        msg += "-" * 10 + "\n\n"
        contents.append(msg)
        title = item[0].lstrip("Title: ").strip()
        titles.append(title)

    if len(group) == 0:
        msg_all = ""
    else:
        msg_all = "\n【Complete " + name + " {} Paper List】\n\n".format(keyword)
        for idx, item in enumerate(group):
            msg_all += "- Title: " + item[0].lstrip("Title:").strip() + "\n"
            msg_all += "- Arxiv Link: " + item[2] + "\n\n"
    contents = [item[:2000] for item in contents]
    return num, contents, titles, msg_all, name, group


links = [
    "https://arxiv.org/list/cs.CL/pastweek?skip=0&show=100",
    "https://arxiv.org/list/cs.CV/pastweek?skip=0&show=100",
    "https://arxiv.org/list/cs.CY/pastweek?skip=0&show=100",
    "https://arxiv.org/list/cs.HC/pastweek?skip=0&show=100",
    "https://arxiv.org/list/cs.IR/pastweek?skip=0&show=100",
    "https://arxiv.org/list/cs.LG/pastweek?skip=0&show=100",
    "https://arxiv.org/list/cs.MA/pastweek?skip=0&show=100",
    "https://arxiv.org/list/cs.SE/pastweek?skip=0&show=100",
    "https://arxiv.org/list/cs.NE/pastweek?skip=0&show=100",
    "https://arxiv.org/list/cs.AI/pastweek?skip=0&show=100"
]

all_response = []
msg_opening = ""
count_read = 0
for link in links:
    num, contents, titles, msg_all, name, group = get_content(link)
    all_response.append([num, contents, titles, msg_all, name, group])
    msg_opening += "Parse latest " + str(num) + " " + name + " Arxiv papers, in which there are " + str(
        len(group)) + " papers related to " + keyword + "\n"
    count_read += len(group)

content_json = create_title(msg_opening)
for num, contents, titles, msg_all, name, group in all_response:
    content_json = add_top(content_json, name, contents, titles)

content_json = add_complete_titles(content_json, [item[3] for item in all_response])

nums_related = [len(item[-1]) for item in all_response]
page_id = send(logger, content_json, nums_related)
logger.info(page_id)
