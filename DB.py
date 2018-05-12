from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy import Table
from collections import defaultdict
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

    len_word_frequency = Column(String())
    freq_word_frequency = Column(String())

    documents = relationship('Document')


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


def update_DB(topics):
    Base.metadata.create_all(engine)
    for t in topics:
        res = session.query(Topic).filter(Topic.link == t.link).first()
        if res is not None:
            if res.time < t.time:
                res.time = t.time

                topic_len_freq = defaultdict(
                    int, json.loads(res.len_word_frequency))
                topic_freq_freq = defaultdict(
                    int, json.loads(res.freq_word_frequency))

                for d in t.docs:
                    res_d = session.query(Document).filter(
                        Document.link == d.link).first()

                    if res_d is None:
                        dc = Document(name=d.name,
                                      paragraphs='\n'.join(d.paragraphs),
                                      time=d.time,
                                      link=d.link)

                        word_freq = defaultdict(int)
                        len_freq = defaultdict(int)
                        for w in dc.paragraphs.split():
                            word_freq[w] += 1
                            len_freq[len(w)] += 1
                            topic_len_freq[len(w)] += 1

                        dc.word_frequency = json.dumps(word_freq)
                        dc.len_word_frequency = json.dumps(len_freq)
                        freq_freq = defaultdict(int)
                        for v in word_freq.values():
                            freq_freq[v] += 1
                            topic_freq_freq[v] += 1
                        dc.freq_word_frequency = json.dumps(freq_freq)

                        res.documents.insert(0, dc)

                        for tg in d.tags:
                            tag = Tag(name=tg)
                            res.documents[0].tags.append(tag)

                res.len_word_frequency = json.dumps(topic_len_freq)
                res.freq_word_frequency = json.dumps(topic_freq_freq)
        else:
            tp = Topic(name=t.name,
                       description=t.description,
                       time=t.time,
                       link=t.link)

            topic_word_freq = defaultdict(int)
            topic_len_freq = defaultdict(int)
            topic_freq_freq = defaultdict(int)

            session.add(tp)
            session.commit()

            for d in t.docs:
                dc = Document(name=d.name,
                              paragraphs='\n'.join(d.paragraphs),
                              time=d.time,
                              link=d.link)

                word_freq = defaultdict(int)
                len_freq = defaultdict(int)
                for w in dc.paragraphs.split():
                    word_freq[w] += 1
                    len_freq[len(w)] += 1
                    topic_word_freq[w] += 1
                    topic_len_freq[len(w)] += 1

                dc.word_frequency = json.dumps(word_freq)
                dc.len_word_frequency = json.dumps(len_freq)
                freq_freq = defaultdict(int)
                for v in word_freq.values():
                    freq_freq[v] += 1
                dc.freq_word_frequency = json.dumps(freq_freq)

                tp.documents.append(dc)

                for tg in d.tags:
                    tag = Tag(name=tg)
                    tp.documents[-1].tags.append(tag)

            for v in topic_word_freq.values():
                topic_freq_freq[v] += 1

            tp.len_word_frequency = json.dumps(topic_len_freq)
            tp.freq_word_frequency = json.dumps(topic_freq_freq)

    session.commit()


def select_newest_docs(n):
    res = session.query(Document).order_by(Document.time.desc())[:n]
    return res


def select_newest_topics(n):
    res = session.query(Topic).order_by(Topic.time.desc())[:n]
    return res


def select_topic(topic_name):
    res = session.query(Topic).filter(Topic.name == topic_name).first()
    return res


def select_doc(doc_name):
    res = session.query(Document).filter(Document.name == doc_name).first()
    return res


def remain_need_to_update_topics(topics):
    Base.metadata.create_all(engine)
    need_to_update = []
    for t in topics:
        res = session.query(Topic).filter(Topic.link == t.link).first()
        if res is not None:
            if t.time > res.time:
                need_to_update.append(t)
        else:
            need_to_update.append(t)
    return need_to_update
