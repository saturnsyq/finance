import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.keys import Keys
import time

# url='https://www.jisilu.cn/data/bond/?do_search=true&sort_column=&sort_order=&forall=0&treasury=1&from_rating=1&from_issuer_rating=1&from_year_left=0&from_repo=0.56&from_ytm=5.3&from_volume=0&from_market=&y1=&y2=&to_rating=99&to_issuer_rating=99&to_year_left=2&to_repo=2&to_ytm=8&to_volume='
url='https://www.jisilu.cn/data/bond/'
try:
    from selenium import webdriver
    import ssl

    ssl._create_default_https_context = ssl._create_unverified_context  # 取消证书认证
    try:
        driver = webdriver.PhantomJS()
        driver.get('https://www.jisilu.cn/login/')
        elem = driver.find_element_by_id('aw-login-user-name')
        if elem is not None:
            driver.find_element_by_id('aw-login-user-name').send_keys(Keys.TAB)  # 定位并输入用户名
            driver.find_element_by_id('aw-login-user-password').send_keys(Keys.TAB)  # 定位并输入用户名
            driver.find_element_by_id('aw-login-user-name').send_keys('***')   #定位并输入用户名
            driver.find_element_by_id('aw-login-user-password').send_keys('***')  # 定位并输入用户名
            driver.find_element_by_id('login_submit').click()

        time.sleep(3)
        driver.get(url)
        driver.implicitly_wait(3)  # 等待3秒
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(driver.page_source, "html.parser")
        # print(soup)
        table = soup.find('tbody', id='bond_table_body')
        data =[]
        if table is not None:
            for tr in table.findAll('tr'):
                col = 0
                row=[]
                for td in tr.findAll('td'):
                    col+=1
                    if col in (1,2,6,8,10,14):
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
                if irow[5][-1]=='%':
                    if irow[4][-1]=='%':
                        ytm=float(irow[4][:-1])
                    else:
                        ytm = float(irow[4])
                    bs =0.95 * 1/(100/(0.88*float(irow[5][:-1]))-1)
                    total = ytm + (ytm - 3.6) * bs
                    if total >= 10.5 and float(irow[3])<2:
                        print('%s,%s,%s  - total=%s' % (irow[0],irow[1],irow[3],round(total,2)))
        #print(soup)
    except:
        print ('请安装phantomjs')

except ImportError:
    print('No module named selenium. 请安装selenium模块')
