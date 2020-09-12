import os.path
import os

from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String
from sqlalchemy import create_engine, func, desc
from sqlalchemy.ext.declarative import declarative_base

from tabulate import tabulate
from datetime import date
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.expected_conditions import presence_of_element_located

Base = declarative_base()

class User(Base):
    __tablename__ = 'srewaitinglist'

    id = Column('id', Integer, primary_key=True, autoincrement=True)
    created = Column('created', String)
    telegram_id = Column('telegram_id', Integer)
    login = Column('login', Integer)
    password = Column('password', String)
    application_date = Column('application_date', String)
    is_active = Column('is_active', Integer, default=1)
    country = Column('country', String)
    status = Column('status', String, default='')
    date = Column('date', String, default='')
    nickname = Column('nickname', String)

    def add_user(self, telegram_id, login, password, date_applied, current_status, nickname):

        # Parse country
        tx1 = str(current_status['expediente'])
        tx2 = tx1.split('/')
        tx3 = tx2[2].lower()
        tx4 = [l for l in tx3 if str(l).isalpha()]
        country_code = ''.join(tx4)

        # Process application date
        dt0 = str(date_applied)
        dt1 = dt0.replace('.', ' ').replace(',', ' ').replace('/', ' ').replace('-', ' ').replace('  ', ' ')
        dt2 = dt1.split()
        application_date = date(year=int(dt2[2]), month=int(dt2[1]), day=int(dt2[0]))

        engine = create_engine('sqlite:///sre.db')
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        if str(current_status['estatusinm']).lower() == 'nuevo ingreso':
            stdate = application_date
        else:
            stdate = date.today()
        new_user = User(
            created=date.today(),
            telegram_id=telegram_id,
            login=login,
            password=password,
            application_date=application_date,
            country=country_code,
            status=current_status['estatusinm'],
            date=stdate,
            nickname=nickname
        )
        session.add(new_user)
        session.commit()
        session.close()
        return ":white_check_mark: <b>" + current_status['estatusinm'] + "</b>" + "\n:round_pushpin: " + current_status['estatusdgaj']

    def status_check(self, login, password):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chromedriver = '/usr/bin/chromedriver'
        os.environ["webdriver.chrome.driver"] = chromedriver
        # chrome_options = webdriver.ChromeOptions()
        # chrome_options.add_argument('--ignore-certificate-errors')
        # chrome_options.add_argument('--ignore-ssl-errors')
        # chrome_options.add_argument('--headless')
        # chrome_options.add_argument('--no-sandbox')
        # chromedriver = os.path.join(os.getcwd(), 'chromedriver.exe')
        # os.environ["webdriver.chrome.driver"] = chromedriver

        with webdriver.Chrome(executable_path=chromedriver, options=chrome_options) as driver:
            try:
                driver.get('https://siactla03.sre.gob.mx/ConsultaExpedienteActualizacion/ConsultaEstadoExpediente.aspx')
                driver.find_element(by='id', value='txtUsuario').send_keys(login)
                driver.find_element(by='id', value='txtContrasenia').send_keys(password)
                driver.find_element(by='id', value='btnConsultar').click()

                WebDriverWait(driver, 10).until(presence_of_element_located((By.ID, 'tbConsulta')))

                expediente = driver.find_element(by='id', value='lblExpediente').text
                estatusinm = driver.find_element(by='id', value='lblEstatusINM').text
                estatusdgaj = driver.find_element(by='id', value='lblEstatusDGAJ').text

                driver.close()
                status = dict()
                status['expediente'] = expediente
                status['estatusinm'] = estatusinm
                status['estatusdgaj'] = estatusdgaj
                return status
            except (TimeoutException, NoSuchElementException):
                return False

    def count_active_users(self):
        engine = create_engine('sqlite:///sre.db')
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        query_result = session.query(User).filter(User.is_active == 1).count()
        session.commit()
        session.close()
        return query_result

    def count_users_by_country(self):
        engine = create_engine('sqlite:///sre.db')
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        query_result = session.query(User.country, func.count(User.id)).group_by(User.country).order_by(desc(func.count(User.id)))
        session.commit()

        countries = list()
        for c in query_result:
            countries.append([str(c[0]).upper(), str(c[1]) + " pax"])
        table = "<code>" + tabulate(countries, tablefmt="pretty") + "</code>"

        session.close()
        return table

    def active_list(self):
        engine = create_engine('sqlite:///sre.db')
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        query_result = session.query(User).filter(User.is_active == 1)
        session.commit()

        active_users = list()
        for u in query_result:
            active_users.append(
                {
                    'telegram_id': u.telegram_id,
                    'status': u.status,
                    'date': u.date,
                    'login': u.login,
                    'password': u.password
                }
            )
        session.close()
        return active_users

    def update_status(self, telegram_id, status):
        engine = create_engine('sqlite:///sre.db')
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        client_info = session.query(User).filter_by(telegram_id=telegram_id)[-1]
        client_info.status = status
        client_info.date = date.today()
        session.commit()
        session.close()
        return

    def get_user_info(self, telegram_id):
        engine = create_engine('sqlite:///sre.db')
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        client_info = session.query(User).filter_by(telegram_id=telegram_id).order_by(desc(User.id)).first()
        session.commit()
        client_info_dict = {
            'id': client_info.id,
            'created': client_info.created,
            'telegram_id': client_info.telegram_id,
            'login': client_info.login,
            'password': client_info.password,
            'application_date': client_info.application_date,
            'is_active': client_info.is_active,
            'country': client_info.country,
            'status': client_info.status,
            'date': client_info.date,
            'nickname': client_info.nickname,
        }
        session.close()
        return client_info_dict

    def __repr__(self):
        return "<User (id='%s', created='%s', login='%s', application date='%s')>" % (self.id, self.created, self.login, self.application_date)
