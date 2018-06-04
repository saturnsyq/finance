#!/usr/bin/python3
# coding=utf-8

import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.keys import Keys
import time
import tamCommonLib
import credentials

import imaplib
import email
from email.parser import Parser
from email.header import decode_header
from email.utils import parseaddr
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.utils import COMMASPACE,formatdate
from email import encoders
import re
import datetime
import logging


##logging configuration
logging.basicConfig(level=logging.INFO,
                format='%(asctime)s %(filename)s[line:%(lineno)3d] %(levelname)s %(message)s',
                datefmt='%Y-%m-%d %a %H:%M:%S',
                filename='/home/local/ANT/yongqis/BondMonitorVolume.%s.log'%datetime.datetime.now().strftime('%Y-%m-%d.%H%M%S'),
                filemode='w')


mail_list = ['yongqis@amazon.com']
display_in_mail = 1

def send_mail(fro, to, subject, text, files=[], mtype='plain'):
    #assert type(server) == dict
    #assert type(to) == list
    #assert type(files) == list

    msg = MIMEMultipart()
    msg['From'] = fro
    msg['Subject'] = subject
    msg['To'] = ','.join(to)  # COMMASPACE==', '
    #msg['Date'] = formatdate(localtime=True)
    msg.attach(MIMEText(text,mtype,'utf-8'))

    for file in files:
        part = MIMEBase('application', 'octet-stream')  # 'octet-stream': binary data
        part.set_payload(open(file, 'rb').read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(file))
        msg.attach(part)

    import smtplib
    smtp = smtplib.SMTP('mail-relay.amazon.com')
    #smtp.login(server['user'], server['passwd'])
    smtp.sendmail(fro, to, msg.as_string())
    smtp.close()

def get_sell1_volume(driver,url):
    driver.get(url)
    time.sleep(2)
    driver.implicitly_wait(2)  # 等待3秒
    soup = BeautifulSoup(driver.page_source, "html.parser")
    table = soup.find('table', id='flex0')
    repo_info = table.find('thead').find('table').find_all('tr')[2].find_all('td')[1]
    repo = float(re.findall(r'^回购资金利用率：([\d\.]+)%?$', repo_info.getText().strip())[0])
    # adjust the italic font repo to 0
    span = repo_info.find('span')
    if span is not None and span.attrs.get('style') is not None and span.attrs['style'].find('font-style:italic') >= 0:
        repo = 0
    tbody = table.find_all('tbody')[1]
    volume=None
    try:
        # for sell in ('sell1', 'sell2', 'sell3', 'sell4', 'sell5'):
        tr = tbody.find('tr', id='sell1')
        if tr is not None:
            col = 0
            price, volume, dur1, ytm1, dur2, ytm2 = 0, 0, 0, 0, 0, 0
            for td in tr.findAll('td'):
                col += 1
                if col == 2: price = float(td.getText().strip())
                if col == 3: volume = round(float(td.getText().strip()), 1)
                if col == 5: ytm1 = float(td.getText().strip())
                if col == 7: dur1 = float(td.getText().strip())
                if col == 10: ytm2 = float(td.getText().strip())
                if col == 12: dur2 = float(td.getText().strip())

    except:
        # do nothing, just skipping this one
        print("error happend, skip url:" + url)
    return volume

def get_exclude_list():
    try:
        conn = tamCommonLib.getMysqlConnect()
        cursor = conn.cursor()
        cursor.execute("select code from finance.bond_exclude_list")
        bond_list = [code for code, in cursor.fetchall()]
    except Exception as e:
        bond_list = list()
    return bond_list

# url='https://www.jisilu.cn/data/bond/?do_search=true&sort_column=&sort_order=&forall=0&treasury=1&from_rating=1&from_issuer_rating=1&from_year_left=0&from_repo=0.56&from_ytm=5.3&from_volume=0&from_market=&y1=&y2=&to_rating=99&to_issuer_rating=99&to_year_left=2&to_repo=2&to_ytm=8&to_volume='
url='https://www.jisilu.cn/data/bond/'
bond_url='https://www.jisilu.cn/data/bond/detail/%s'
repo_rate=3.6
bar=11   #ytm bar
vol=10
if __name__ == '__main__':
    try:
        conn = tamCommonLib.getMysqlConnect()
        cursor = conn.cursor()

        from selenium import webdriver
        import ssl

        ssl._create_default_https_context = ssl._create_unverified_context  # 取消证书认证
        try:
            driver = webdriver.PhantomJS(executable_path='/home/local/ANT/yongqis/finance/phantomjs')
            driver.get('https://www.jisilu.cn/login/')
            elem = driver.find_element_by_id('aw-login-user-name')
            if elem is not None:
                driver.find_element_by_id('aw-login-user-name').send_keys(Keys.TAB)  # 定位并输入用户名
                driver.find_element_by_id('aw-login-user-password').send_keys(Keys.TAB)  # 定位并输入用户名
                driver.find_element_by_id('aw-login-user-name').send_keys(credentials.jisilu_user)   #定位并输入用户名
                driver.find_element_by_id('aw-login-user-password').send_keys(credentials.jisilu_password)  # 定位并输入用户名
                driver.find_element_by_id('login_submit').click()

            time.sleep(3)
            driver.implicitly_wait(30)
            driver.get(url)
            time.sleep(30)
            #driver.implicitly_wait(3)  # 等待3秒
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(driver.page_source, "html.parser")
            # print(soup)
            table = soup.find('tbody', id='bond_table_body')
            data =[]
            #meet_list = [['code','name','duration','ytm','actual_ytm']]
            meet_list=[]
            print_list = []
            if table is not None:
                for tr in table.findAll('tr'):
                    col = 0
                    row=[]
                    for td in tr.findAll('td'):
                        col+=1
                        # if col in (1,2,6,8,10,14):
                        if col in (1, 2, 8, 12, 18):
                            if col==14 and td.attrs.get('style') is not None and td.attrs['style'].find('font-style:italic')>=0:
                                row.append('0.00%')
                            else:
                                row.append(td.getText().strip())
                    cnt=cursor.execute("select code from finance.bond_all where code='%s'"%row[0])
                    #sh or sz
                    loc=None
                    r=requests.get("http://hq.sinajs.cn/list=sh%s"%row[0])
                    if '=""' not in BeautifulSoup(r.content,"html.parser").getText():
                        loc='sh'
                    else:
                        r = requests.get("http://hq.sinajs.cn/list=sz%s" % row[0])
                        if '=""' not in BeautifulSoup(r.content, "html.parser").getText():
                            loc='sz'


                    if not cnt and len(row)==5:
                        if row[2].find('/')>0: #两个期限，分成两条记录
                            duration=row[2].split('/')
                            diff = int(round(float(duration[1]) - float(duration[0]),0))
                            xdate=str(int(row[4][:4])-diff)+row[4][4:]
                            if loc is None:
                                cursor.execute("insert finance.bond_all(code,name,coupon,mat_xdate,mat_ydate,is_review) values('%s','%s',%s,'%s','%s','n')"%(row[0],row[1],row[3],xdate,row[4]))
                            else:
                                cursor.execute("insert finance.bond_all(code,loc,name,coupon,mat_xdate,mat_ydate,is_review) values('%s','%s','%s',%s,'%s','%s','n')" % (
                                    row[0], loc, row[1], row[3], xdate, row[4]))
                            conn.commit()
                        else:
                            if loc is None:
                                cursor.execute(
                                    "insert finance.bond_all(code,name,coupon,mat_xdate,mat_ydate,is_review) values('%s','%s',%s,'%s',null,'n')" % (
                                        row[0], row[1], row[3], row[4]))
                            else:
                                cursor.execute(
                                "insert finance.bond_all(code,loc,name,coupon,mat_xdate,mat_ydate,is_review) values('%s','%s','%s',%s,'%s',null,'n')" % (
                                row[0],loc, row[1], row[3], row[4]))
                            conn.commit()

            #print(soup)
        except Exception as e:
            print(repr(e))

    except ImportError:
        print('No module named selenium. 请安装selenium模块')
