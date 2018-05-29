#!/usr/bin/python3
# coding=utf-8

import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.keys import Keys
import time
import tamCommonLib
import credentials
import re
import sys
import datetime
import xlrd
import os

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

local_file='temp.xls'
if __name__ == '__main__':
    mode=1
    if len(sys.argv)==2:
        mode=2
        start=datetime.datetime.strptime(sys.argv[1],'%Y%m%d')
    if len(sys.argv)==3:
        mode=3
        start=datetime.datetime.strptime(sys.argv[1],'%Y%m%d')
        end = datetime.datetime.strptime(sys.argv[2], '%Y%m%d')
    conn = tamCommonLib.getMysqlConnect()
    cursor = conn.cursor()
    pages=20
    cnt=1
    while cnt<=pages:
        if cnt==1:
            raw_url="http://www.chinaclear.cn/zdjs/xbzzsl/center_bzzsl.shtml"
        else:
            raw_url = "http://www.chinaclear.cn/zdjs/xbzzsl/center_bzzsl_%s.shtml"%cnt
        cnt+=1
        r=requests.get(raw_url)
        # html = r.content.decode('utf8', "ignore")
        soup = BeautifulSoup(r.content, 'html.parser', from_encoding='utf-8')
        lis = soup.select("div.pageTabContent > ul > li")
        matched=0
        for li in lis:
            file_link=li.select_one("> a").attrs['href'].strip()
            if u'上海' in li.select_one("> a").getText().strip():
                market='sh'
                shift=0
            else:
                market='sz'
                shift=1
            if not 'chinaclear' in file_link:
                file_link='http://www.chinaclear.cn'+file_link
            file_date=datetime.datetime.strptime(li.select_one("> span").getText().strip(),'%Y-%m-%d')
            if mode==1 or (mode==2 and file_data.date()==start.date()) or (mode==3 and file_date>=start and file_date<=end):
                matched+=1
                print("Processing " + file_date.strftime('%Y-%m-%d') + ' ' + file_link)
                try:
                    r = requests.get(file_link)
                    with open(local_file, "wb") as code:
                        code.write(r.content)
                    data = xlrd.open_workbook(local_file)
                    table = data.sheet_by_index(0)
                    nrows = table.nrows
                    ncols = table.ncols
                    can_retrieve=False
                    for i in range(nrows):
                        if can_retrieve==False:
                            if market=='sz' and str(table.cell(i,1).value).lower().startswith(u'债券代码'): can_retrieve=True
                            if market=='sh' and '债券ETF代码' in str(table.cell(i,0).value).upper(): can_retrieve = True
                            continue
                        if len(str(table.cell(i,0+shift).value))>2:
                            code=str(table.cell(i,0+shift).value)
                            rate=str(table.cell(i,2+shift).value)
                            start_d=str(table.cell(i,3+shift).value)
                            if start_d[-2:]=='.0': start_d=start_d[:4]+'-'+start_d[4:6]+'-'+start_d[6:8]
                            end_d = str(table.cell(i, 4 + shift).value)
                            if end_d[-2:] == '.0': end_d = end_d[:4] + '-' + end_d[4:6] + '-' + end_d[6:8]
                            print("%s,%s,%s,%s"%(code,rate,start_d,end_d))
                            cursor.execute("delete from finance.dis_rate_hist where code='%s' and start='%s'"%(code,start_d))
                            cursor.execute("insert finance.dis_rate_hist values ('%s',%s,'%s','%s')" % (code,rate, start_d,end_d))
                            conn.commit()
                except Exception as e:
                    print("error with %s" % (repr(e)))
            if mode in (1, 2) and matched == 2: break
        if mode in (1,2) and matched==2:
            break
    if os.path.exists(local_file):
        os.remove(local_file)
