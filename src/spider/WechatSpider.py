import requests
import time
import re
import os
import sys
import subprocess
import xml.dom.minidom
import json
import urllib
import threading
from urllib import parse
class WechatSpider(object):
    tip = 0
    uuid = ''
    base_uri = ''
    redirect_uri = ''
    push_uri = ''

    skey = ''
    wxsid = ''
    wxuin = ''
    pass_ticket = ''
    deviceId = 'e000000000000000'

    BaseRequest = {}
    ContactList = []
    My = []
    SyncKey = []

    def __init__(self, debug=False):
        self.req = requests.Session()
        headers = {
            'User-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.125 Safari/537.36'}
        self.req.headers.update(headers)
        self.QRImagePath = os.path.join(os.getcwd(), 'qrcode.jpg')
        self.DEBUG = debug
        self.friend_list = []
        self.group_list = []

    def getUUid(self):
        global uuid
        url = 'https://login.weixin.qq.com/jslogin'
        params = {
            'appid': 'wx782c26e4c19acffb',
            'func': 'new',
            'lang': 'zh_CN',
            '_': int(time.time()),
        }
        r = self.req.get(url=url, params=params)
        r.encoding = 'utf-8'
        data = r.text
        regx = r'window.QRLogin.code = (\d+); window.QRLogin.uuid = "(\S+?)"'
        pm = re.search(regx, data)
        code = pm.group(1)
        uuid = pm.group(2)
        if code == '200':
            return True
        return False

    def responseState(self, func, BaseResopnse):
        ErrMsg = BaseResopnse['ErrMsg']
        Ret = BaseResopnse['Ret']
        if self.DEBUG or Ret != 0:
            print('func: %s, Ret %d. ErrMsg:%s' % (func, Ret, ErrMsg))

        if Ret != 0:
            return False
        return True

    def showQRImage(self):
        global tip
        url = 'https://login.weixin.qq.com/qrcode/' + uuid
        params = {
            't': 'webwx',
            '_': int(time.time()),
        }
        r = self.req.get(url=url, params=params)

        tip = 1
        f = open(self.QRImagePath, 'wb')
        f.write(r.content)
        f.close()
        time.sleep(1)

        # for mac os
        if sys.platform.find('darwin') >= 0:
            subprocess.call(['open', self.QRImagePath])
        # for linux
        elif sys.platform.find('linux') >= 0:
            subprocess.call(['xdg-open', self.QRImagePath])
        # for windows
        elif sys.platform.find('win32') >= 0:
            # subprocess.call(['open', QRImagePath])
            os.startfile(self.QRImagePath)
        else:
            subprocess.call(['xdg-open', self.QRImagePath])
        print('请使用微信扫描二维码登陆')

    def waitForLogin(self):
        global tip, base_uri, redirect_uri, push_uri

        url = 'https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?tip=%s&uuid=%s&_=%s' % (
            tip, uuid, int(time.time()))
        r = self.req.get(url=url)
        r.encoding = 'utf-8'
        data = r.text
        regx = r'window.code=(\d+);'
        pm = re.search(regx, data)

        code = pm.group(1)

        if code == '201':
            print('扫描成功，请在手机上点击确认以登陆')
            tip = 0
        elif code == '200':
            print('正在登陆...')
            regx = r'window.redirect_uri="(\S+?)";'
            pm = re.search(regx, data)
            redirect_uri = pm.group(1) + '&fun=new'
            base_uri = redirect_uri[:redirect_uri.rfind('/')]

            services = [('wx2.qq.com', 'webpush2.weixin.qq.com'), ('qq.com', 'webpush.weixin.qq.com'),
                        ('web1.wechat.com', 'webpush1.wechat.com'), ('web2.wechat.com', 'webpush2.wechat.com'),
                        ('wechat.com', 'webpush.wechat.com'), ('web1.wechatapp.com', 'webpush1.wechatapp.com'), ]

            push_uri = base_uri
            for (searchUrl, pushUrl) in services:
                if base_uri.find(searchUrl) >= 0:
                    push_uri = 'https://%s/cgi-bin/mmwebwx-bin' % pushUrl
                    break
            # closeQRImage
            if sys.platform.find('darwin') >= 0:
                # for OSX with Preview
                os.system("osascript -e 'quit app \"Preview\"'")
        elif code == '408':
            # 超时
            pass
        # elif code == '400' or code == '500':

        return code

    def login(self):
        global skey, wxsid, wxuin, pass_ticket, BaseRequest
        r = self.req.get(url=redirect_uri)
        r.encoding = 'utf-8'
        data = r.text
        # print(data)
        doc = xml.dom.minidom.parseString(data)
        root = doc.documentElement
        for node in root.childNodes:
            if node.nodeName == 'skey':
                skey = node.childNodes[0].data
            elif node.nodeName == 'wxsid':
                wxsid = node.childNodes[0].data
            elif node.nodeName == 'wxuin':
                wxuin = node.childNodes[0].data
            elif node.nodeName == 'pass_ticket':
                pass_ticket = node.childNodes[0].data
        # print('skey: %s, wxsid: %s, wxuin: %s, pass_ticket: %s' % (skey, wxsid, # wxuin, pass_ticket))

        if not all((skey, wxsid, wxuin, pass_ticket)):
            return False
        BaseRequest = {
            'Uin': int(wxuin),
            'Sid': wxsid,
            'Skey': skey,
            'DeviceID': self.deviceId,
        }

        return True

    def webwxinit(self):
        url = (base_uri +
               '/webwxinit?pass_ticket=%s&skey=%s&r=%s' % (
                   pass_ticket, skey, int(time.time())))
        params = {'BaseRequest': BaseRequest}
        headers = {'content-type': 'application/json; charset= UTF-8'}

        r = self.req.post(url=url, data=json.dumps(params), headers=headers)
        r.encoding = 'utf-8'
        data = r.json()

        if self.DEBUG:
            f = open(os.path.join(os.getcwd(), '../resource/webwxinit.json'), 'wb')
            f.write(r.content)
            f.close()

        # print(data)

        global ContactList, My, SyncKey
        dic = data
        ContactList = dic['ContactList']
        My = dic['User']
        SyncKey = dic['SyncKey']

        state = self.responseState('webwxinit', dic['BaseResponse'])
        return state

    def get_contact_url(self):
        base_url = base_uri + '/webwxgetcontact?'
        params = {
            "pass_ticket": self.pass_ticket,
            "skey": self.skey,
            "r": int(time.time())
        }
        url = base_url + parse.urlencode(params)
        return url

    def get_group_url(self):
        base_url = base_uri + '/webwxbatchgetcontact?'
        params = {
            "type": "ex",
            "pass_ticket": self.pass_ticket,
            "skey": self.skey,
            "r": int(time.time()),
            "lang": 'zh_CN'
        }
        url = base_url + parse.urlencode(params)
        return url


    def webwxgetcontact(self):
        # url = (base_uri + '/webwxgetcontact?pass_ticket=%s&skey=%s&r=%s' % (pass_ticket, skey, int(time.time())))
        user_url = self.get_contact_url()
        headers = {
            'content-type': 'application/json; charset=UTF-8',
        }
        r1 = self.req.post(url=user_url, headers=headers)
        r1.encoding = 'utf-8'
        print("get memeber list")
        url = self.get_group_url()



        data = r1.json()
        if self.DEBUG:
            f = open(os.path.join(os.getcwd(), '../resource/webwxgetcontact.json'), 'wb')
            f.write(r1.content)
            f.close()


        dic = data
        MemberList = dic['MemberList']

        # 倒序遍历,不然删除的时候出问题..
        SpecialUsers = ["newsapp", "fmessage", "filehelper", "weibo", "qqmail", "tmessage", "qmessage", "qqsync",
                        "floatbottle", "lbsapp", "shakeapp", "medianote", "qqfriend", "readerapp", "blogapp",
                        "facebookapp",
                        "masssendapp", "meishiapp", "feedsapp", "voip", "blogappweixin", "weixin", "brandsessionholder",
                        "weixinreminder", "wxid_novlwrv3lqwv11", "gh_22b87fa7cb3c", "officialaccounts",
                        "notification_messages", "wxitil", "userexperience_alarm"]

        for i in range(len(MemberList) - 1, -1, -1):
            Member = MemberList[i]
            if Member['VerifyFlag'] & 8 != 0:  # 公众号/服务号
                MemberList.remove(Member)
            elif Member['UserName'] in SpecialUsers:  # 特殊账号
                MemberList.remove(Member)
            elif Member['UserName'].find('@@') != -1:  # 群
                MemberList.remove(Member)
                self.group_list.append(Member)
            elif Member['UserName'] == My['UserName']:  # 自己
                MemberList.remove(Member)

        return MemberList

    def create_bacth_query_data(self):
        group_list = list(map(lambda x: {"EncryChatRoomId": '', "UserName": x['UserName']}, self.group_list))
        params = {'BaseRequest': BaseRequest, 'Count': len(group_list), 'List': group_list}
        print(params)
        return json.dumps(params)

    def getwxbatchcontact(self):
        r2 = self.req.post(url=self.get_group_url(), data=self.create_bacth_query_data())
        r2.encoding = 'utf-8'
        data2 = r2.json()
        if self.DEBUG:
            f2 = open(os.path.join(os.getcwd(), '../resource/webwxbatchgetcontact.json'), 'wb')
            f2.write(r2.content)
            f2.close()
        print(data2)

    def syncKey(self):
        SyncKeyItems = ['%s_%s' % (item['Key'], item['Val'])
                        for item in SyncKey['List']]
        SyncKeyStr = '|'.join(SyncKeyItems)
        return SyncKeyStr

    def syncCheck(self):
        url = push_uri + '/synccheck?'
        params = {
            'skey': BaseRequest['/Skey'],
            'sid:': BaseRequest['Sid'],
            'uin:': BaseRequest['Uin'],
            'deviceId': BaseRequest['DeviceId'],
            'syncKey': self.syncKey(),
            'r': int(time.time())
        }
        r = self.req.get(url=url, params=params)
        r.encoding = 'utf-8'
        data = r.text

        regx = r'window.synccheck={retcode:"(\d+)", selector:"(\d+)"}'
        pm = re.search(regx, data)

        retcode = pm.group(1)
        selector = pm.group(2)
        return selector

    def webwxsync(self):
        global SyncKey
        url = base_uri + '/webwxsync?lang=zh_CN&skey=%s&sid=%s&pass_ticket=%s' % (
            BaseRequest['Skey'], BaseRequest['Sid'], urllib.quote_plus(pass_ticket))

        params = {'BaseRequest': BaseRequest, 'SyncKey': SyncKey, 'rr': ~int(time.time()), }
        headers = {'content-type': 'application/json; charset=UTF-8'}
        r = self.req.post(url=url, data=json.dumps(params))
        r.encoding = 'utf-8'
        data = r.json()

        dic = data
        SyncKey = dic['SyncKey']
        state = self.responseState('webwxsync', dic['BaseResponse'])
        return state

    def heartBeatLoop(self):
        while True:
            selector = self.syncCheck()
            if selector != '0':
                self.webwxsync()
                time.sleep(1)

    def spider(self):
        if not self.getUUid():
            print('获取uuid失败')
            return
        print('正在获取二维码图片...')
        self.showQRImage()

        while self.waitForLogin() != '200':
            pass

        os.remove(self.QRImagePath)

        if not self.login():
            print('登录失败')
            return
        if not self.webwxinit():
            print('初始化失败')
            return
        self.MemberList = self.webwxgetcontact()
        self.getwxbatchcontact()
        threading.Thread(target=self.heartBeatLoop)
        MemberCount = len(self.MemberList)
        print('通讯录共%s位好友' % MemberCount)

if __name__ == '__main__':
    ws = WechatSpider(debug=True)
    ws.spider()