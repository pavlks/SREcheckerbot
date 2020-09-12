from sqlalchemy import create_engine, func, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import sessionmaker

from tabulate import tabulate
from datetime import date

Base = declarative_base()


class Status(Base):
    __tablename__ = 'statuslogger'

    id = Column('id', Integer, primary_key=True, autoincrement=True)
    telegram_id = Column('telegram_id', Integer)
    date = Column('date', String)
    status = Column('status', String)
    timedelta = Column('timedelta', Integer)


    def new_log(self, telegram_id, chdate, status, timedelta):
        engine = create_engine('sqlite:///stlog.db')
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        new_log = Status(
            telegram_id=telegram_id,
            date=chdate,
            status=status,
            timedelta=timedelta
        )
        session.add(new_log)
        session.commit()
        session.close()
        return

    def __repr__(self):
        return "<Log (id='%s', date='%s', status='%s', timedelta='%s' days)>" % (self.id, self.date, self.status, self.timedelta)
