from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy import Table
from collections import Counter
import json

engine = create_engine('sqlite:///news.db?check_same_thread=False')
Session = scoped_session(sessionmaker(bind=engine))
session = Session()
Base = declarative_base()


class Topic(Base):
    __tablename__ = 'topics'

    id = Column(Integer(), primary_key=True)
    name = Column(String())
    description = Column(String())
    time = Column(DateTime())
    link = Column(String())

    """ Статистика """
    word_frequency = Column(String())
    len_word_frequency = Column(String())
    freq_word_frequency = Column(String())

    documents = relationship('Document')


""" Связующая таблица в БД между Document и Tag """
association_table = Table('association',
                          Base.metadata,
                          Column('doc_id', Integer(),
                                 ForeignKey('documents.id')),
                          Column('tag_id', Integer(),
                                 ForeignKey('tags.id')))


class Document(Base):
    __tablename__ = 'documents'

    id = Column(Integer(), primary_key=True)
    name = Column(String())
    time = Column(DateTime())
    link = Column(String())
    paragraphs = Column(String())

    """ Статистика """
    word_frequency = Column(String())
    len_word_frequency = Column(String())
    freq_word_frequency = Column(String())

    topic_id = Column(Integer(), ForeignKey('topics.id'))
    topic = relationship("Topic", back_populates="documents")
    tags = relationship("Tag", secondary=association_table,
                        backref='documents')


class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer(), primary_key=True)
    name = Column(String())


def create_doc_db(doc):
    """
    Создать документ в БД по переданному документу
    :param doc: документ с информацией
    :return: документ в БД
    """
    new_doc_db = Document(name=doc.name,
                          paragraphs='\n'.join(doc.paragraphs),
                          time=doc.time,
                          link=doc.link)

    words = new_doc_db.paragraphs.split()
    doc_word_freq = Counter(words)
    doc_len_freq = Counter([len(word) for word in words])
    doc_freq_freq = Counter(doc_word_freq.values())

    new_doc_db.word_frequency = json.dumps(doc_word_freq)
    new_doc_db.len_word_frequency = json.dumps(doc_len_freq)
    new_doc_db.freq_word_frequency = json.dumps(doc_freq_freq)

    return new_doc_db


def create_topic_db(topic):
    """
    Создать тему в БД по переданной теме
    :param topic: тема с информацией
    :return: тема в БД
    """
    new_topic_db = Topic(name=topic.name,
                         description=topic.description,
                         time=topic.time,
                         link=topic.link)
    return new_topic_db


def create_tag_db(tag):
    """
    Создать тег в БД по данному тегу
    :param tag: тег с информацией
    :return: тег в БД
    """
    tag_db = Tag(name=tag)
    return tag_db


def refresh_dicts_with_doc(doc_db, topic_db_word_freq, topic_db_len_freq):
    """
    Обновить статистику документа в БД
    :param doc_db: документ в БД
    :param topic_db_word_freq: новые данные о частоте слов
    :param topic_db_len_freq: новые данные о частоте длин
    :return: void
    """
    topic_db_word_freq += json.loads(doc_db.word_frequency)
    topic_db_len_freq += json.loads(doc_db.len_word_frequency)


def fill_statistics(topic_db, topic_db_word_freq, topic_db_len_freq):
    """
    Заполняет данные о статистке темы в БД
    :param topic_db: тема в БД
    :param topic_db_word_freq: данные о частоте слов
    :param topic_db_len_freq: данные о частоте длинн
    :return: void
    """
    topic_db_freq_freq = Counter(topic_db_word_freq.values())
    topic_db.word_frequency = json.dumps(topic_db_word_freq)
    topic_db.len_word_frequency = json.dumps(topic_db_len_freq)
    topic_db.freq_word_frequency = json.dumps(topic_db_freq_freq)


def add_docs_for_new_topic(topic, new_topic_db):
    """
    Добавляет документы в БД к новой теме
    :param topic: тема
    :param new_topic_db: только что созданная тема в БД
    :return: void
    """
    topic_db_word_freq = Counter()
    topic_db_len_freq = Counter()

    for doc in topic.docs:
        new_doc_db = create_doc_db(doc)
        refresh_dicts_with_doc(new_doc_db,
                               topic_db_word_freq,
                               topic_db_len_freq)
        new_topic_db.documents.append(new_doc_db)

        for tag in doc.tags:
            tag_db = create_tag_db(tag)
            new_topic_db.documents[-1].tags.append(tag_db)

    fill_statistics(new_topic_db, topic_db_word_freq, topic_db_len_freq)


def refresh_docs_for_topic(topic, topic_db):
    """
    Добавляет новые документы к теме в БД
    :param topic: тема (вероятно) с новыми документами
    :param topic_db: тема в БД
    :return: void
    """
    topic_db_word_freq = Counter(json.loads(topic_db.word_frequency))
    topic_db_len_freq = Counter(json.loads(topic_db.len_word_frequency))

    for doc in topic.docs:
        doc_db = session.query(Document).filter(
            Document.link == doc.link).first()

        if doc_db is None:
            new_doc_db = create_doc_db(doc)
            refresh_dicts_with_doc(new_doc_db,
                                   topic_db_word_freq,
                                   topic_db_len_freq)
            topic_db.documents.insert(0, new_doc_db)

            for tag in doc.tags:
                tag_db = create_tag_db(tag)
                topic_db.documents[0].tags.append(tag_db)

    fill_statistics(topic_db, topic_db_word_freq, topic_db_len_freq)


def update_DB(topics):
    """
    Обновить БД, используя переданные темы
    :param topics: темы
    :return: void
    """
    Base.metadata.create_all(engine)
    for topic in topics:
        topic_db = session.query(Topic).filter(Topic.link == topic.link).first()
        if topic_db is not None:
            if topic_db.time < topic.time:
                topic_db.time = topic.time
                refresh_docs_for_topic(topic, topic_db)
        else:
            new_topic_db = create_topic_db(topic)
            session.add(new_topic_db)
            session.commit()
            add_docs_for_new_topic(topic, new_topic_db)

    session.commit()


def select_newest_docs(n):
    """
    Выбрать из БД новейшие документы
    :param n: количество
    :return: массив документов БД
    """
    res = session.query(Document).order_by(Document.time.desc())[:n]
    return res


def select_newest_topics(n):
    """
    Выбрать из БД новейшие темы
    :param n: количество
    :return: массив тем БД
    """
    res = session.query(Topic).order_by(Topic.time.desc())[:n]
    return res


def select_topic(topic_name):
    """
    Выбрать из БД тему
    :param topic_name: название
    :return: тема БД
    """
    res = session.query(Topic).filter(Topic.name == topic_name).first()
    return res


def select_doc(doc_name):
    """
    Выбрать из БД документ
    :param doc_name: название
    :return: документ БД
    """
    res = session.query(Document).filter(Document.name == doc_name).first()
    return res


def remain_need_to_update_topics(topics):
    """
    По массиву тем оставить только те,
    данные которых нужно обновить
    :param topics: массив тем
    :return: массив тем, которые надо обновить
    """
    Base.metadata.create_all(engine)
    need_to_update = []
    for topic in topics:
        res = session.query(Topic).filter(Topic.link == topic.link).first()
        if res is not None:
            if topic.time > res.time:
                need_to_update.append(topic)
        else:
            need_to_update.append(topic)
    return need_to_update
