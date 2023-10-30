import json
import os
from time import sleep
import requests

integration_token = os.environ['integration_token']

database_id = os.environ['database_id']

import datetime

current_date = datetime.date.today()

headers = {
    'Authorization': f'Bearer {integration_token}',
    'Content-Type': 'application/json',
    'Notion-Version': '2021-08-16',
}


def send(logger, content_json, nums):
    new_page_data = {'parent': {
        'database_id': database_id,
    }, 'properties': {
        'title': {
            'title': [
                {
                    'text': {
                        'content': 'Paper Express ' + str(current_date),
                    },
                },
            ],
        },
        '#cs.CL': {
            'number': nums[0]
        },
        '#cs.CV': {
            'number': nums[1]
        },
        '#cs.CY': {
            'number': nums[2]
        },
        '#cs.HC': {
            'number': nums[3]
        },
        '#cs.IR': {
            'number': nums[4]
        },
        '#cs.LG': {
            'number': nums[5]
        },
        '#cs.MA': {
            'number': nums[6]
        },
        '#cs.SE': {
            'number': nums[7]
        },
        '#cs.NE': {
            'number': nums[8]
        },
        '#cs.AI': {
            'number': nums[9]
        },
    }, 'children': content_json['children']}

    response = requests.post('https://api.notion.com/v1/pages', headers=headers, data=json.dumps(new_page_data))

    if response.status_code == 200:
        logger.info('✅ Successfully pushed to Notion！')
        sleep(1)
        response = requests.post(
            f"https://api.notion.com/v1/databases/{database_id}/query",
            headers=headers,
        )
        data = response.json()
        page_id = data["results"][0]["id"]
        return page_id
    else:
        logger.info('❌ Error pushing paper to Notion!')
        logger.info(response.text)
        return None
