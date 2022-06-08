# -*- encoding: utf8 -*-

import threading, queue

import requests
import urllib, socket, time, sys, re, mimetypes, math
from os import path, mkdir, rename, unlink, makedirs
import urllib.parse
from bs4 import BeautifulSoup
from datetime import timedelta, date
import dateutil.parser

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import logging # hide encoding warnings, remove to debug!
logging.disable(logging.WARNING)

global domain, max_depth, output_folder, output_report_file, allowed_img_ext, already_processed_url, already_processed_img, media_path, report_filepath, scheme, url_root, strict_root, timeout_request, target_url, session, parser, proxies, timeout_retry, urls_to_process, reporting_queue, blacklist_ext, timedout_queue, allow_all_origin, blacklist_url_content, request_header, cli_summary, cli_end_char, rate_limiter, run_threads, default_rate_thread_ratio, max_printed_progress

try:
    import lxml
    parser = 'lxml'
except ImportError:
    parser = 'html.parser'
    pass
    
# Init internal globals
#
max_printed_progress = [0, 0]
run_threads = True
runtime_start = time.time()
args_offset = 0
already_processed_url= queue.Queue(maxsize=0)
already_processed_img = queue.Queue(maxsize=0)
urls_to_process = queue.Queue(maxsize=0)
reporting_queue = queue.Queue(maxsize=0)
timedout_queue = queue.Queue(maxsize=0)
session = requests.session()
output_report_file = 'scraping-report'
proxies = None
request_header = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Accept": "*/*",
    "Accept-Language": "fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3",
}
blacklist_ext = ['mp4', 'mp3', 'mpg', 'avi', 'mov', 'wav', 'swf', 'flv', 'pdf', 'doc', 'docx', 'xslx', 'xls', 'ppt', 'pptx', 'zip', 'rar']
blacklist_url_content = ['docreader', 'readspeaker']
cli_end_char = '\r'
default_rate_thread_ratio = 3
#
# End of internal globals init



# Default global params
#
max_threads = 20
rate_limiter = max_threads * default_rate_thread_ratio
timeout_retry = 2
timeout_request = 10
max_depth = 10
output_folder = 'media'
allowed_img_ext = ['jpg', 'jpeg', 'png']
allow_all_origin = False
strict_root = False
cli_summary = True
#
# End of deault global params



try:
    target_url = sys.argv[1]
    
    if 'help' in target_url:
        raise Exception("help: display this help screen")
    
    overrideMaxRate = False
    changedFromMR = 'default'
    
    overrideMaxThread = False
    changedFromMT = 'default'
    
    while (2 + args_offset) < len( sys.argv ):
    
        if len( sys.argv ) > 2 + args_offset and 'help' in sys.argv[2 + args_offset]:
            raise Exception("help: display this help screen")
    
        elif len( sys.argv ) > 2 + args_offset and sys.argv[2 + args_offset][:9] == 'maxdepth=':
            tmp_max_depth = int(sys.argv[2 + args_offset][9:])
            print('Max depth changed from default (' + str(max_depth) + ') to ' + str(tmp_max_depth))
            max_depth = tmp_max_depth
            args_offset = args_offset + 1
        
        elif len( sys.argv ) > 2 + args_offset and sys.argv[2 + args_offset][:11] == 'strictroot=':
            tmp_strict_root = True if sys.argv[2 + args_offset][11:] == 't' else False
            print('Strict root changed from default (' + str(strict_root) + ') to ' + str(tmp_strict_root))
            strict_root = tmp_strict_root
            args_offset = args_offset + 1
        
        elif len( sys.argv ) > 2 + args_offset and sys.argv[2 + args_offset][:8] == 'timeout=':
            tmp_timeout_request = int(sys.argv[2 + args_offset][8:])
            print('Timeout changed from default (' + str(timeout_request) + ') to ' + str(tmp_timeout_request))
            timeout_request = tmp_timeout_request
            args_offset = args_offset + 1
        
        elif len( sys.argv ) > 2 + args_offset and sys.argv[2 + args_offset][:6] == 'retry=':
            tmp_timeout_retry = int(sys.argv[2 + args_offset][6:])
            print('Timeout retry changed from default (' + str(timeout_retry) + ') to ' + str(tmp_timeout_retry))
            timeout_retry = tmp_timeout_retry
            args_offset = args_offset + 1
        
        elif len( sys.argv ) > 2 + args_offset and sys.argv[2 + args_offset][:4] == 'ext=':
            tmp_allowed_img_ext = sys.argv[2 + args_offset][4:].split(',')
            print('Extensions list changed from default (' + str(allowed_img_ext) + ') to ' + str(tmp_allowed_img_ext))
            allowed_img_ext = tmp_allowed_img_ext
            args_offset = args_offset + 1
        
        elif len( sys.argv ) > 2 + args_offset and sys.argv[2 + args_offset][:10] == 'maxthread=':
            tmp_max_threads = int(sys.argv[2 + args_offset][10:]) or 1
            print('Max threads count changed from ' + changedFromMT + ' (' + str(max_threads) + ') to ' + str(tmp_max_threads))
            max_threads = tmp_max_threads
            args_offset = args_offset + 1
            overrideMaxThread = True
            if not overrideMaxRate:
                tmp_rate_limiter = round(max_threads * default_rate_thread_ratio)
                print('Rate limit (per second) automatically adjusted from ' + changedFromMT + ' (' + str(rate_limiter) + ') to ' + str(tmp_rate_limiter))
                rate_limiter = tmp_rate_limiter
                changedFromMR = 'auto-adjusted'
        
        elif len( sys.argv ) > 2 + args_offset and sys.argv[2 + args_offset][:11] == 'allorigins=':
            tmp_allow_all_origin =  True if sys.argv[2 + args_offset][11:] == 't' else False
            print('Allow all origins changed from default (' + str(allow_all_origin) + ') to ' + str(tmp_allow_all_origin))
            allow_all_origin = tmp_allow_all_origin
            args_offset = args_offset + 1
        
        elif len( sys.argv ) > 2 + args_offset and sys.argv[2 + args_offset][:8] == 'maxrate=':
            tmp_rate_limiter =  int(sys.argv[2 + args_offset][8:])
            print('Rate limit (per second) changed from ' + changedFromMR + ' (' + str(rate_limiter) + ') to ' + str(tmp_rate_limiter))
            rate_limiter = tmp_rate_limiter
            args_offset = args_offset + 1
            overrideMaxRate = True
            if not overrideMaxThread:
                tmp_max_threads = (math.ceil(rate_limiter / default_rate_thread_ratio) or 100) if rate_limiter < 1 or rate_limiter > default_rate_thread_ratio else default_rate_thread_ratio
                print('Max threads count automatically adjusted from ' + changedFromMR + ' (' + str(max_threads) + ') to ' + str(tmp_max_threads))
                max_threads = tmp_max_threads
                changedFromMT = 'auto-adjusted'
        
        elif len( sys.argv ) > 2 + args_offset and sys.argv[2 + args_offset][:8] == 'summary=':
            tmp_cli_summary = True if sys.argv[2 + args_offset][8:] == 't' else False
            print('Output summary changed from default (' + str(cli_summary) + ') to ' + str(tmp_cli_summary))
            cli_summary = tmp_cli_summary
            args_offset = args_offset + 1
            if not cli_summary:
                cli_end_char = '\n'
            
        else:
            raise Exception("Invalid input parameter: " + str(sys.argv[2 + args_offset]))

except Exception as e:
    print('''
    Usage:
    .\scraper.py <target_url> [maxdepth={0}] [strictroot={1}] [timeout={2}] [retry={3}] [ext={4}] [maxthread={5}] [allorigins={6}] [summary={7}] [maxrate={8}]
    
    \ttarget_url\t\t: console IP or hostname
    \tmaxdepth\t\t: max depth scraping (default: {0})
    \tmaxthread\t\t: max thread count (default: {5})
    \tmaxrate\t\t\t: max requests sent per second (default: {8}, put 0 for no limit)
    \tretry\t\t\t: retries if timeout (default: {3})
    \ttimeout\t\t\t: request timeout delay (default: {2} seconds)
    \text\t\t\t: valid images extension (default: {4})
    \tstrictroot\t\t: stick to provided URL as root (default: {1})
    \tallorigins\t\t\t: allow all origins (default: {6})
    \tsummary\t\t\t: show summary as output (default: {7})
    '''.format(str(max_depth), str(strict_root), str(timeout_request), str(timeout_retry), ','.join(allowed_img_ext), str(max_threads), str(strict_root), str(cli_summary), str(rate_limiter)))

    print( "Erreur during initialization. Trace:\n%s" % str(e))
    sys.exit()



# Decorators
#
def RateLimited(max_per_second):
    global max_threads
    '''
    Decorator that make functions not be called faster than
    '''
    if max_per_second > 0:
        lock = threading.Lock()
        minInterval = (1.0 / float(max_per_second)) * max_threads
        def decorate(func):
            lastTimeCalled = [0.0]
            def rateLimitedFunction(args,*kargs):
                lock.acquire()
                elapsed = time.monotonic() - lastTimeCalled[0]
                leftToWait = minInterval - elapsed
                if leftToWait>0:
                    time.sleep(leftToWait)
                lock.release()

                ret = func(args,*kargs)
                lastTimeCalled[0] = time.monotonic()
                return ret
            return rateLimitedFunction
    else:
        def decorate(func):
            def rateLimitedFunction(args,*kargs):
                return func(args,*kargs)
            return rateLimitedFunction
    return decorate
#
# End Decorators



# Functions definition
#
def getUrlParts(url):
    urlDetails = urllib.parse.urlparse(url)
    scheme = (urlDetails.scheme).strip()
    ptDomain = (urlDetails.netloc).split(':')
    domain = ptDomain[0].strip()
    port = ptDomain[1].strip() if len(ptDomain) > 1 else None
    tmpDomain = domain.split('.')
    smDomain = domain.strip() if len(tmpDomain) <= 2 else domain.split('.', 1)[-1].strip()
    sbDomain = None if len(tmpDomain) <= 2 else domain.split('.', 1)[0].strip()
    return { 'scheme': scheme, 'domain': smDomain, 'subdomain': sbDomain, 'port': port }
    
def getDomain(url):
    return getUrlParts(url)['domain']
    
def getFullDomain(url):
    urlDetails = getUrlParts(url)
    portExt = ''
    if urlDetails['port'] is not None:
        portExt = ':' + urlDetails['port']
    return urlDetails['subdomain'] + '.' + urlDetails['domain'] + portExt
    
def getRootUrl(url):
    urlDetails = getUrlParts(url)
    portExt = ''
    if urlDetails['port'] is not None:
        portExt = ':' + urlDetails['port']
    subDomain = ''
    if urlDetails['subdomain'] is not None:
        subDomain = urlDetails['subdomain'] + '.'
    return urlDetails['scheme'] + '://' + subDomain + urlDetails['domain'] + portExt
    
def getFilename(url):
    # Parse filename from URL
    fragmentRemoved = url.split("#")[0]
    queryStringRemoved = fragmentRemoved.split("?")[0]
    schemeRemoved = queryStringRemoved.split("://")[-1].split(":")[-1]
    if schemeRemoved.find("/") == -1:
        return schemeRemoved
    return path.basename(schemeRemoved)

def filterLink(link):
    global already_processed_url, blacklist_ext, blacklist_url_content, domain
    if link is not None:
        fileName = getFilename(link)
        fileType = path.splitext(fileName)[-1]
        if link.startswith('http') and getDomain(link) in domain and fileType[1:].lower() not in blacklist_ext:
            for buc in blacklist_url_content:
                if buc in link:
                    return False
            return True
    return False

def filterImg(imgUrl):
    global already_processed_img
    if imgUrl is not None:
        imgName = getFilename(imgUrl)
        imgType = path.splitext(imgName)[-1]
        if imgUrl.startswith('http'): #  and domain in imgUrl necessary??
            return True
    return False

@RateLimited(rate_limiter)
def getWebContentOrStream(url, stream):
    global timeout_request, timeout_retry, proxies, session, blacklist_ext, timedout_queue, already_processed_img, already_processed_url, target_url, url_root, blacklist_url_content, request_header
    root = None
    res = None
    goget = True
    # HTTP request
    timer = 0
    while goget:
        try:
            res = session.get(url, headers=request_header, verify=False, stream=stream, timeout=timeout_request, proxies=proxies, allow_redirects=True)
            goget = False
            if res is not None and res.status_code == 200 and (len(res.history) <= 1 or (stream and res.url not in already_processed_img.queue) or (not stream and res.url not in already_processed_url.queue)):
                root = getRootUrl(res.url)
                if not filterLink(res.url):
                    res = None
            else:
                raise Exception('Not status 200')
        except requests.exceptions.TooManyRedirects as e:
            print('ERROR: Too many redirect from URL: {0}'.format(url))
            goget = False
            pass
        except requests.exceptions.ConnectionError as e:
            if timer < timeout_retry:
                timer = timer + 1
                time.sleep(timer * 2)
            else:
                if url not in timedout_queue.queue:
                    timedout_queue.put(url)
                goget = False
            pass
        except requests.exceptions.ReadTimeout as e:
            if timer < timeout_retry:
                timer = timer + 1
                time.sleep(timer * 2)
            else:
                if url not in timedout_queue.queue:
                    timedout_queue.put(url)
                goget = False
            pass
        except urllib3.exceptions.ReadTimeoutError as e:
            if timer < timeout_retry:
                timer = timer + 1
                time.sleep(timer * 2)
            else:
                if url not in timedout_queue.queue:
                    timedout_queue.put(url)
                goget = False
            pass
        except requests.exceptions.InvalidURL as e:
            goget = False
            print('WARNING: Invalid URL {}:\n{}'.format(url, str(e)))
            pass
        except Exception as e:
            if timer < timeout_retry:
                timer = timer + 1
                time.sleep(timer * 2)
                pass
            else:
                goget = False
                print('ERROR: Unknown error with query to URL {}:\n{}'.format(url, str(e)))
                pass
    return [res, root]

def getWebContent(url):
    # Interface for HTTP requests
    return getWebContentOrStream(url, False)

def getWebImage(imgUrl, subfolder):
    global allowed_img_ext
    # Download and save image
    global media_path
    imgName = getFilename(imgUrl)
    imgNameUnquote = urllib.parse.unquote(imgName)
    if not path.isfile( path.join(subfolder, imgNameUnquote) ):
        response = getWebContentOrStream(imgUrl, True)[0]
        if response is None:
            return False
        elif not response.ok:
            print('WARNING: [{0}] {1}'.format(str(response.status_code), imgUrl))
            return False
        imgType = path.splitext(imgName)[-1]
        if imgType[1:].lower() not in allowed_img_ext:
            add = False
            contentType = response.headers.get('content-type')
            if contentType is not None:
                contentType = contentType.partition(';')[0].strip()
                for ct in allowed_img_ext:
                    if '.{}'.format(ct) in mimetypes.guess_all_extensions(contentType):
                        add = True
                        imgName = '{}.{}'.format(imgName, ct)
                        imgNameUnquote = urllib.parse.unquote(imgName)
                        break
        else:
            add = True
            
        if add:
            # Create tree if not existing
            if not path.isdir(subfolder):
                try:
                    makedirs(subfolder)
                except FileExistsError:
                    pass
            try:
                with open(path.join(subfolder, imgNameUnquote), 'wb') as handle:
                    for block in response.iter_content(1024):
                        if not block:
                            break
                        handle.write(block)
            except FileNotFoundError:
                pass
        else:
            return False
    return imgName

def getContentBody(url, page):
    global parser
    try:
        if page[0] is not None:
            soup = BeautifulSoup(page[0].content, parser, from_encoding="utf-8")
            if soup is not None:
                body = soup.find('body')
            else:
                body = soup
        else:
            body = page[0]
    except Exception as e:
        body = None
        print('ERROR: Parsing content from URL: {0}\n-- Trace:\n{1}'.format(url, str(e)))
        pass
    return [body, page[1]]
    
def getImagesUrlFromStylesheet(style):
    # Parse links from CSS syntax
    return re.findall(r'\burl\([\'"]?(.*?)[\'"]?\)', str(style))
    
def consolidateLinks(root, link):
    global url_root
    output = link
    if link is not None:
        link = link.strip()
        if link.startswith("//"):
            output = scheme + ':' + link
        elif link.startswith("/"):
            output = url_root if root is None else root + link
        elif not link.startswith("http"):
            output = url_root if root is None else root + '/' + link
    return output

def getContentParts(body):
    links = []
    imgs = []
    if body[0] is None:
        return [links, imgs]
    for metaDate in body[0].find_all('meta', {"name": "last_modified"}) + body[0].find_all('meta', {"http-equiv": "last-modified"}):
        if metaDate.get('content') is not None:
            try:
                dateModified = dateutil.parser.parse(metaDate.get('content'))
                if date.today() > dateModified + timedelta(days=730):
                    body[0] =  None
                    print('Too old: {}'.format(body[1]))
            except:
                pass
    # Get all HTML links
    for link in body[0].find_all('a', {"href": True}):
        if link.get('href') is not None:
            if not link.get('href').startswith('javascript:') and not link.get('href').startswith('mailto:') and not link.get('href').startswith('tel:'):
                linkUrl = consolidateLinks(body[1], link.get('href'))
                if filterLink(linkUrl):
                    links.append(linkUrl)
    # Get all HTML images
    for img in body[0].find_all('img'):
        if img.get('data-src') is not None:
            imgUrl = img.get('data-src')
        elif img.get('src') is not None:
            imgUrl = img.get('src')
        elif img.get('poster') is not None:
            imgUrl = img.get('poster')
        else:
            imgUrl = None
        imgUrl = consolidateLinks(body[1], imgUrl)
        if filterImg(imgUrl):
            imgs.append(imgUrl)
    # Get all HTML images from noscript
    for noscript in body[0].find_all('noscript'):
        for img in noscript.find_all('img'):
            if img.get('data-src') is not None:
                imgUrl = img.get('data-src')
            elif img.get('src') is not None:
                imgUrl = img.get('src')
            else:
                imgUrl = None
            imgUrl = consolidateLinks(body[1], imgUrl)
            if filterImg(imgUrl):
                imgs.append(imgUrl)
    # Get all url in embedded styles
    for div in body[0].find_all('div', {"style": True}):
        divStyle = div.get("style")
        if divStyle is not None:
            styleImgs = getImagesUrlFromStylesheet(divStyle)
            for styleImg in styleImgs:
                tmpUrl = consolidateLinks(body[1], styleImg)
                if filterImg(tmpUrl):
                    imgs.append(tmpUrl)
    # Get all url in CSS styles
    for style in body[0].find_all('style'):
        styleImgs = getImagesUrlFromStylesheet(style)
        for styleImg in styleImgs:
            tmpUrl = consolidateLinks(body[1], styleImg)
            if filterImg(tmpUrl):
                imgs.append(tmpUrl)
    # Get all url in CSS stylesheets
    for stylesheet in body[0].find_all('link', {"type": "text/css"}):
        stylesheetUrl = consolidateLinks(body[1], stylesheet.get('href'))
        styleImgs = getImagesUrlFromStylesheet(getWebContent(stylesheetUrl)[0])
        for styleImg in styleImgs:
            tmpUrl = consolidateLinks(body[1], styleImg)
            if filterImg(tmpUrl):
                imgs.append(tmpUrl)
    return [links, imgs]

def getAndParseWebContent(url):
    return getContentParts(getContentBody(url, getWebContent(url)))

def webScraper(targetUrl, currentDepth):
    global max_depth, target_url, domain, urls_to_process, already_processed_url, strict_root, already_processed_img, url_root, cli_end_char
    # Quit if too deep into it or already processed
    if (currentDepth >= max_depth) or not filterLink(targetUrl) or (targetUrl in already_processed_url.queue) or (strict_root is False and allow_all_origin is False and domain not in targetUrl) or (strict_root is True and target_url not in targetUrl) or (strict_root is True and allow_all_origin is True and domain not in targetUrl and target_url not in targetUrl):
        return
    already_processed_url.put(targetUrl)
    displayUrl = urllib.parse.unquote(targetUrl)
    if url_root in targetUrl:
        displayUrl = targetUrl[len(url_root):]
    if len(displayUrl) == 0:
        displayUrl = '/'
    elif len(displayUrl) > 76:
        tmpSh = displayUrl.split('?')[0]
        if len(tmpSh) > 0 and len(tmpSh) < 76:
            displayUrl = tmpSh + '...'
        else:
            displayUrl = displayUrl[:76] + '...'
    urls, imgs = getAndParseWebContent(targetUrl)
    # For all images and links
    for img in imgs:
        if img is not None and img not in urls_to_process.queue and img not in already_processed_img.queue:
            urls_to_process.put({ 'type':'img', 'depth':currentDepth,'url':img, 'page':targetUrl, 'displayUrl':displayUrl })
    for url in urls:
        if url is not None and url not in urls_to_process.queue and url not in already_processed_url.queue:
            urls_to_process.put({ 'type':'web', 'depth':currentDepth+1, 'url':url, 'displayUrl':displayUrl })
    return

def imgScraper(img, targetUrl, currentDepth, displayUrl):
    global already_processed_img, cli_end_char, media_path
    res = False
    if img not in already_processed_img.queue:
        already_processed_img.put(img)
        # Setup subfolders tree
        subfolder = re.sub(r'[<>:/\|?*"]+',"", media_path)
        tmpPath = urllib.parse.urlparse(targetUrl).path
        tmpPath = tmpPath.split('/') if '/' in tmpPath else tmpPath.split('\\')
        if len(tmpPath) > 1:
            tmpSubfolder = path.join(media_path, re.sub(r'[<>:/\|?*"]+',"", tmpPath[1]))
            if len(tmpPath[1]) < 8 and len(tmpPath) > 2:
                tmpSubfolder = path.join(tmpSubfolder, re.sub(r'[<>:/\|?*"]+',"",tmpPath[2]))
            subfolder = tmpSubfolder
        subfolder = urllib.parse.unquote(subfolder)
        # Scrap image and add it to trace
        res = getWebImage(img, subfolder)
        # Complete the report if success
        if res is not None and res is not False:
            reporting_queue.put([res, targetUrl, displayUrl, str(currentDepth), subfolder])
    return res
        
def processScrapingQueue(tid, q):
    global run_threads, rate_limiter, already_processed_img, already_processed_url, max_printed_progress
    info = ''
    lock = threading.Lock()
    if rate_limiter>0:
        time.sleep((1.0 / float(rate_limiter)) * tid)
    while run_threads:
        item = q.get()
        if item['type'] == 'web':
            webScraper(item['url'], item['depth'])
            info = '>> Scraping ' + item['displayUrl'] + ' ' * (80-len(item['displayUrl']))
        elif item['type'] == 'img':
            res = imgScraper(item['url'], item['page'], item['depth'], item['displayUrl'])
            if res is not None and res is not False:
                info = '+> Image ' + str(res[-64:]) + ' saved!' + ' ' * (64-len(str(res[-64:])))
        
        if lock.acquire(True, 0.005):
            progress = len(already_processed_img.queue)+len(already_processed_url.queue)
            if progress > max_printed_progress[0]:
                max_printed_progress = [progress, len(q.queue)+progress]
            progress = '[{}/{}] '.format(max_printed_progress[0], max_printed_progress[1])
            print(progress + info, end=cli_end_char)
            lock.release()
        q.task_done()
#
# End of Functions Definition



# Initialize globals from parameters
# URL details
url_details = getUrlParts(target_url)
scheme = url_details['scheme']
domain = url_details['domain']
url_root = getRootUrl(target_url)
sanitized_domain = re.sub('[^A-Za-z0-9]+', '', domain)
# Report file details
output_report_file = 'scraping-report-' + sanitized_domain
report_filepath = path.join(sanitized_domain, output_report_file)
# Storage folder details
media_path = path.join(sanitized_domain, output_folder)

# Storage initialization
if not path.isdir(sanitized_domain):
    mkdir(sanitized_domain)
if not path.isdir(media_path):
    mkdir(media_path)
#
# End of Globals Init



# Running sequence only in main thread
if __name__ == '__main__':
    if path.isfile( report_filepath + '.html' ):
        last = report_filepath + '.old'
        if path.isfile( last ):
            unlink( last )
        rename( report_filepath + '.html', last )
    print('''    Session Parameters:
        Max Depth\t\t: {0}
        Attempts\t\t: {2}
        Max threads\t\t: {3}
        Max rate\t\t: {8} hit(s)/s
        Timeout\t\t\t: {1} seconds
        Strict root\t\t: {4}
        Allow all origins\t: {6}
        Output summary\t\t: {7}
        Extensions\t\t: {5}'''.format(max_depth, timeout_request, timeout_retry, max_threads, strict_root, str(allowed_img_ext), str(allow_all_origin), str(cli_summary), str(rate_limiter)))
    # Display, run and report
    # Report initialization
    reportHandle = open(report_filepath + '.html', "a", encoding="utf-8")
    galleryHandle = open(report_filepath + '-gallery.html', "w", encoding="utf-8")
    # Report header
    reportHandle.write('<html><head><style>h1{{ width:100%;text-align:center; }} .head{{ border: 0 !important; font-weight:bolder; }} table{{ width:100%; text-align:center; }} tr:nth-child(odd){{ background-color: #e6f3fc !important; }}</style></head><body><h1>Scraping: {}</h1><h2>Pictures</h2><table><tr class="head"><td>Depth</td><td>Image</td><td>Source</td></tr>'.format(domain))
    galleryHandle.write('<html><head><style>td > table{ width:100%; } img{ max-width:100%; max-height:100%; }</style></head><body><table><tr>')
    # Recursive scraping
    print('Starting scraping...')
    urls_to_process.put({ 'type':'web', 'depth':0, 'url':target_url, 'displayUrl':'/' })
    # Assign workers
    for i in range(max_threads):
        worker = threading.Thread(target=processScrapingQueue, args=(i, urls_to_process,))
        worker.setDaemon(True)
        worker.start()
    urls_to_process.join()
    # Report writing
    i = 0
    while not reporting_queue.empty():
        lineItem = reporting_queue.get()
        reportHandle.write('<tr><td>{3}</td><td>{0}</td><td><a href="{1}">{2}</a></td></tr>'.format(urllib.parse.unquote(lineItem[0]), str(lineItem[1]), str(lineItem[2]), str(lineItem[3])))
        if i % 4 == 0:
            galleryHandle.write('</tr><tr>')
        galleryHandle.write('<td><center><img src="{0}" /><br /><a href="{1}" target="_blank">{2}</a> ({3})</center></td>'.format(path.join('..', lineItem[4], lineItem[0]), str(lineItem[1]), str(lineItem[2]), str(lineItem[3])))
        i = i + 1
    runtime_stop = time.time()
    runtime_total = timedelta(seconds=(runtime_stop - runtime_start))
    galleryHandle.write('</tr></table></body></html>')
    galleryHandle.close()
    # Links timeout
    if not timedout_queue.empty():
        reportHandle.write('</table><h2>Timeout URL:</h2><table><tr class="head"><td>Link</td></tr>')
        for url in timedout_queue.queue:
            reportHandle.write('<tr><td><a href="{0}">{0}</a></td></tr>'.format(str(url)))
    # Run summary
    reportHandle.write("</table><h2>Results Summary:</h2><table>")
    reportHandle.write('<tr><td>Links explored</td><td>{}</td></tr>'.format(str(len(already_processed_url.queue))))
    reportHandle.write('<tr><td>Links timeout</td><td>{}</td></tr>'.format(str(len(timedout_queue.queue))))
    reportHandle.write('<tr><td>Images saved</td><td>{}</td></tr>'.format(str(len(already_processed_img.queue))))
    reportHandle.write('<tr><td>Total duration</td><td>{} seconds</td></tr>'.format(str(runtime_total)))
    # Run parameters
    reportHandle.write("</table><h2>Run Details:</h2><table>")
    reportHandle.write('<tr class="head"><td>Parameter</td><td>Value</td></tr>')
    reportHandle.write('<tr><td>Target URL</td><td>{}</td></tr>'.format(target_url))
    reportHandle.write('<tr><td>Max Depth</td><td>{}</td></tr>'.format(max_depth))
    reportHandle.write('<tr><td>Attempts</td><td>{}</td></tr>'.format(timeout_retry))
    reportHandle.write('<tr><td>Max threads</td><td>{}</td></tr>'.format(max_threads))
    reportHandle.write('<tr><td>Rate limiter</td><td>{} hit(s)/s</td></tr>'.format(rate_limiter))
    reportHandle.write('<tr><td>Timeout</td><td>{} seconds</td></tr>'.format(timeout_request))
    reportHandle.write('<tr><td>Strict root</td><td>{}</td></tr>'.format(strict_root))
    reportHandle.write('<tr><td>Allow all origins</td><td>{}</td></tr>'.format(allow_all_origin))
    reportHandle.write('<tr><td>Extensions</td><td>{}</td></tr>'.format(str(allowed_img_ext)))
    reportHandle.write("</table></body></html>")
    reportHandle.close()
    # Exit
    print(' ' * 92 + '\nDone!')
    print('''
    Statistics: {url}
        Links explored\t:  {linksLen}
        Links timeout\t:  {linksTO}
        Images saved  \t:  {imgSaved}
        Total duration\t:  {duration}
    '''.format(url=target_url, linksLen=str(len(already_processed_url.queue)), imgSaved=str(len(already_processed_img.queue)), duration=str(runtime_total), linksTO=str(len(timedout_queue.queue))))