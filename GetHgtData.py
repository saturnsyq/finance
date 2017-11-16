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
    raw_url='http://www.hkexnews.hk/sdw/search/mutualmarket_c.aspx?t='
    try:
        conn = tamCommonLib.getMysqlConnect()
        cursor= conn.cursor()
        for mm in ('sh','sz'):
            url = raw_url + mm
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
        #get the statistics data
        cursor.execute('drop table if exists temp.tt_ss')
        sql='''
        create table temp.tt_ss as
Select m.*,(@rowNum:=@rowNum+1) as row_num
From ( select distinct ss_date from finance.hk_mainland_hist ) m,
(Select (@rowNum :=-1) ) b
Order by m.ss_date Desc
       '''
        cursor.execute(sql)
        cursor.execute('truncate table finance.hk_mainland_stat')
        conn.commit()
        sql='''
        insert finance.hk_mainland_stat
        select
d0.code,
d0.name,
d0.volume,
d0.percent,
d0.volume - d1.volume net1_income,
d0.volume - d2.volume net2_income,
d0.volume - d3.volume net3_income,
d0.volume - d4.volume net4_income,
d0.volume - d5.volume net5_income,
d0.volume - d6.volume net6_income,
d0.volume - d7.volume net7_income,
d0.volume - d10.volume net10_income,
d0.volume - d14.volume net14_income,
d0.volume - d28.volume net28_income
from ( select code,name,volume,percent from finance.hk_mainland_hist where ss_date=(select ss_date from temp.tt_ss where row_num=0) ) d0
left join ( select code,volume from finance.hk_mainland_hist where ss_date=(select ss_date from temp.tt_ss where row_num=1) ) d1 on d0.code=d1.code
left join ( select code,volume from finance.hk_mainland_hist where ss_date=(select ss_date from temp.tt_ss where row_num=2) ) d2 on d0.code=d2.code
left join ( select code,volume from finance.hk_mainland_hist where ss_date=(select ss_date from temp.tt_ss where row_num=3) ) d3 on d0.code=d3.code
left join ( select code,volume from finance.hk_mainland_hist where ss_date=(select ss_date from temp.tt_ss where row_num=4) ) d4 on d0.code=d4.code
left join ( select code,volume from finance.hk_mainland_hist where ss_date=(select ss_date from temp.tt_ss where row_num=5) ) d5 on d0.code=d5.code
left join ( select code,volume from finance.hk_mainland_hist where ss_date=(select ss_date from temp.tt_ss where row_num=6) ) d6 on d0.code=d6.code
left join ( select code,volume from finance.hk_mainland_hist where ss_date=(select ss_date from temp.tt_ss where row_num=7) ) d7 on d0.code=d7.code
left join ( select code,volume from finance.hk_mainland_hist where ss_date=(select ss_date from temp.tt_ss where row_num=10) ) d10 on d0.code=d10.code
left join ( select code,volume from finance.hk_mainland_hist where ss_date=(select ss_date from temp.tt_ss where row_num=14) ) d14 on d0.code=d14.code
left join ( select code,volume from finance.hk_mainland_hist where ss_date=(select ss_date from temp.tt_ss where row_num=28) ) d28 on d0.code=d28.code
        '''
        cursor.execute(sql)
        conn.commit()
        conn.close()

    except Exception as e:
        print(repr(e))
