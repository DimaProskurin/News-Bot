import urllib.request
import re
import html
from datetime import datetime
# import locale

# locale.setlocale(locale.LC_ALL, "")
AMOUNT_OF_TOPICS_TO_PARSE = 50
AMOUNT_OF_DOCS_TO_PARSE = 50


class Topic:
    def __init__(self, _name, _link, _description):
        self.name = _name
        self.link = _link
        self.description = _description
        self.time = None
        self.docs = []


class Document:
    def __init__(self, _name, _link, _time):
        self.name = _name
        self.link = _link
        self.time = _time
        self.paragraphs = []
        self.tags = []


def date_convert(s):
    if s.__contains__(','):
        '''Вынужденные меры, так как на сервере не хочет менять locale'''
        s = s.replace('янв', 'jan')
        s = s.replace('фев', 'feb')
        s = s.replace('мар', 'mar')
        s = s.replace('апр', 'apr')
        s = s.replace('мая', 'may')
        s = s.replace('июн', 'jun')
        s = s.replace('июл', 'jul')
        s = s.replace('авг', 'aug')
        s = s.replace('сен', 'sep')
        s = s.replace('окт', 'oct')
        s = s.replace('ноя', 'nov')
        s = s.replace('дек', 'dec')

        try:
            date = datetime.strptime(s, "%d %b, %H:%M")
            return date.replace(year=2018)
        except ValueError:
            # значит, не 2018 года
            return datetime.strptime(s, "%d %b %Y, %H:%M")
    else:
        # если дата сегодняшняя, то есть только время
        date = datetime.strptime(s, "%H:%M")
        return datetime.today().replace(
            hour=date.hour, minute=date.minute, second=0, microsecond=0)


def parse_topics(url):
    response = urllib.request.urlopen(url)
    html_ans = response.read().decode('utf-8')
    blocks_topics = re.findall(
        r'<div class="item item_story js-story-item">(.*?)</div>',
        html_ans, re.DOTALL)

    topics = []
    for b in blocks_topics:
        topic_link = re.findall(
            r'<a href="(.*)" class="item__link no-injects">',
            b, re.DOTALL)[0]
        topic_name = re.findall(
            r'<span class="item__title">(.*?)</span>',
            b, re.DOTALL)[0]
        topic_description = re.findall(
            r'<span class="item__text">(.*?)</span>',
            b, re.DOTALL)[0].strip()
        topic = Topic(topic_name, topic_link, topic_description)
        topics.append(topic)
        if len(topics) >= AMOUNT_OF_TOPICS_TO_PARSE:
            break

    return topics[:-1]  # так как "герои РБК"


def parse_docs(topics):
    for t in topics:
        response = urllib.request.urlopen(t.link)
        html_ans = response.read().decode('utf-8')
        blocks_docs = re.findall(
            r'<div class="item item_story-single js-story-item">(.*?)</div>',
            html_ans, re.DOTALL)

        docs = []
        for b in blocks_docs:
            doc_link = re.findall(
                r'<a href="(.*)" class="item__link no-injects js-yandex-counter">',
                b, re.DOTALL)[0]
            doc_name = re.findall(
                r'<span class="item__title">(.*?)</span>',
                b, re.DOTALL)[0]
            doc_time = re.findall(
                r'<span class="item__info">(.*?)</span>',
                b, re.DOTALL)[0]
            doc = Document(doc_name, doc_link, date_convert(doc_time))
            docs.append(doc)
            if len(docs) >= AMOUNT_OF_DOCS_TO_PARSE:
                break

        for d in docs:
            doc_link = d.link
            response = urllib.request.urlopen(doc_link)
            html_ans = response.read().decode('utf-8')

            paragraphs = re.findall(r'<p>(.*?)</p>', html_ans, re.DOTALL)
            paragraphs = [
                html.unescape(re.sub(r'(\<(/?[^>]+)>)', '', item)).strip()
                for item in paragraphs]

            tags = re.findall(
                r'class="article__tags__link">(.*?)</a>',
                html_ans, re.DOTALL)
            d.paragraphs = paragraphs
            d.tags = tags

        t.docs = docs
        t.time = t.docs[0].time

    return topics


def parse_one_doc_to_set_topic_time(topic):
    response = urllib.request.urlopen(topic.link)
    html_ans = response.read().decode('utf-8')
    blocks_docs = re.findall(
        r'<div class="item item_story-single js-story-item">(.*?)</div>',
        html_ans, re.DOTALL)
    b = blocks_docs[0]
    doc_time = re.findall(
        r'<span class="item__info">(.*?)</span>',
        b, re.DOTALL)[0]
    topic.time = date_convert(doc_time)
