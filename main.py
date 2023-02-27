import cfscrape
import json
import re
import colorama
from bs4 import BeautifulSoup


colorama.init()

REQUESTS_MANAGER = cfscrape.CloudflareScraper()
GET = REQUESTS_MANAGER.get
POST = REQUESTS_MANAGER.post
JSON_TO_TABLE = json.loads
TABLE_TO_JSON = json.dumps
COLOR = colorama.Fore

RUB_CURRENCY = 79.49



COUNTRY_LINKS = {
    'IT': 'https://www.zalando.it/release-calendar/sneakers-uomo/',
    'UK': 'https://www.zalando.co.uk/release-calendar/mens-shoes-sneakers/'
}

COUNTRY_BASE_URL = {
    'IT': 'https://www.zalando.it/',
    'UK': 'https://www.zalando.co.uk/'
}


def save_external_articles(content):
    file = open('articles.json', 'w+')
    file.write(TABLE_TO_JSON(content))
    file.close()
    return content


def load_external_articles():
    open('articles.json', 'a+')
    file = open('articles.json', 'r')
    fileContent = file.read()
    if len(fileContent) < 2:
        save_external_articles([])
        return []
    try:
        file.close()
        return JSON_TO_TABLE(fileContent)
    except:
        save_external_articles([])
        return []


def validate_country(countryCode):
    return not (COUNTRY_LINKS[countryCode] == None)


def get_page_data(countryCode):

    if validate_country(countryCode):
        response = GET(COUNTRY_LINKS[countryCode])
        if response.status_code == 200:
            return response.content
    return {'error': 'Invalid Country'}


def filter_json(content):
    bs = BeautifulSoup(content, 'html.parser')
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

def shoe_size_from_IT_to_RUS(itSizeStr):
    rusSize = float(itSizeStr.split(' ')[0]) - 1.
    return rusSize
def adjust_articles_info(content, countryCode):
    adjustedArticlesList = []
    for article in content:
        articleInfo = {}
        rSplit = article['availability']['releaseDate'].split(' ')
        rDate = rSplit[0].split('-')
        rTime = rSplit[1]
        articleInfo['zalandoId'] = article['id']
        articleInfo['releaseDate'] = '%s-%s-%s %s' % (
            rDate[2], rDate[1], rDate[0], rTime)
        articleInfo['productName'] = article['brand'] + ' ' + article['name']
        articleInfo['originalPrice'] = article['price']['original']
        articleInfo['currentPrice'] = article['price']['current']
        articleInfo['link'] = "%s%s.html" % (
            COUNTRY_BASE_URL[countryCode], article['urlKey'])
        articleInfo['imageUrl'] = article['imageUrl']
        articleInfo['sizes'] = ''
        for position in article['simples']:
            articleInfo['sizes'] += position['size']['local_size'] + '(' + position['size']['local_size_type'] +')' + '; '

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




oldArticles = load_external_articles()

def eu_to_rub_converter(eu_price_str):
    eu_price = re.findall("\d+", eu_price_str)[0]
    rub_price = round(float(eu_price) * (RUB_CURRENCY + 7.) * 1.4)
    return str(rub_price)
def vk_yml_print(content):

    ymlFile = open('vk_shop.xml', 'a+')

    #begin
    ymlFile.write('<?xml version="1.0" encoding="utf-8"?> \n')
    ymlFile.write('<yml_catalog date="2021-04-01 12:20"> \n')
    ymlFile.write('<shop> \n')
    ymlFile.write('<name>vk.com</name> \n')
    ymlFile.write('<company>vk.com</company> \n')
    ymlFile.write('<url>https://vk.com/</url> \n')
    ymlFile.write('<currencies> \n')
    ymlFile.write(' <currency id="RUB" rate="1"/> \n')
    ymlFile.write('</currencies> \n')

    #body
    ymlFile.write('<offers> \n')
    for article in content:
        ymlFile.write('<offer id=\"' + article['zalandoId'] + '\">' + '\n')
        ymlFile.write('<price>' + eu_to_rub_converter(article['currentPrice']) + '</price>\n')
        ymlFile.write('<currencyId>RUB</currencyId> \n')
        ymlFile.write('<name>' + article['productName'] + '</name>\n')
        ymlFile.write('<description>' + article['productName'] + ' available sizes: (' + article['sizes'] + ')'+ '</description>\n')
        ymlFile.write('<picture>' + article['imageUrl'] + '</picture>\n')
        ymlFile.write('</offer> \n')

    ymlFile.write('</offers> \n')

    #end
    ymlFile.write('</shop> \n')
    ymlFile.write('</yml_catalog> \n')

    ymlFile.close()

def main():
    global oldArticles
    country = 'IT'
    articles = adjust_articles_info(filter_coming_soon(
        filter_articles(filter_json(get_page_data(country)))), country)
    newArticles = compare_articles(articles)
    vk_yml_print(newArticles)
    save_external_articles(articles)
    oldArticles = articles


if __name__ == '__main__':
    main()
