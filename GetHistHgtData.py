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

page_wait = 3      #wait for 3 seconds to load pages content

if __name__ == '__main__':
    raw_url='http://www.hkexnews.hk/sdw/search/mutualmarket_c.aspx?t='
    try:
        from selenium import webdriver
        import ssl
        from selenium.webdriver.common.keys import Keys
        import datetime
        import time
        from selenium.webdriver.support.select import Select

        ssl._create_default_https_context = ssl._create_unverified_context  # 取消证书认证
        driver = webdriver.PhantomJS(executable_path='/home/local/ANT/yongqis/finance/phantomjs')

        conn = tamCommonLib.getMysqlConnect()
        cursor= conn.cursor()
        now=datetime.datetime.now()
        for mm in ('sh','sz'):
            url = raw_url + mm
            driver.get(url)
            time.sleep(page_wait)
            for dd in range(365):
                pre_day = now + datetime.timedelta(days=0-dd)
                if (pre_day - datetime.datetime.strptime('2017-03-18 00:00:00', '%Y-%m-%d %H:%M:%S')).days <=0: break
                sel = driver.find_element_by_xpath("//select[@id='ddlShareholdingDay']")
                temp=str(pre_day.day)
                if pre_day.day<10: temp = '0'+ temp
                Select(sel).select_by_value(temp)
                sel = driver.find_element_by_xpath("//select[@id='ddlShareholdingMonth']")
                temp = str(pre_day.month)
                if pre_day.month < 10: temp = '0' + temp
                Select(sel).select_by_value(temp)
                sel = driver.find_element_by_xpath("//select[@id='ddlShareholdingYear']")
                temp = str(pre_day.year)
                Select(sel).select_by_value(temp)
                driver.find_element_by_xpath("//input[@id='btnSearch']").click()
                time.sleep(page_wait)

                soup = BeautifulSoup(driver.page_source,"lxml")
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
                    cursor.execute("insert finance.hk_mainland_hist(ss_date,code,name,volume,percent) values('%s','%s','%s',%s,%s)" % (ss_date, each[0],each[1][:10],vol,str(percent)))
                    conn.commit()
        conn.close()

    except Exception as e:
        print(repr(e))
