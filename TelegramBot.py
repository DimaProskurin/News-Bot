import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
from telegram.ext import Updater, CommandHandler
import Parse
import DB
import json
from collections import defaultdict

CHAT_ID = '166532268'
TOKEN = "579989274:AAEzwSK5zi_HASYfDrzDn1rV3RCfa8OEbYg"
URL = 'https://www.rbc.ru/story/'
INTERVAL = 3600  # in seconds => every 60 min


def start(bot, update):
    """Send a message when the command /start is issued."""
    update.message.reply_text('Hi!')


def help(bot, update):
    """Send a message when the command /help is issued."""
    text = '''
    new_docs <N> - показать N самых свежих новостей
new_topics <N> - показать N самых свежих тем
topic <topic_name> - показать описание темы и заголовки 5 самых свежих новостей в этой теме
doc <doc_title> - показать текст документа с заданным заголовком
words <topic_name> - показать 5 слов, лучше всего характеризующих тему
describe_doc <doc_title> - вывести статистику по документу
describe_topic <topic_name> - вывести статистику по теме
'''
    update.message.reply_text(text)


def update_news(bot, job):
    topics = Parse.parse_topics(URL)
    for t in topics:
        Parse.parse_one_doc_to_set_topic_time(t)
    topics = DB.remain_need_to_update_topics(topics)
    topics = Parse.parse_docs(topics)
    DB.update_DB(topics)


def new_docs(bot, update, args):
    """show n newest docs"""
    amount = int(args[0])
    res = DB.select_newest_docs(amount)
    for d in res:
        update.message.reply_text(str(d.time) + ' ' + d.name + '\n' + d.link)


def new_topics(bot, update, args):
    """show n newest topics"""
    amount = int(args[0])
    res = DB.select_newest_topics(amount)
    for t in res:
        update.message.reply_text(str(t.time) + ' ' + t.name + '\n' + t.link)


def topic(bot, update, args):
    """show descrp of topic and 5 newest docs of topic"""
    topic_name = ' '.join(args)
    t = DB.select_topic(topic_name)
    text = [t.description + '\n']
    i = 0
    while i < 5 and i < len(t.documents):
        text.append(t.documents[i].name)
        i += 1
    update.message.reply_text('\n'.join(text))


def doc(bot, update, args):
    """show text of doc"""
    doc_name = ' '.join(args)
    d = DB.select_doc(doc_name)
    update.message.reply_text(d.paragraphs)


def describe_doc(bot, update, args):
    """show doc's statistics"""
    doc_name = ' '.join(args)
    dc = DB.select_doc(doc_name)
    len_stat = json.loads(dc.len_word_frequency)
    freq_stat = json.loads(dc.freq_word_frequency)

    plt.bar([int(i) for i in len_stat],
            list(len_stat.values()),
            align='center')
    plt.title('Распределение длин слов')
    plt.savefig('len_pic' + str(doc_name) + '.png')
    bot.send_photo(chat_id=CHAT_ID,
                   photo=open('len_pic' + str(doc_name) + '.png',
                              'rb'))
    plt.close()

    plt.bar([int(i) for i in freq_stat],
            list(freq_stat.values()),
            align='center')
    plt.title('Распределение частот слов')
    plt.savefig('freq_pic' + str(doc_name) + '.png')
    bot.send_photo(chat_id=CHAT_ID,
                   photo=open('freq_pic' + str(doc_name) + '.png',
                              'rb'))
    plt.close()


def describe_topic(bot, update, args):
    """show topic's statistics"""
    topic_name = ' '.join(args)
    tc = DB.select_topic(topic_name)
    text = ['Количество документов в теме: ' + str(len(tc.documents))]

    avg_len_doc = 0
    for dc in tc.documents:
        avg_len_doc += len(dc.paragraphs)
    avg_len_doc /= len(tc.documents)
    text.append('Средняя длина документа: ' + str(avg_len_doc))
    update.message.reply_text('\n'.join(text))

    len_stat = json.loads(tc.len_word_frequency)
    freq_stat = json.loads(tc.freq_word_frequency)

    plt.bar([int(i) for i in len_stat],
            list(len_stat.values()),
            align='center')
    plt.title('Распределение длин слов в рамках всей темы')
    plt.savefig('len_pic' + str(topic_name) + '.png')
    bot.send_photo(chat_id=CHAT_ID,
                   photo=open('len_pic' + str(topic_name) + '.png',
                              'rb'))
    plt.close()

    plt.bar([int(i) for i in freq_stat],
            list(freq_stat.values()),
            align='center')
    plt.title('Распределение частот слов в рамках всей темы')
    plt.savefig('freq_pic' + str(topic_name) + '.png')
    bot.send_photo(chat_id=CHAT_ID,
                   photo=open('freq_pic' + str(topic_name) + '.png',
                              'rb'))
    plt.close()


def words(bot, update, args):
    """show 5 most relevant words for topic"""
    topic_name = ' '.join(args)
    t = DB.select_topic(topic_name)
    t_tags = defaultdict(int)
    for d in t.documents:
        for tg in d.tags:
            t_tags[tg.name] += 1
    sorted_tags = sorted(t_tags, key=lambda x: t_tags[x], reverse=True)

    text = []
    i = 0
    while i < 5 and i < len(sorted_tags):
        text.append(sorted_tags[i])
        i += 1

    update.message.reply_text('\n'.join(text))


def main():
    """Start the bot."""
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(TOKEN)

    if not updater.job_queue.get_jobs_by_name('update_news'):
         updater.job_queue.run_repeating(update_news,
                                         interval=INTERVAL,
                                         first=0)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("new_docs", new_docs,
                                  pass_args=True))
    dp.add_handler(CommandHandler("new_topics", new_topics,
                                  pass_args=True))
    dp.add_handler(CommandHandler("topic", topic,
                                  pass_args=True))
    dp.add_handler(CommandHandler("doc", doc,
                                  pass_args=True))
    dp.add_handler(CommandHandler("words", words,
                                  pass_args=True))
    dp.add_handler(CommandHandler("describe_doc", describe_doc,
                                  pass_args=True))
    dp.add_handler(CommandHandler("describe_topic", describe_topic,
                                  pass_args=True))

    # Start the Bot
    updater.start_polling()

    updater.idle()


main()
