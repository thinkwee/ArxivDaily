import re
from bs4 import BeautifulSoup
import requests
import fitz  
import os
import time
import re

def retry(max_retries=3, delay=1):
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    print(f"Attempt {retries + 1} failed: {e}")
                    retries += 1
                    time.sleep(delay)
            raise Exception(f"Function {func.__name__} exceeded maximum retries")

        return wrapper

    return decorator


def norm(text):
    return "".join(text.lower().strip().split())


@retry(max_retries=10, delay=3)
def get_abstract(paper_url):
    paper_response = requests.get(paper_url)
    paper_soup = BeautifulSoup(paper_response.text, 'html.parser')
    return paper_soup

@retry(max_retries=20, delay=10)
def download_paper_pdf(title, pdf_link):
    pdf_response = requests.get(pdf_link)
    pdf_filename = title + ".pdf"
    assert pdf_response.status_code == 200
    with open("./papers/" + pdf_filename, 'wb') as pdf_file:
        pdf_file.write(pdf_response.content)
    return pdf_filename


def parse(logger, arxiv_url, keyword):
    total_num = 0
    statistic = []
    
    try:
        response = requests.get(arxiv_url, timeout=30)
        exist_file_list = set()
        for file_pdf in os.listdir("./papers/"):
            if file_pdf.endswith(".pdf"):
                exist_file_list.add(norm(file_pdf).rstrip(".pdf"))
        
        exist_parse = set()
        try:
            with open("./exist", "r") as f:
                for line in f:
                    exist_parse.add(line.strip())
        except Exception as e:
            logger.error(f"Error reading exist file: {str(e)}")
        
        fw_exist_parse = open("./exist", "a")

        if response.status_code == 200:
            try:
                html_source = response.text
                soup = BeautifulSoup(html_source, 'html.parser')

                metas = soup.find_all('dt')
                papers = soup.find_all('dd')
                total_num = len(papers)

                for idx, (meta, paper) in enumerate(zip(metas, papers)):
                    try:
                        title = paper.find('div', class_='list-title mathjax').text.strip()

                        if norm(title) in exist_file_list:
                            logger.info("⚠️ 【downloaded before, pass】\tPaper {}, {},".format(idx, title))
                            continue

                        if norm(title) in exist_parse:
                            logger.info("⚠️ 【checked before, pass】\tPaper {}, {},".format(idx, title))
                            continue

                        authors = paper.find('div', class_='list-authors').text.strip()

                        try:
                            paper_link = meta.find('a', title="Download PDF")['href']
                            paper_url = "https://arxiv.org" + paper_link.replace("pdf", "abs")
                        except Exception as e:
                            logger.error(f"Error getting paper URL: {str(e)}")
                            continue

                        abstract = ""
                        try:
                            paper_soup = get_abstract(paper_url)
                            abstract = paper_soup.find('blockquote', class_='abstract').text.strip()
                        except Exception as e:
                            logger.info(f"❌ 【parse abstract error, pass】\tPaper {idx}, {title}, Error: {str(e)}")

                        if keyword not in title.lower() and keyword not in abstract.lower():
                            logger.info("⚠️ 【not related to {}, pass】\tPaper {}, {},".format(keyword, idx, title))
                            fw_exist_parse.write(norm(title) + "\n")
                            continue

                        date = "Empty Date"
                        try:
                            version_info = paper_soup.find('div', class_='submission-history').text.strip()
                            date_pattern = r'\w{3}, \d{1,2} \w{3} \d{4} \d{1,2}:\d{1,2}:\d{1,2} UTC'
                            match = re.search(date_pattern, version_info)
                            if match:
                                date = match.group(0)
                        except Exception as e:
                            logger.error(f"Error extracting date: {str(e)}")

                        logger.info("✅ 【parsed】\tPaper {}, {},".format(idx, title))
                        fw_exist_parse.write(norm(title) + "\n")

                        statistic.append([title, authors, paper_url, date, abstract])
                    except Exception as e:
                        logger.error(f"Error processing paper {idx}: {str(e)}")
                        continue
            except Exception as e:
                logger.error(f"Error parsing HTML: {str(e)}")
        else:
            logger.info("❌ Error parse {} with status_code: {}".format(arxiv_url, response.status_code))
    except Exception as e:
        logger.error(f"Error requesting URL {arxiv_url}: {str(e)}")
    
    try:
        fw_exist_parse.close()
    except:
        pass

    return total_num, statistic
