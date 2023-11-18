import multiprocessing 
import time
from random import randint

PROCESSES = 4

url_queue = multiprocessing.Queue() #url queue for multiprocessing


url_queue.put("start") #add two urls
url_queue.put("second")



def process_url(queue, url_dict, urls, i, dict_lock): #function to process urls
    while not queue.empty():
        url = queue.get() #grab a url from queue
        #print(url, multiprocessing.current_process())
        with dict_lock: #aquire lock to see if url is in dictionary 
            if(url in url_dict): #check if url has been visited 
                continue
            url_dict[url] = "visited" #visit url 
            #lock released 
        print(url, multiprocessing.current_process()) #print url
        if(i < 10): #only for testing purposes this is where the url will be processed
            for n in range(1, 10): #add 10 urls to queue
                queue.put(urls[randint(0, 999)]) #add random url to queue
                queue.put(100) #add 100 to queue to make sure that no repeats
            i = i+1 #this variable is not protected with a lock so there can be interesting behaviour with it
    return True

def run():
    processes = []
    manager = multiprocessing.Manager()
    dict_lock = multiprocessing.Lock()
    url_dict = manager.dict()
    urls = []
    for i in range(0, 1000):
        urls.append(i)
    
    print(urls)
    for n in range(PROCESSES):
        i = 0
        p = multiprocessing.Process(target=process_url, args=(url_queue, url_dict, urls, i, dict_lock,))
        processes.append(p)
        p.start()
    for p in processes:
        p.join()

    url_queue.close()

    print(url_dict)
    print(len(url_dict))

if __name__ == "__main__":
    run()
        

