#!/usr/bin/python3
# coding=utf-8

import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.keys import Keys
import time
import tamCommonLib
import credentials
import re

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
if __name__ == '__main__':
    url='http://www.hkexnews.hk/sdw/search/mutualmarket_c.aspx?t=sh'
    try:
        conn = tamCommonLib.getMysqlConnect()
        cursor= conn.cursor()
        result = requests.get(url)
        soup = BeautifulSoup(result.content,"lxml")
        area = soup.find('div',id='pnlResult')
        fields = re.findall(r'(\d{2})/(\d{2})/(\d{4})',area.find('div').getText().strip())[0]
        ss_date = "%s-%s-%s" % (fields[2],fields[1],fields[0])
        data = []
        for row in area.find_all('tr',attrs={'class':re.compile('row(0|1)')}):
            each = []
            for td in row.find_all('td'):
                each.append(td.getText().strip())
            data.append(each)
            cursor.execute("delete from finance.hk_mainland_hist where ss_date='%s' and code='%s'" % (ss_date,each[0]))
            vol = each[2].replace(',','')
            percent = round(float(re.findall(r'^([0-9]*\.?[0-9]+|[0-9]+\.?[0-9]*)%$',each[3])[0])/100,4)
            cursor.execute("insert finance.hk_mainland_hist(ss_date,code,name,volume,percent) values('%s','%s','%s',%s,%s)" % (ss_date, each[0],each[1],vol,str(percent)))
            conn.commit()
        conn.close()

    except Exception as e:
        print(repr(e))
