#!/usr/bin/python3
# coding=utf-8

import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.keys import Keys
import time
import tamCommonLib
import credentials
import math

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

mail_list = ['yongqis@amazon.com']

if __name__ == '__main__':

    conn = tamCommonLib.getMysqlConnect()
    cursor = conn.cursor()
    send_list = {}
    while True:
        cursor.execute("select concat(loc,code) as full_code,code,coupon,mat_xdate,mat_ydate,monitor_ytm,name FROM finance.bond_all where is_monitor='y' and loc is not null")
        all_bond={}
        bond_str=''
        for row in cursor.fetchall():
            all_bond[row[0]]=row
            bond_str=bond_str+row[0]+","
        cur=datetime.datetime.now()
        bond_str = bond_str[:-1]

        if len(bond_str)>0:
            r = requests.get("http://hq.sinajs.cn/list=%s"%bond_str)
            ret_list=r.text.split(';\n')
            meet_list = []
            for each in ret_list:
                temp=re.findall(r'^var hq_str_(\w+)="(.*)"$',each)
                if len(temp)==0 or len(temp[0][1])==0: continue
                #s1_v,s1_p,s2_v,s2_p,s3_v,s3_p,s4_v,s4_p,s5_v,s5_p=temp[0][1].split(',')[20:30]
                sells=temp[0][1].split(',')[20:30]
                need_detect=False
                for i in range(5):
                    if float(sells[2*i])>10:
                        s1_v=sells[2*i]
                        s1_p=sells[2*i+1]
                        need_detect=True
                        break
                if not need_detect: continue
                #calculate xdate
                row=all_bond[temp[0][0]]
                mat=row[3]
                dcf=0
                if cur.date()>=datetime.date(cur.year,mat.month,mat.day):
                    next_coupon_day=datetime.date(cur.year+1,mat.month,mat.day)
                    coupon_days = (cur.date() - datetime.date(cur.year,mat.month,mat.day)).days + 1
                else:
                    next_coupon_day = datetime.date(cur.year, mat.month, mat.day)
                    coupon_days = (cur.date() - datetime.date(cur.year-1, mat.month, mat.day)).days + 1
                if (mat - cur.date()).days < 365:
                    dcf = (100 + float(row[2])) /( 1 + float(row[5]) * round((next_coupon_day-cur.date()).days/365,4) )
                else:
                    while next_coupon_day<=mat:
                        span=round((next_coupon_day-cur.date()).days/365,4)
                        if next_coupon_day==mat:
                            dcf += (100 + float(row[2])) / math.pow(1 + float(row[5]) * 0.01, span)
                            break
                        else:
                            dcf+=float(row[2])/math.pow(1+float(row[5])*0.01,span)
                            next_coupon_day=datetime.date(next_coupon_day.year+1,next_coupon_day.month,next_coupon_day.day)
                full_price=float(s1_p)+float(row[2])*coupon_days/365
                if full_price<dcf and send_list.get(row[0]) is None:
                    code_link = 'https://www.jisilu.cn/data/bond/detail/%s' % row[1]
                    html_code = '<a href="%s">%s</a>' % (code_link, row[1])
                    meet_list.append([html_code, row[6], s1_p, s1_v, row[5],mat,round(span,2)])
                    send_list[row[0]]=1
                #calculate ydate
            if len(meet_list)>0:
                meet_list.insert(0, ['code', 'name','price', 'vol', 'ytm_bar','mature_date','remain_years'])
                body = tamCommonLib.table_html_with_rn(meet_list, '')
                send_mail('yongqis@amazon.com', mail_list, '[AAA_bonds] buy list', body, [], 'html')

            if datetime.datetime.now().hour>15:
                break
            else:
                print("sleep for 10 seconds at %s......" % str(datetime.datetime.now()))
                time.sleep(10)
                print("wake up to run again at %s......" % str(datetime.datetime.now()))





