# WebScraper

Multithreaded web scraper with file download, gallery and full listing including images' parent webpage for easier referencing.
Useful for academic research. Please do not use to do harm.

## Requirements
 * Python 3.7
 * PIP
 * Internet connection
 
## Installation
 Run `python -m pip install -r .\requires.txt` to install libraries
 
## Run
 Use `python scraper.py <url>` to get started with default settings. Type `python scraper.py help` for full details about the usage.
 
## Details
 ### Usage
    .\scraper.py <target_url> [maxdepth=10] [strictroot=f] [timeout=10] [retry=2] [ext=jpg,jpeg,png] [maxthread=20] [allorigins=f] [summary=t] [maxrate=60]
    
 ### Parameters list as follow:
        target_url              : URL of the first page to scrap.
        maxdepth                : Max depth for recurrent crawling.
        maxthread               : Limit threads to use.
        maxrate                 : Limit request per second allowed.
        retry                   : Quantity of retry allowed if any request timeout.
        timeout                 : Delay before considering a request as timed-out.
        ext                     : Valid images extensions list.
        strictroot              : Target URL will be required to be part of all pages' URL to crawl (=target_url/*).
        allorigins              : Allow images to be downloaded from any domain.
        summary                 : by default, all activities won't generate a new line in the console.

## Notes
- This tool does not come with any guarantee of exhaustivity. If images are stored in a data-* not taken into account, or stored as a string, this will have to be taken into account with further development.
- Websites tend to not like scrapers. Also you will probably encounter countermeasures getting in the way. Tweak query limit rate, and timeout delays, and idealy ask permission for unrestricted access.
- Timeout delays can vary depending on servers location and connection stability. Timedout links are presented at the end of the report page.

## Author
 Wr0ng.Name - https://wr0ng.name
