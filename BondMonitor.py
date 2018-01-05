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

# url='https://www.jisilu.cn/data/bond/?do_search=true&sort_column=&sort_order=&forall=0&treasury=1&from_rating=1&from_issuer_rating=1&from_year_left=0&from_repo=0.56&from_ytm=5.3&from_volume=0&from_market=&y1=&y2=&to_rating=99&to_issuer_rating=99&to_year_left=2&to_repo=2&to_ytm=8&to_volume='
url='https://www.jisilu.cn/data/bond/'
try:
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
                    if col in (1,2,6,8,10,14):
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
                    total = ytm + (ytm - 3.6) * bs
                    if total >= 10.5 and float(irow[3])<2:
                        meet_list.append([html_code,irow[1],irow[3],round(ytm,2),round(total,2)])
                        print_list.append([irow[0], irow[1], irow[3], round(ytm, 2), round(total, 2)])
                        #print('%s,%s,%s  - total=%s' % (irow[0],irow[1],irow[3],round(total,2)))
            if display_in_mail==1:
                meet_list.sort(key=lambda bond:bond[4],reverse=True)
                meet_list.insert(0,['code','name','duration','ytm','actual_ytm'])
                body = tamCommonLib.table_html_with_rn(meet_list, '')
                send_mail('cn-tam-auto@amazon.com', mail_list, 'Bond Monitor List', body, [], 'html')
            else:
                for row in print_list:
                    print('%s,%s,dur=%s,ytm=%s, act_ytm=%s' % (row[0],row[1],row[2],row[3],row[4]) )

        #print(soup)
    except Exception as e:
        print(repr(e))

except ImportError:
    print('No module named selenium. 请安装selenium模块')
