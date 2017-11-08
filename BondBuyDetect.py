#!/usr/bin/python3
# coding=utf-8

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

import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.keys import Keys
import time
import re
import tamCommonLib
import credentials

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

# url='https://www.jisilu.cn/data/bond/?do_search=true&sort_column=&sort_order=&forall=0&treasury=1&from_rating=1&from_issuer_rating=1&from_year_left=0&from_repo=0.56&from_ytm=5.3&from_volume=0&from_market=&y1=&y2=&to_rating=99&to_issuer_rating=99&to_year_left=2&to_repo=2&to_ytm=8&to_volume='
url='https://www.jisilu.cn/data/bond/detail/%s'
detect_list = [
('136515',11,1),('124135',11,1),('136259',11,1),('122846',11,1),('136447',12,1),('136547',11,1),('136654',10.5,1),('136654',10.5,1),('136167',13,1),
('122231',11,1),('112279',11,1),('122099',11,1),('122814',11,1),('112418',12,1),('136081',11,1),('136206',11.5,1),('112373',12.5,1),('136033',11,1),
('122516',11,1),('122219',12,1),('136210',12,1),('112340',12,1),('112320',12,1),('112452',12,1),('112048',12,1),('112394',12,1),('122476',14,1),('136188',12,1)
]
repo_rate = 3.6    #回购利率，即资金成本
page_wait = 4      #wait for 3 seconds to load pages content
try:
    from selenium import webdriver
    import ssl

    ssl._create_default_https_context = ssl._create_unverified_context  # 取消证书认证
    try:
        driver = webdriver.PhantomJS(executable_path='/home/local/ANT/yongqis/finance/phantomjs')
        driver.get('https://www.jisilu.cn/login/')
        time.sleep(page_wait)
        elem = driver.find_element_by_id('aw-login-user-name')
        if elem is not None:
            driver.find_element_by_id('aw-login-user-name').send_keys(Keys.TAB)  # 定位并输入用户名
            driver.find_element_by_id('aw-login-user-password').send_keys(Keys.TAB)  # 定位并输入用户名
            driver.find_element_by_id('aw-login-user-name').send_keys(credentials.jisilu_user)   #定位并输入用户名
            driver.find_element_by_id('aw-login-user-password').send_keys(credentials.jisilu_password)  # 定位并输入用户名
            driver.find_element_by_id('login_submit').click()
            time.sleep(page_wait)

        meet_list =[['code','volume(w)','duration','ytm','actual_ytm']]
        for code, bar, vol in detect_list:
            html_code='<a href="%s">%s</a>' % (url%code,code)
            driver.get(url%code)
            time.sleep(page_wait)
            driver.implicitly_wait(page_wait)  # 等待3秒
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(driver.page_source, "html.parser")
            table = soup.find('table', id='flex0')
            repo_info=table.find('thead').find('table').find_all('tr')[2].find_all('td')[1]
            repo=float(re.findall(r'^回购资金利用率：([\d\.]+)%?$',repo_info.getText().strip())[0])
            #adjust the italic font repo to 0
            span=repo_info.find('span')
            if span is not None and span.attrs.get('style') is not None and span.attrs['style'].find('font-style:italic')>=0:
                repo = 0
            tbody = table.find_all('tbody')[1]
            for sell in ('sell1','sell2','sell3','sell4','sell5'):
                tr=tbody.find('tr',id=sell)
                if tr is not None:
                    col = 0
                    price, volume, dur1, ytm1, dur2, ytm2 = 0,0,0,0,0,0
                    for td in tr.findAll('td'):
                        col += 1
                        if col == 2: price  = float(td.getText().strip())
                        if col == 3: volume = round(float(td.getText().strip()),1)
                        if col == 5: ytm1 = float(td.getText().strip())
                        if col == 7: dur1 = float(td.getText().strip())
                        if col == 10: ytm2 = float(td.getText().strip())
                        if col == 12: dur2 = float(td.getText().strip())
                    act_ytm = round(ytm1,2)
                    if repo>0:
                        act_ytm = round(ytm1 + (ytm1 - repo_rate) * 0.95 * 1/(100/(0.88*repo)-1),2)
                    if act_ytm>bar and volume>vol:
                        meet_list.append([html_code,volume,dur1,ytm1,act_ytm])
                        break
                    act_ytm = round(ytm2,2)
                    if repo > 0:
                        act_ytm = round(ytm2 + (ytm2 - repo_rate) * 0.95 * 1 / (100 / (0.88 * repo) - 1),2)
                    if act_ytm > bar and volume > vol:
                        meet_list.append([html_code, volume, dur2, ytm2, act_ytm])
                        break
        #send warning mail
        if len(meet_list)>1:
            body = tamCommonLib.table_html(meet_list, '')
            send_mail('yongqis@amazon.com', ['yongqis@amazon.com'], 'Bond Detection List', body, [],'html')
    except:
        print ('请安装phantomjs')

except ImportError:
    print('No module named selenium. 请安装selenium模块')
