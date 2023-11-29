from selenium import webdriver
from bs4 import BeautifulSoup

#I tried a shot at your program, I don't know how you are going to get around the Cloudflare and the JavaScript.
#I would rather not use the selenium framework, but this was the best way for me to access the different webpages.
#I just think indeed.com is a very hard website that requires a lot of effort to scrape through compared to some
#smaller website. If you got this, then lets do it your way.



def main():
    base_url = "https://www.indeed.com"
    query = "software+engineer"
    location = "Connecticut"
    num_pages = 5

    # Set up the WebDriver (using Chrome in this example)
    driver = webdriver.Chrome()

    try:
        for page in range(num_pages):
            url = f"{base_url}/jobs?q={query}&l={location}&start={page + 1}"
            print(f"Accessing URL: {url}")  # Print the URL being accessed
            driver.get(url)

            # Process the page content immediately after it loads
            job_titles = process_page(driver.page_source)
            print(f"Page {page + 1}: Found {len(job_titles)} job titles.")

    finally:
        # Close the browser window
        driver.quit()

#This part can be converted into MongoDB
def process_page(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    job_titles = soup.find_all('h2', {'class': 'jobTitle'})

    for title in job_titles:
        print(title.text.strip())

    return job_titles


if __name__ == "__main__":
    main()
