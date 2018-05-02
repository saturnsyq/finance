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
import random
import photoRecognize
import json
import urllib
from urllib import parse


##logging configuration
logging.basicConfig(level=logging.INFO,
                format='%(asctime)s %(filename)s[line:%(lineno)3d] %(levelname)s %(message)s',
                datefmt='%Y-%m-%d %a %H:%M:%S',
                filename='/home/local/ANT/yongqis/BondMonitorVolume.%s.log'%datetime.datetime.now().strftime('%Y-%m-%d.%H%M%S'),
                filemode='w')


mail_list = ['yongqis@amazon.com']
display_in_mail = 1
# headers = { "User-agent":'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36', "Accept":"application/json, text/javascript, */*; q=0.01",'Accept-Encoding': 'gzip, deflate, br','Accept-Language': 'en-US,en;q=0.9'}
headers = {
"Host":"www.jisilu.cn",
"Connection":"keep-alive",
"Cache-Control":"max-age=0",
"Upgrade-Insecure-Requests":"1",
"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36",
"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
"Referer":"https://www.jisilu.cn/",
"Accept-Encoding":"gzip, deflate, br",
"Accept-Language":"en-US,en;q=0.9"
}


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

def get_exclude_list():
    try:
        conn = tamCommonLib.getMysqlConnect()
        cursor = conn.cursor()
        cursor.execute("select code from finance.bond_exclude_list")
        bond_list = [code for code, in cursor.fetchall()]
    except Exception as e:
        bond_list = list()
    return bond_list


def to_float(value):
    try:
        return float(value)
    except:
        return 0

# url='https://www.jisilu.cn/data/bond/?do_search=true&sort_column=&sort_order=&forall=0&treasury=1&from_rating=1&from_issuer_rating=1&from_year_left=0&from_repo=0.56&from_ytm=5.3&from_volume=0&from_market=&y1=&y2=&to_rating=99&to_issuer_rating=99&to_year_left=2&to_repo=2&to_ytm=8&to_volume='
url='https://www.jisilu.cn/data/bond/'
bond_url='https://www.jisilu.cn/data/bond/detail/%s'
repo_rate=3.6
bar=11   #ytm bar
vol=10
data = {'return_url': 'https://www.jisilu.cn/data/bond/',
        'user_name': 'saturn99',
        'password': '64445169',
        'net_auto_login':'1',
        '_post_type':'ajax'
        }
verify_code=True
if __name__ == '__main__':
    try:
        bond_list=get_exclude_list()
        session = requests.Session()
        try:
            fail_code=int(random.random()*10000)
            if fail_code<1000: fail_code=1000+fail_code
            fail_str="fail152457061%s"%fail_code
            session.get('https://www.jisilu.cn/account/login/%s'%fail_str, headers=headers)
            retries = 5
            while retries>0:
                r = session.get("https://www.jisilu.cn/account/captcha/%s"%(int(random.random()*10000)), headers=headers)
                chaojiying = photoRecognize.Chaojiying_Client('saturn99', '64445169', '895197')
                result=chaojiying.PostPic(r.content, 1006)
                if (result['err_no']==0 or result['err_str']=='OK') and len(result['pic_str'])==6:
                    r = session.get("https://www.jisilu.cn/account/ajax/check_verify_code/code-%s" % (result['pic_str']),headers=headers)
                    if json.loads(r.content.decode('utf8', "ignore"))['errno'] != 1:
                        break
                retries-=1
                time.sleep(2*(5-retries))
            if retries==0:
                print("cannot recongize the photos for several times. exist now.")
                exit()
            data['seccode_verify']=result['pic_str']
            headers['Content-Type']='application/x-www-form-urlencoded; charset=UTF-8'
            r = session.post('https://www.jisilu.cn/account/ajax/login_process/%s'%fail_str, data=parse.urlencode(data),headers=headers)
            if json.loads(r.content.decode('utf8', "ignore"))['errno'] != 1:
                print("cannot login. exist now.")
                exit()
            r=session.get(url,headers=headers)
            html = r.content.decode('utf8', "ignore")

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
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
                done_list={}
                for irow in data:
                    if done_list.get(irow[0]) is not None: continue
                    done_list[irow[0]]=1
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
                        if total >= 10.5 and float(irow[3])<5:
                            r=session.get(code_link,headers=headers)
                            html = r.content.decode('utf8', "ignore")
                            soup = BeautifulSoup(html, "html.parser")
                            table = soup.find('table', id='flex0')
                            span =soup.select_one("#exbondtitle > table > tr:nth-of-type(3) > td:nth-of-type(2) > span")
                            repo = float(re.findall(r'^([\d\.]+)%?$', span.getText().strip())[0])
                            # adjust the italic font repo to 0
                            if span is not None and span.attrs.get('style') is not None and span.attrs['style'].find('font-style:italic') >= 0:
                                repo = 0
                            r=session.get("https://www.jisilu.cn/data/bond_ajax/bond_yield/?bond_id=%s"%irow[0],headers=headers)
                            sell_rows = json.loads(r.content.decode('utf8', "ignore"))['rows']

                            for sell in ('sell1', 'sell2', 'sell3', 'sell4', 'sell5'):
                                # for each_row in sell_rows:
                                rows = [each_row for each_row in sell_rows if each_row['id']==sell]
                                if len(rows)==0: continue
                                each_row = rows[0]
                                col = 0
                                price, volume, dur1, ytm1, dur2, ytm2 = 0, 0, 0, 0, 0, 0
                                price = to_float(each_row['cell']['price'])
                                volume = round(to_float(each_row['cell']['volume']),1)
                                dur1 = to_float(each_row['cell']['md_x'])
                                dur2 = to_float(each_row['cell']['md_y'])
                                ytm1 = to_float(each_row['cell']['ytm_x'])
                                ytm2 = to_float(each_row['cell']['ytm_y'])

                                act_ytm = act_ytm38 = act_ytm40 = round(ytm1, 2)
                                if repo > 0:
                                    act_ytm = round(ytm1 + (ytm1 - repo_rate) * 0.95 * 1 / (100 / (0.88 * repo) - 1), 2)
                                    act_ytm38 = round(ytm1 + (ytm1 - 3.8) * 0.95 * 1 / (100 / (0.88 * repo) - 1), 2)
                                    act_ytm40 = round(ytm1 + (ytm1 - 4.0) * 0.95 * 1 / (100 / (0.88 * repo) - 1), 2)
                                if act_ytm > bar and volume > vol and irow[0] not in bond_list:
                                    meet_list.append([html_code, irow[1], volume, dur1, ytm1, act_ytm,act_ytm38,act_ytm40])
                                    break
                                act_ytm = act_ytm38 = act_ytm40 = round(ytm2, 2)
                                if repo > 0:
                                    act_ytm = round(ytm2 + (ytm2 - repo_rate) * 0.95 * 1 / (100 / (0.88 * repo) - 1), 2)
                                    act_ytm38 = round(ytm2 + (ytm2 - 3.8) * 0.95 * 1 / (100 / (0.88 * repo) - 1), 2)
                                    act_ytm40 = round(ytm2 + (ytm2 - 4.0) * 0.95 * 1 / (100 / (0.88 * repo) - 1), 2)
                                if act_ytm > bar and volume > vol and irow[0] not in bond_list:
                                    meet_list.append([html_code, irow[1], volume, dur2, ytm2, act_ytm,act_ytm38,act_ytm40])
                                    break
                                #     break
                                # except Exception as e:
                                #     # do nothing, just skipping this one
                                #     logging.warning("error %s happened, retry %s, left retries:%s" % (repr(e),irow[0],retries))
                                #     retries -=1

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
