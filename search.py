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
    search = arxiv.Search(
      query = "ti:{} AND cat:{}".format(keyword, cat),
      max_results = cat2max[cat],
      sort_by = arxiv.SortCriterion.SubmittedDate
    )
    
    count = 0 
    for r in client.results(search):
        if r.title in exist:
            continue
        fw.write(r.title + "\n")
        logger.info("{}: {}\t{}".format(count, r.title, str(r.published)))
        ret.append([r.title, " ".join([item.name for item in r.authors]), r.pdf_url, r.published, r.summary])
        count += 1

    return len(ret), ret

