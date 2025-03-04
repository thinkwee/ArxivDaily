import arxiv

client = arxiv.Client(
  page_size = 10,
  delay_seconds = 10.0,
  num_retries = 5,
)

exist = set()
with open("./exist", "r") as f:
    for line in f:
        exist.add(line.strip())

fw = open("./exist", "a")

def get_search(logger, link, cat, keyword):
    cat2max = {"cs.CL": 140, 
               "cs.CV": 100,
               "cs.CY": 50,
               "cs.HC": 50,
               "cs.IR": 50,
               "cs.LG": 100,
               "cs.MA": 100,
               "cs.SE": 20,
               "cs.NE": 20,
               "cs.AI": 200}
    if link != cat:
        return 0, []
    ret = []
    try:
        search = arxiv.Search(
          query = "ti:{} AND cat:{}".format(keyword, cat),
          max_results = cat2max.get(cat, 100),
          sort_by = arxiv.SortCriterion.SubmittedDate
        )
        
        count = 0 
        try:
            for r in client.results(search):
                try:
                    if r.title in exist:
                        continue
                    fw.write(r.title + "\n")
                    logger.info("{}: {}\t{}".format(count, r.title, str(r.published)))
                    ret.append([r.title, " ".join([item.name for item in r.authors]), r.pdf_url, r.published, r.summary])
                    count += 1
                except Exception as e:
                    logger.error(f"Error processing paper: {str(e)}")
                    continue
        except Exception as e:
            logger.error(f"Error getting results from ArXiv: {str(e)}")
    except Exception as e:
        logger.error(f"Error creating ArXiv search: {str(e)}")
    
    return len(ret), ret

