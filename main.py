import cfscrape
from bs4 import BeautifulSoup
import json
import time

REQUESTS_MANAGER = cfscrape.CloudflareScraper()
GET = REQUESTS_MANAGER.get
POST = REQUESTS_MANAGER.post
JSON_TO_TABLE = json.loads

WEBHOOKS = [
    'https://discord.com/api/webhooks/895077077273935933/p8EankULZliTMjEnZ7eRaBBCfPCj61qCZsbbj3QbE3oHIyn5tyglbT6s-Wuy_deNyszU'
]

COUNTRY_LINKS = {
    'IT' : 'https://www.zalando.it/release-calendar/sneakers-uomo/'
}

COUNTRY_BASE_URL = {
    'IT' : 'https://www.zalando.it/'
}

oldArticles = []

def validate_country(countryCode):
    return not (COUNTRY_LINKS[countryCode] == None)

def get_page_data(countryCode):

    if validate_country(countryCode):
        response = GET(COUNTRY_LINKS[countryCode])
        if response.status_code == 200:
            return response.content
        else:
            return { 'error' : 'Invalid Status Code', 'status_code' : response.status_code}
    return { 'error' : 'Invalid Country'}

def filter_json(content):
    bs = BeautifulSoup(content,'html.parser')
    foundScripts = bs.find_all('script')

    for script in foundScripts:
        if len(script.contents) == 1:
            if script.contents[0].startswith('window.feedPreloadedState='):
                script = script.contents[0]
                script = script[26:]
                script = script[:-1]
                return JSON_TO_TABLE(script)['feed']['items']

def filter_articles(content):
    for articlesList in content:
        if articlesList['id'] == 'products':
            return articlesList['articles']

def filter_coming_soon(content):
    comingSoonList = []
    for article in content:
        if article['availability']['comingSoon'] == True:
            comingSoonList.append(article)
    return comingSoonList

def adjust_articles_info(content, countryCode):
    adjustedArticlesList = []
    for article in content:
        articleInfo = {}
        rSplit = article['availability']['releaseDate'].split(' ')
        rDate = rSplit[0].split('-')
        rTime = rSplit[1]
        articleInfo['zalandoId'] = article['id']
        articleInfo['releaseDate'] = '%s-%s-%s %s' % (rDate[2],rDate[1],rDate[0],rTime)
        articleInfo['productName'] = article['brand'] + ' ' + article['name']
        articleInfo['originalPrice'] = article['price']['original']
        articleInfo['currentPrice'] = article['price']['current']
        articleInfo['link'] = "%s%s.html" % (COUNTRY_BASE_URL[countryCode],article['urlKey'])
        articleInfo['imageUrl'] = article['imageUrl']

        adjustedArticlesList.append(articleInfo)
    
    return adjustedArticlesList

def compare_articles(articles):
    if len(oldArticles) == 0:
        return articles
    else:
        if len(articles) == len(oldArticles):
            return []
        else:
            articlesToReturn = []
            for article in articles:
                found = False

                for article_ in oldArticles:

                    if article['zalandoId'] == article_['zalandoId']:
                        found = True

                if found == False: 
                    articlesToReturn.append(article)
            
            return articlesToReturn

def get_product_stock(link):
    response = GET(link)
    bs = BeautifulSoup(response.content,'html.parser')
    sizeArray = JSON_TO_TABLE(bs.find("script", {'id' : 'z-vegas-pdp-props'}).contents[0][9:-3])['model']['articleInfo']['units']

    sizeStockArray = []
    for x in sizeArray:
        sizeStockArray.append({
            'size' : x['size']['local'],
            'sizeCountry' : x['size']['local_type'],
            'stock' : x['stock']
        })
    
    return sizeStockArray
        

def send_message(content):

    for article in content:

        stocks = get_product_stock(article['link'])

        sizeString = ''
        countryString = ''
        stockString = ''
        totalStock = 0

        for size in stocks:
            sizeString += size['size'] + '\n'
            countryString += size['sizeCountry'] + '\n'
            stockString += str(size['stock']) + '\n'
            totalStock += size['stock']

        data = {
          "content": None,
          "embeds": [
            {
              "description": "[%s](%s)" % (article['productName'],article['link']),
              "color": None,
              "fields": [
                {
                  "name": "Price",
                  "value": article['currentPrice'],
                  "inline": True
                },
                {
                  "name": "Release Date",
                  "value": article['releaseDate'],
                  "inline": True
                },
                {
                  "name": "Total Stock",
                  "value": totalStock,
                  "inline": True
                }
              ],
              "author": {
                "name": "Sneaker Drop",
                "url": article['link']
              },
              "thumbnail": {
                "url": article['imageUrl']
              }
            },
            {
              "color": None,
              "fields": [
                {
                  "name": "Sizes",
                  "value": sizeString,
                  "inline": True
                },
                {
                  "name": "Country",
                  "value": countryString,
                  "inline": True
                },
                {
                  "name": "Stock",
                  "value": stockString,
                  "inline": True
                }
              ]
            }
          ],
          "username": "᲼",
          "avatar_url": "https://avatars.githubusercontent.com/u/1564818?s=280&v=4"
        }
        for webhook in WEBHOOKS:

            POST(webhook,json=data)

def main():
    global oldArticles
    country = 'IT'
    articles = adjust_articles_info(filter_coming_soon(filter_articles(filter_json(get_page_data(country)))),country)
    newArticles = compare_articles(articles)
    send_message(newArticles)
    oldArticles = articles
    

if __name__ == '__main__':
    while True:
        main()
        time.sleep(2)

