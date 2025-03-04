import json
import os
from time import sleep
import requests
import re

integration_token = os.environ['integration_token']
database_id = os.environ['database_id']

import datetime
current_date = datetime.date.today()

headers = {
    'Authorization': f'Bearer {integration_token}',
    'Content-Type': 'application/json',
    'Notion-Version': '2021-08-16',
}

def process_content_for_links(content):
    # Process the content to convert URLs to hyperlinks
    # Match URL pattern for arXiv links
    url_pattern = r'https://arxiv\.org/(?:abs|pdf)/[\d\.]+(?:v\d+)?'
    
    # Find all URLs in the content
    urls = re.findall(url_pattern, content)
    
    # For each URL, create a hyperlink in Notion format
    for url in urls:
        link_text = url
        # Replace plain URL text with Notion hyperlink format
        content = content.replace(url, '')
    
    return content

def send(logger, content_json, nums):
    try:
        # Process the content to convert URLs to hyperlinks in children blocks
        for i, child in enumerate(content_json['children']):
            if child.get('type') == 'paragraph':
                paragraph_text = child['paragraph']['text'][0]['text']['content']
                
                # Check for arXiv links
                url_pattern = r'https://arxiv\.org/(?:abs|pdf)/[\d\.]+(?:v\d+)?'
                urls = re.findall(url_pattern, paragraph_text)
                
                # If links are found, replace them with hyperlink format
                if urls:
                    text_parts = re.split(url_pattern, paragraph_text)
                    new_text_blocks = []
                    
                    for j, part in enumerate(text_parts):
                        if part:
                            new_text_blocks.append({
                                'type': 'text',
                                'text': {'content': part}
                            })
                        
                        # Add hyperlink after each part (except the last one)
                        if j < len(urls):
                            new_text_blocks.append({
                                'type': 'text',
                                'text': {
                                    'content': urls[j],
                                    'link': {'url': urls[j]}
                                }
                            })
                    
                    # Replace the single text block with multiple blocks including hyperlinks
                    content_json['children'][i]['paragraph']['text'] = new_text_blocks
        
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

        try:
            response = requests.post('https://api.notion.com/v1/pages', headers=headers, data=json.dumps(new_page_data), timeout=30)
            
            if response.status_code == 200:
                logger.info('✅ Successfully pushed to Notion！')
                try:
                    sleep(1)
                    response = requests.post(
                        f"https://api.notion.com/v1/databases/{database_id}/query",
                        headers=headers,
                        timeout=30
                    )
                    if response.status_code == 200:
                        data = response.json()
                        if "results" in data and len(data["results"]) > 0:
                            page_id = data["results"][0]["id"]
                            return page_id
                    logger.info('⚠️ Could not retrieve page ID, returning None')
                    return None
                except Exception as e:
                    logger.info(f'⚠️ Error querying database: {str(e)}')
                    return None
            else:
                logger.info('❌ Error pushing paper to Notion!')
                logger.info(response.text)
                return None
        except Exception as e:
            logger.info(f'❌ Error in Notion API request: {str(e)}')
            return None
    except Exception as e:
        logger.info(f'❌ Error preparing data for Notion: {str(e)}')
        return None
