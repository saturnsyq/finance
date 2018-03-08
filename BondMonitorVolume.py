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
        bond_list=get_exclude_list()

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
                        if col in (1, 2, 6, 9, 10, 14):
                            if col==14 and td.attrs.get('style') is not None and td.attrs['style'].find('font-style:italic')>=0:
                                row.append('0.00%')
                            else:
                                row.append(td.getText().strip())
                    if len(row)==6:
                        if row[3].find('/')>0: #两个期限，分成两条记录
                            duration=row[3].split('/')
                            ytm=row[4].split('/')
                            data.append([row[0],row[1],row[2],duration[0],ytm[0],row[5]])
                            data.append([row[0],row[1],row[2],duration[1],ytm[1],row[5]])
                        else:
                            data.append(row)
                for irow in data:
                    code_link = 'https://www.jisilu.cn/data/bond/detail/%s' % irow[0]
                    html_code = '<a href="%s">%s</a>' % (code_link, irow[0])
                    if irow[5][-1]=='%':
                        if irow[4][-1]=='%':
                            ytm=float(irow[4][:-1])
                        else:
                            ytm = float(irow[4])
                        bs = 0
                        if float(irow[5][:-1])>0.001:
                            bs =0.95 * 1/(100/(0.88*float(irow[5][:-1]))-1)
                        total = ytm + (ytm - repo_rate) * bs
                        if total >= 10.5 and float(irow[3])<2:
                            # vol=get_sell1_volume(driver,code_link)
                            # if vol is not None and vol>10:
                            #     meet_list.append([html_code,irow[1],irow[3],round(ytm,2),round(total,2)])
                            #     print_list.append([irow[0], irow[1], irow[3], round(ytm, 2), round(total, 2)])
                            retries =5
                            driver.implicitly_wait(3)  # 等待3秒
                            while retries>0:
                                try:
                                    driver.get(code_link)
                                    time.sleep(7 - retries)
                                    #driver.implicitly_wait(2)  # 等待3秒
                                    soup = BeautifulSoup(driver.page_source, "html.parser")
                                    table = soup.find('table', id='flex0')
                                    repo_info = table.find('thead').find('table').find_all('tr')[2].find_all('td')[1]
                                    repo = float(re.findall(r'^回购资金利用率：([\d\.]+)%?$', repo_info.getText().strip())[0])
                                    # adjust the italic font repo to 0
                                    span = repo_info.find('span')
                                    if span is not None and span.attrs.get('style') is not None and span.attrs['style'].find('font-style:italic') >= 0:
                                        repo = 0
                                    tbody = table.find_all('tbody')[1]
                                    volume = None

                                    for sell in ('sell1', 'sell2', 'sell3', 'sell4', 'sell5'):
                                        tr = tbody.find('tr', id=sell)
                                        if tr is not None:
                                            col = 0
                                            price, volume, dur1, ytm1, dur2, ytm2 = 0, 0, 0, 0, 0, 0
                                            for td in tr.findAll('td'):
                                                col += 1
                                                try:
                                                    if col == 2: price = float(td.getText().strip())
                                                    if col == 3: volume = round(float(td.getText().strip()), 1)
                                                    if col == 5: ytm1 = float(td.getText().strip())
                                                    if col == 7: dur1 = float(td.getText().strip())
                                                    if col == 10: ytm2 = float(td.getText().strip())
                                                    if col == 12: dur2 = float(td.getText().strip())
                                                except:
                                                    do_nothing=1
                                            act_ytm = act_ytm38 = act_ytm40 = round(ytm1, 2)
                                            if repo > 0:
                                                act_ytm = round(ytm1 + (ytm1 - repo_rate) * 0.95 * 1 / (100 / (0.88 * repo) - 1), 2)
                                                act_ytm38 = round(ytm1 + (ytm1 - 3.8) * 0.95 * 1 / (100 / (0.88 * repo) - 1), 2)
                                                act_ytm40 = round(ytm1 + (ytm1 - 4.0) * 0.95 * 1 / (100 / (0.88 * repo) - 1), 2)
                                            if act_ytm > bar and volume > vol and irow[0] not in bond_list:
                                                meet_list.append([html_code, irow[1], volume, dur1, ytm1, act_ytm,act_ytm38,act_ytm40])
                                                #meet_list.append([html_code, irow[1], irow[3], round(ytm, 2), round(total, 2)])
                                                break
                                            act_ytm = act_ytm38 = act_ytm40 = round(ytm2, 2)
                                            if repo > 0:
                                                act_ytm = round(ytm2 + (ytm2 - repo_rate) * 0.95 * 1 / (100 / (0.88 * repo) - 1), 2)
                                                act_ytm38 = round(ytm2 + (ytm2 - 3.8) * 0.95 * 1 / (100 / (0.88 * repo) - 1), 2)
                                                act_ytm40 = round(ytm2 + (ytm2 - 4.0) * 0.95 * 1 / (100 / (0.88 * repo) - 1), 2)
                                            if act_ytm > bar and volume > vol and irow[0] not in bond_list:
                                                meet_list.append([html_code, irow[1], volume, dur2, ytm2, act_ytm,act_ytm38,act_ytm40])
                                                break
                                    break
                                except Exception as e:
                                    # do nothing, just skipping this one
                                    logging.warning("error %s happened, retry %s, left retries:%s" % (repr(e),irow[0],retries))
                                    retries -=1

                            #print('%s,%s,%s  - total=%s' % (irow[0],irow[1],irow[3],round(total,2)))
                if display_in_mail==1:
                    meet_list.sort(key=lambda bond:bond[5],reverse=True)
                    meet_list.insert(0,['code','name','vol','duration','ytm','actual_ytm36','actual_ytm38','actual_ytm40'])
                    body = tamCommonLib.table_html_with_rn(meet_list, '')
                    send_mail('yongqis@amazon.com', mail_list, 'Bond Monitor List', body, [], 'html')
                else:
                    for row in print_list:
                        print('%s,%s,dur=%s,ytm=%s, act_ytm=%s' % (row[0],row[1],row[2],row[3],row[4]) )

            #print(soup)
        except Exception as e:
            print(repr(e))

    except ImportError:
        print('No module named selenium. 请安装selenium模块')
