from fake_useragent import UserAgent
import datetime
import requests
import re
import random
from lxml import etree
import time

class Utils(object):
    def __init__(self, sid, titleExpression, year):
        #ua = UserAgent(verify_ssl=False)
        ua = UserAgent(path="fake_useragent.json")
        fake_agent = ua.random
        thisYear = datetime.datetime.now().year
        self.hearders = {
            'Origin': 'https://apps.webofknowledge.com',
            'Referer': 'https://apps.webofknowledge.com/UA_GeneralSearch_input.do?product=UA&search_mode=GeneralSearch&SID='+sid,
            'User-Agent': fake_agent,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        self.form_data = {
            'fieldCount': 2,
            'action': 'search',
            'product': 'WOS',
            'search_mode': 'GeneralSearch',
            'SID': sid,
            'max_field_count': 25,
            'formUpdated': 'true',
            'value(input1)': titleExpression,
            'value(select1)': 'SO',
            'value(hidInput1)': '',
            'value(bool_1_2)': 'AND',
            'value(input2)': year,
            'value(select2)': 'PY',
            'value(hidInput2)': '',
            'limitStatus': 'collapsed',
            'ss_lemmatization': 'On',
            'ss_spellchecking': 'Suggest',
            'SinceLastVisit_UTC': '',
            'SinceLastVisit_DATE': '',
            'period': 'Range Selection',
            'range': 'ALL',
            'startYear': '1982',
            'endYear': thisYear,
            'update_back2search_link_param': 'yes',
            'ssStatus': 'display:none',
            'ss_showsuggestions': 'ON',
            'ss_query_language': 'auto',
            'ss_numDefaultGeneralSearchFields': 1,
            'rs_sort_by': 'PY.D;LD.D;SO.A;VL.D;PG.A;AU.A'
        }

    def craw(self,root_url,item,file,threshold,start):
        try:
            s = requests.Session()
            r = s.post(root_url, data=self.form_data, headers=self.hearders)
            #f = open("save.txt",'a')
            #f.write(r.text)
            r.encoding = r.apparent_encoding
            tree = etree.HTML(r.text)
            totalRes = int(tree.xpath("//span[@id='trueFinalResultCount']/text()")[0])
            totalPage = int(tree.xpath("//span[@id='pageCount.top']/text()")[0].replace(",",""))
            paperPerPage = round(totalRes/totalPage)
            print("total result item number is: "+str(totalRes))
            print("paper per page: "+str(paperPerPage))

            #这个用来限制爬多少页文章之后更换SID防止封SID反扒
            #现在是20页*10条=200条后更换一次SID，如果程序中途退出的话，基本就是SID被封了，把这个数调小一点
            #然后从progress里记录的数开始，改stop_id后再运行就行了。
            #另外如果已经完成了source.txt中某一项的搜索，这个时候需要临时吧source.txt中间的某一项搜索条件删掉后，
            #再进行上述过程，防止重复记录（其实也可以再写一个防重复。。。但是我懒）
            pressure_threshold = threshold
            #这个用来更改起始的位置,0表示从头开始
            start_id = start

            if (start_id % paperPerPage == 0):
                start_id = start_id - 1
            start_page = int(start_id / paperPerPage) + 1
            paper_id = (start_page - 1) * paperPerPage  
            if (start_id % paperPerPage == 0):
                start_id = start_id + 1

            for j in range(start_page, totalPage+1):
                #Update sid, renew search item
                if (j % pressure_threshold == 0 & paper_id > start_id):
                    print("Applying for a new session")
                    root = 'https://apps.webofknowledge.com'
                    sid_url = requests.get(root)
                    sid = re.findall(r'SID=\w+&', sid_url.url)[0].replace('SID=', '').replace('&', '')
                    self.form_data['SID']=sid
                    print("new sid")
                    print(self.form_data.get('SID'))
                    ua = UserAgent(path="fake_useragent.json")
                    fake_agent = ua.random 
                    self.hearders['User-Agent']=fake_agent
                    r = s.post(root_url, data=self.form_data, headers=self.hearders)
                
                searched_result_page_url = "http://apps.webofknowledge.com/summary.do?product=WOS&search_mode=GeneralSearch&qid=1&SID="+self.form_data.get('SID')+"&&update_back2search_link_param=yes&page="+str(j)
                #print(searched_result_page_url)
                r = s.get(searched_result_page_url, headers=self.hearders) 
                tree = etree.HTML(r.text)
                #f = open("save"+str(j)+".txt",'a')
                #f.write(r.text)

                for i in range(1, paperPerPage+1):
                    paper_id += 1
                    #print(paper_id)
                    if (paper_id <= start_id):
                        continue
                    
                    full_record_location = "//div[@id='RECORD_" + str(paper_id) + "']/div[@class='search-results-content']//a[starts-with(@href,'/full_record')]/@href"
                    full_record_page_url = self.hearders.get('Origin')+tree.xpath(full_record_location)[0]
                    #print(full_record_page_url)
                    #这里停了随机0～1秒，尽可能地避免爬虫检测
                    wait_time = random.random()
                    time.sleep(wait_time)
                    #print("here 1")
                    paper_page = s.get(full_record_page_url, headers=self.hearders)
                    #print("here 2")
                    #file.write(paper_page.text)
                    paper_page.encoding = paper_page.apparent_encoding
                    paper_page_tree = etree.HTML(paper_page.text)
                    #f = open("save.txt",'a')
                    #f.write(paper_page.text)
                    #print("here 3")
                    title = paper_page_tree.xpath("//div[@class='title']/value/text()")[0]
                
                    authorRaw =  paper_page_tree.xpath("//p[@class='FR_field' and contains(.//span, 'By')]/text()")
                    authorRaw2 = list(filter(lambda x: x != '\n', authorRaw))
                    author = ''.join(list(map(lambda x: x.replace('(', '').replace(')', ''), authorRaw2)))
                
                    journal = paper_page_tree.xpath("//span[@class='sourceTitle']//span[@class='hitHilite']/text()")[0]
                
                    publish_year = paper_page_tree.xpath("//p[@class='FR_field' and contains(.//span, 'Published')]/value/text()")[0]
                
                    abstract = ''.join(paper_page_tree.xpath("//div[@class='block-record-info' and contains(.//div, 'Abstract')]/p/text()"))
                    
                    keyword = ','.join(paper_page_tree.xpath("//div[@class='block-record-info' and contains(.//span, 'Keywords')]//a/text()"))
                    
                    #print(title)
                    #print(author)
                    #print(journal)
                    #print(publish_year)
                    #print(abstract)
                    #print(keyword)

                    file.writelines('Title: \n')
                    file.writelines(title+"\n")
                    file.writelines('Author: \n')
                    file.writelines(author+'\n')
                    file.writelines('Journal: \n')
                    file.writelines(journal+"\n")
                    file.writelines('Publish Year: \n')
                    file.writelines(publish_year+'\n')
                    file.writelines('Abstract: \n')
                    file.writelines(abstract+'\n')
                    file.writelines('Keyword: \n')
                    file.writelines(keyword+'\n')
                    file.writelines('\n')
                    print("Progress: "+str(item)+":"+str(paper_id)+"/"+str(totalRes))

        except Exception as e:
            print(e)
            print(i)
            print(searched_result_page_url)
            print(full_record_page_url)
            flag = 1
            return


if __name__ == "__main__":
    
    source = open('source.txt','rt').readlines()
    count = len(source)
    #print(count)

    root = 'https://apps.webofknowledge.com'
    s = requests.get(root)
    sid = re.findall(r'SID=\w+&', s.url)[0].replace('SID=', '').replace('&', '')
    print("Applying for a new session")
    print("SID") 
    print(sid)

    #每多少页更新一次SID改这里
    threshold = 15
    #上次停的地方，这里从这里再开始（这里是1527的话，则再次运行开始记录的是1528条）
    start_id = 1527
    #上次停的source.txt里的第几条改这里,0是第一条，依此类推
    start_item = 0

    saved_result = open("result.txt", 'a')
    #saved_result.write("Title, Author, Journal/Conference, Publish Year, Abstract, Keywords")

    with open('source.txt', 'rt') as f:
        for i in range(start_item*2, count-1, 2):
            year = source[i]
            titleExpression = source[i+1]
            print("searched title expression: "+titleExpression)
            print("searched year: "+year)
            utils = Utils(sid, titleExpression, year)
            utils.craw('https://apps.webofknowledge.com/WOS_GeneralSearch.do', i/2+1, saved_result, threshold, start_id)