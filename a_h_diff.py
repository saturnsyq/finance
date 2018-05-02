#!/usr/bin/python
# coding=utf-8

import urllib,urllib2
import json
import pandas as pd
import re

stock_list =[['600016','002142']]
bgdate='2017-01-01'
eddate='2018-03-30'

def get_dq(code='00005',mkt='AUTO', bgdate='2017-03-01',eddate='2017-04-30',fq=None):

    if mkt=='AUTO':
        if re.search('^\d{5}$',code):
            mkt='hk'
        elif re.search('^6\d{5}$',code):
            mkt='sh'
        elif re.search('^0|3\d{5}$',code):
            mkt='sz'
    code_par= mkt +code
    print('get dq of %s.%s[from:%s, to:%s]' % (code, mkt, bgdate,eddate))
    if fq==None:
        url= 'http://web.ifzq.gtimg.cn/appstock/app/kline/kline?_var=kline_day&param=%s,day,%s,%s,640,' % (code_par, bgdate,eddate)
        dataname='day'
    else:
        assert fq in ['qfq','hfq']
        url= 'http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_day&param=%s,day,%s,%s,640,%s' % (code_par, bgdate,eddate, fq)
        dataname= fq+ 'day'
    cn=urllib.urlopen(url)
    raw='\n'.join(cn.readlines())
    js= re.search('(?<=kline_day=).*$', raw).group()
    jsparsed=json.loads(js)
    return jsparsed['data'][code_par][dataname]
    # dq=pd.DataFrame(jsparsed['data'][code_par][dataname])
    # if dq.shape[1]==6:
    #     dq.columns=  ['date','o','c','h','l','v']
    # elif dq.shape[1]==7:
    #     dq.columns=  ['date','o','c','h','l','v','qy']
    # return dq

if __name__=='__main__':
    for sa,sh in stock_list:
        data_a={ row[0]:row[2] for row in get_dq(sa,bgdate=bgdate,eddate=eddate,fq='qfq') }
        data_h={ row[0]:row[2] for row in get_dq(sh,bgdate=bgdate,eddate=eddate,fq='qfq') }
    result={}
    for dd in data_a:
        if data_h.get(dd) is not None:
            result[dd]="a:%s,b:%s,div:%s"%(data_a[dd],data_h[dd],round(float(data_a[dd])/float(data_h[dd]),3))

    for key in sorted(result.keys()):
        print("%s:%s"%(key,result[key]))
        # print(result[key])


