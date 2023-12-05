import multiprocessing
import time
from random import randint
import pymongo
from selenium import webdriver
from bs4 import BeautifulSoup
from bson.json_util import dumps

PROCESSES = 4
MAX_URLS = 100

url_queue = multiprocessing.Queue()  # url queue for multiprocessing

mongo_clnt = pymongo.MongoClient("mongodb://localhost:27017/")
db = mongo_clnt["scraper_database"]
url_col = db["job_info"]

base_url = "https://www.indeed.com"
query = "software+engineer"
location = "Connecticut"
num_pages = 5

#track the total run time
start = time.time()

#initial queue
#url_queue.put(f"{base_url}/browsejobs/")

for page in range(num_pages):
    url_queue.put(f"{base_url}/jobs?q={query}&l={location}&start={page + 1}0")

#read robots.txt rules - Nathan Benham
rules = []
robots = open("robots.txt", "r")
correct_agent = False

print("DISALLOWED for User-agent: *")
for rule in robots:
    if not rule.strip():
        continue

    if "User-agent: *" in rule:
        correct_agent = True
        continue

    if "User-agent:" in rule and correct_agent:
        correct_agent = False
        break

    if correct_agent:
        if not "Allow:" in rule:
            line = rule.rsplit(":")[1].strip()
            #print(line)
            rules.append(line)

robots.close()

print("END ROBOTS.TXT User-agent: *")

#process the url queue in parallel. - Nathan Benham
def process_url(queue, url_dict, dict_lock, db_lock, job_dict):  # function to process urls
    while not queue.empty():
        url = queue.get()  # grab a url from queue
        # print(url, multiprocessing.current_process())

        print(len(url_dict), url, multiprocessing.current_process())  # print url + proccess ID


        page_info = scrape(url)

        if not page_info:
            continue

        new_urls = page_info["urls"]

        #put urls into queue
        for new_url in new_urls:

            with dict_lock:  # aquire lock to see if url is in dictionary
                if (new_url in url_dict):  # check if url has been visited
                    continue

                url_dict[new_url] = "visited"  # mark url as visited
                # lock released
                if not len(url_dict) >= MAX_URLS: #cap the queue at max urls
                    queue.put(new_url)

        #insert into database
        info = page_info["jobs"]

        #remove any already found jobs from the db query

        if len(info) > 0:
            with db_lock:
                for job in info:
                    if job["url"] in job_dict:
                        info.remove(job)
                        continue
                    else:
                        job_dict[job["url"]] = "true"
                        url_col.insert_one(job)


    return True


#start the multprocessing processes + initialize shared resources - Nathan Benham
def run():
    # initalize multiprocessing
    processes = []

    # locks:
    manager = multiprocessing.Manager()
    dict_lock = multiprocessing.Lock()
    db_lock = multiprocessing.Lock() #used for db and job_dict

    # visited url dict to avoid too many reads/writes from database
    url_dict = manager.dict()
    job_dict = manager.dict()

    # create random number array to act as new urls

    # start PROCESS number of processes working on the queue
    for n in range(PROCESSES):
        p = multiprocessing.Process(target=process_url, args=(url_queue, url_dict, dict_lock, db_lock, job_dict,))
        processes.append(p)
        p.start()

    # block new excecution until all processes are finished
    for p in processes:
        p.join()

    # close the queue
    url_queue.close()

    # print the url dictionary
    print(f'{len(url_dict)} pages found, {MAX_URLS} scraped')

    urls = []
    for item in url_col.find():
        if item["url"] in urls:
            pass
            #print("duplicate", item["url"])
            #print("in dict? ", item["url"] in job_dict)
        else:
            urls.append(item["url"])


#scrape the web page -  Niall Geoghegan and Jenna Noce
def scrape(url):
    # Set up the WebDriver (using Chrome in this example)
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--ignore-ssl-errors')
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
    driver = webdriver.Chrome(options)
    page_info = {}
    try:
        if(can_scrape(url, rules)):
            #print(f"Accessing URL: {url}")  # Print the URL being accessed
            driver.get(url)

            # Process the page content immediately after it loads
            page_info = process_page(driver.page_source, url)
            urls = page_info["urls"]
            jobs = page_info["jobs"]

    except Exception as e:
        print(e)
    finally:
        # Close the browser window
        driver.quit()

    return page_info


#extract the information from the page -  Niall Geoghegan and Jenna Noce
def process_page(html_content, curr_url):
    soup = BeautifulSoup(html_content, 'html.parser')
    links = soup.find('nav', {'role': 'navigation'}).find_all('a') + soup.find_all('a', {'class': 'jobsearch-RelatedQueries-queryItem'})
    urls = []
    jobs = []

    #find job cards in search page
    cards = soup.find_all('div', {'class': 'slider_item'})

    #loop through the found cards + extract info
    for card in cards:
        job_url = card.find('a')
        job_url = job_url.get("href")
        if not "indeed.com" in job_url and not "http" in job_url:
            job_url = f'https://indeed.com{job_url}'
        job_title = card.find('h2', {'class' : 'jobTitle'})
        company = card.find('div', {'class' : 'company_location'})
        company_name = company.find('span')
        company_loc = company.find('div', {'data-testid' : 'text-location'})
        jobs.append({"url" : job_url, "title" : job_title.text.strip(), "company" : company_name.text.strip(), "location" : company_loc.text.strip()})
        #print(jobs)

    #grab the hrefs from the links on page
    for title in links:
        url = title.get("href")
        if not "https://" in url:
            url = f'https://indeed.com{url}'

        if "indeed.com" in url:
            urls.append(url)
            #print(url)

    return {"urls" : urls, "jobs" : jobs}

#compare robots.txt rules to url - Nathan Benham
def can_scrape(url, rules):
    for rule in rules:
        if rule in url:
            return False

    return True



if __name__ == "__main__":
    #Collect inputs Jenna Noce
    print("Enter job title:")
    INPUT = input()
    if not INPUT:
        query = INPUT.replace(' ','+')

    print("Enter location:")
    INPUT = input()
    if not INPUT:
        location = INPUT

    run()
    end = time.time()
    print(url_col.count_documents({}), "jobs found")
    print(f'time elapsed {end - start}')

    #output DB to json
    cursor = url_col.find()
    list_cur = list(cursor)
    json_data = dumps(list_cur, indent = 2)
    with open('data.json', 'w') as file:
        file.write(json_data)
