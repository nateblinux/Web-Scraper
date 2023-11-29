import multiprocessing
import time
from random import randint
import pymongo

PROCESSES = 4

url_queue = multiprocessing.Queue()  # url queue for multiprocessing

mongo_clnt = pymongo.MongoClient("mongodb://localhost:27017/")
db = mongo_clnt["scraper_database"]
url_col = db["urls"]

url_queue.put("start")  # add two urls
url_queue.put("second")


def process_url(queue, url_dict, urls, i, dict_lock, db_lock):  # function to process urls
    while not queue.empty():
        url = queue.get()  # grab a url from queue
        # print(url, multiprocessing.current_process())
        with dict_lock:  # aquire lock to see if url is in dictionary
            if (url in url_dict):  # check if url has been visited
                continue
            url_dict[url] = "visited"  # mark url as visited
            # lock released
        print(url, multiprocessing.current_process())  # print url + proccess ID

        info = {"url": url, "job_title": "Software Engineer", "company": "evil corp",
                "job_desc": "write banking software", "company rating": "1"}  # test data to write to mongodb

        with db_lock:
            url_col.insert_one(info)

        if (i < 10):  # only for testing purposes this is where the url will be processed
            for n in range(1, 10):  # add 10 urls to queue
                queue.put(urls[randint(0, 999)])  # add random url to queue
                queue.put(100)  # add 100 to queue to make sure that no repeat urls processed
            i = i + 1  # this variable is not protected with a lock so there can be interesting behaviour with it

    return True


def run():
    # initalize multiprocessing
    processes = []

    # locks:
    manager = multiprocessing.Manager()
    dict_lock = multiprocessing.Lock()
    db_lock = multiprocessing.Lock()

    # visited url dict to avoid too many reads/writes from database
    url_dict = manager.dict()

    # create random number array to act as new urls
    urls = []
    for i in range(0, 1000):
        urls.append(i)

    print(urls)

    # start PROCESS number of processes working on the queue
    for n in range(PROCESSES):
        i = 0
        p = multiprocessing.Process(target=process_url, args=(url_queue, url_dict, urls, i, dict_lock, db_lock,))
        processes.append(p)
        p.start()

    # block new excecution until all processes are finished
    for p in processes:
        p.join()

    # close the queue
    url_queue.close()

    # print the url dictionary
    print(url_dict)
    print(len(url_dict))


if __name__ == "__main__":
    run()
