# -*- coding:utf-8 -*-

__author__ = 'gxb'
"""
视频爬虫
"""

import json
import re
from threading import Thread

import requests
import wx
from moviepy.editor import *
from pubsub import pub
from pyquery import PyQuery as pq
from requests import RequestException

APP_TITLE = u'视频下载器'
WEB_List = ['B站']

# 消息发送的类型
SEND_LOG_INFO = "logInfo"
SEND_STATUS_INFO = "statusInfo"
SEND_PROGRESS_BAR_INFO = "progressBarInfo"


class mainFrame(wx.Frame):
    """
    程序主窗口类，继承自wx.Frame
    """

    def __init__(self, parent):
        """
        构造函数
        """
        # 设置面板属性
        fixSize = (600, 500)
        wx.Frame.__init__(self, parent, -1, APP_TITLE, size=fixSize)
        self.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.SetMaxSize(fixSize)
        self.SetMinSize(fixSize)
        self.Center()

        # 设置图标
        icon = wx.Icon('res/favicon.ico', wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)

        SMALL_FONT = wx.Font(10, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
        MIDDLE_FONT = wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
        LEFT_MARGIN = 30
        HEIGHT_LINE1 = 10

        # 网站
        wx.StaticText(self, -1, u'网站：', pos=(LEFT_MARGIN, HEIGHT_LINE1), style=wx.ALIGN_RIGHT)

        self.webChoice = wx.Choice(self, -1, pos=(LEFT_MARGIN + 40, HEIGHT_LINE1), size=(70, 20), choices=WEB_List,
                                   style=wx.ALIGN_CENTER_VERTICAL)
        self.webChoice.SetSelection(0)
        self.webChoice.SetFont(SMALL_FONT)
        # 添加事件处理
        self.Bind(wx.EVT_CHOICE, self.OnWebChoice, self.webChoice)
        # print(self.webChoice.GetSelection())

        # 模式
        wx.StaticText(self, -1, u'模式：', pos=(LEFT_MARGIN + 180, HEIGHT_LINE1), style=wx.ALIGN_RIGHT)
        modeRadio1 = wx.RadioButton(self, -1, u'单视频', pos=(LEFT_MARGIN + 220, HEIGHT_LINE1), style=wx.RB_GROUP)
        modeRadio2 = wx.RadioButton(self, -1, u'视频选集', pos=(LEFT_MARGIN + 280, HEIGHT_LINE1))
        for eachRadio in [modeRadio1, modeRadio2]:
            self.Bind(wx.EVT_RADIOBUTTON, self.OnModeRadio, eachRadio)
        # 视频选集的需要提供选集的页码区间，比如：1-5，就是下载第1-5个选集视频
        self.beginNum = wx.TextCtrl(self, -1, u'1', pos=(385, HEIGHT_LINE1), size=(40, 20), style=wx.TE_CENTER)
        self.numLine = wx.StaticText(self, -1, '-', pos=(430, HEIGHT_LINE1), style=wx.ALIGN_CENTER)
        self.endNum = wx.TextCtrl(self, -1, u'5', pos=(440, HEIGHT_LINE1), size=(40, 20), style=wx.TE_CENTER)
        self.beginNum.Hide()
        self.numLine.Hide()
        self.endNum.Hide()

        # 保存目录
        HEIGHT_LINE2 = 45
        wx.StaticText(self, - 1, u'保存目录:', pos=(LEFT_MARGIN, HEIGHT_LINE2), style=wx.ALIGN_RIGHT)
        self.savePath = wx.TextCtrl(self, -1, u'D:\视频', pos=(LEFT_MARGIN + 60, HEIGHT_LINE2), size=(400, 20))
        dirBtn = wx.Button(self, -1, u'浏览', pos=(500, HEIGHT_LINE2), size=(40, 20))
        # dirBtn.SetFont(MIDDLE_FONT)
        self.Bind(wx.EVT_BUTTON, self.onDirButton, dirBtn)

        HEIGHT_LINE3 = 80
        # 网址输入框
        wx.StaticText(self, - 1, u'请在下方输入视频网址，多个网址之间换行隔开:', pos=(LEFT_MARGIN, HEIGHT_LINE3))
        self.websiteUrl = wx.TextCtrl(self, -1, pos=(LEFT_MARGIN, HEIGHT_LINE3 + 20), size=(390, 100),
                                      style=wx.TE_MULTILINE | wx.TE_AUTO_URL)

        # 开始下载按钮
        self.donwloadButton = wx.Button(self, -1, u'开 始\n下 载', pos=(440, HEIGHT_LINE3 + 20), size=(100, 100))
        self.donwloadButton.SetBackgroundColour(wx.Colour(0, 157, 255))
        self.donwloadButton.SetFont(wx.Font(13, wx.ROMAN, wx.NORMAL, wx.BOLD))
        self.Bind(wx.EVT_BUTTON, self.OnDownloadButton, self.donwloadButton)

        HEIGHT_LINE4 = 220
        # 日志信息
        self.logInfoText = wx.TextCtrl(self, -1, pos=(LEFT_MARGIN, HEIGHT_LINE4), size=(520, 180),
                                       style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.logInfoText.SetFont(SMALL_FONT)
        # self.logInfoText.Enable(False)

        # 状态栏
        self.statusBar = wx.StatusBar(self, -1)
        self.statusBar.SetSizeWH(580, 20)

        HEIGHT_LINE5 = 410
        # 进度条
        self.progressBar = wx.Gauge(self, -1, 100, pos=(LEFT_MARGIN, HEIGHT_LINE5), size=(520, 20),
                                    style=wx.GA_HORIZONTAL)

        # 消息接收显示
        pub.subscribe(self.updateDisplay, "update")

    def OnWebChoice(self, event):
        """
        网站选择事件函数
        :param evt:
        :return:
        """
        updateStatusText('选择网站：' + event.GetString())
        # print(event.GetSelection())

    def OnModeRadio(self, event):
        """
        模式选择事件函数
        :param evt:
        :return:
        """
        radioSelected = event.GetEventObject()
        text = radioSelected.GetLabel()
        updateStatusText(f'选择模式:{text}')
        if text == '视频选集':
            self.beginNum.Show()
            self.numLine.Show()
            self.endNum.Show()
        else:
            self.beginNum.Hide()
            self.numLine.Hide()
            self.endNum.Hide()

    def onDirButton(self, event):
        """
        文件选择事件函数
        :param event:
        :return:
        """

        dlg = wx.DirDialog(self, u'选择保存目录', style=wx.DD_DEFAULT_STYLE)
        if dlg.ShowModal() == wx.ID_OK:
            self.savePath.SetLabelText(dlg.GetPath())

    def OnDownloadButton(self, event):
        """
        下载按钮事件函数
        :param event:
        :return:
        """

        url = self.websiteUrl.GetValue().strip()
        if url:
            urlList = url.split('\n')
            if self.webChoice.GetSelection() == 0:  # B站
                BilibiliVideoSpider(urlList=urlList)
            else:  # 其他网站
                pass
        else:
            wx.LogWarning("请输入网址！")

    def updateDisplay(self, type, message=None):
        """
        更新显示信息
        :param type:    信息显示的类型，是日志信息，还是状态栏信息……
        :param message: 信息内容
        :return:
        """
        if type == SEND_LOG_INFO:
            printLogs(message)
        elif type == SEND_STATUS_INFO:
            updateStatusText(message)
        elif type == SEND_PROGRESS_BAR_INFO:
            updateProgressBar(value=message)
        else:
            pass


def printLogs(message):
    """
    打印日志信息，追加到日志显示框中
    :param message:
    :return:
    """
    app.Frame.logInfoText.AppendText(message + '\n')


def updateStatusText(message):
    """
    打印状态栏信息
    :param message:
    :return:
    """
    app.Frame.statusBar.SetStatusText(message)


def getSavePath():
    """
    获取保存路径
    :return:
    """
    return app.Frame.savePath.GetValue()


def updateProgressBar(addNum=1, value=None):
    """
    设置进度条的值，默认每次加1
    :param addNum:
    :return:
    """
    if value:
        app.Frame.progressBar.SetValue(value)
    else:
        app.Frame.progressBar.SetValue(app.Frame.progressBar.Value + addNum)


class mainApp(wx.App):
    def OnInit(self):
        self.SetAppName(APP_TITLE)
        self.Frame = mainFrame(None)
        self.Frame.Show()
        return True


class BilibiliVideoSpider(Thread):
    """
    B站视频爬虫
    """

    def __init__(self, urlList):
        self.getHtmlHeaders = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'zh-CN,zh;q = 0.9'
        }

        self.downloadVideoHeaders = {
            'Origin': 'https://www.bilibili.com',
            'Referer': 'https://www.bilibili.com/video/av26522634',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36',
        }
        self.urlList = urlList

        Thread.__init__(self)
        self.start()

    # 一般这里得到的网页源码和F12查看看到的不一样，因为F12开发者工具里的源码经过了浏览器的解释
    def getHtml(self, url):
        try:
            response = requests.get(url=url, headers=self.getHtmlHeaders)
            if response.status_code == 200:
                return response.text
        except RequestException:
            pub.sendMessage("update", type=SEND_LOG_INFO, message="请求Html错误!!!")
            app.Frame.donwloadButton.Enable(True)

    def parseHtml(self, html):
        # 用pq解析得到视频标题
        doc = pq(html)
        video_title = doc('#viewbox_report > h1 > span').text()

        # 用正则、json得到视频url;用pq失败后的无奈之举
        pattern = r'\<script\>window\.__playinfo__=(.*?)\</script\>'
        result = re.findall(pattern, html)[0]
        temp = json.loads(result)
        for item in temp['data']['dash']['video']:
            if 'baseUrl' in item.keys():
                video_url = item['baseUrl']

        for item in temp['data']['dash']['audio']:
            if 'baseUrl' in item.keys():
                audio_url = item['baseUrl']

        return {
            'title': video_title,
            'video_url': video_url,
            'audio_url': audio_url
        }

    def downloadVideo(self, video, title=None):
        """
        下载视频
        :param video:
        :param title:
        :return:
        """
        if not title:
            title = re.sub(r'[\/:*?"<>|]', '-', video['title'])  # 去掉创建文件时的非法字符
        url = video['video_url']
        filename = title + '.flv'
        pub.sendMessage("update", type=SEND_LOG_INFO, message=f"开始下载视频 -> {filename}")
        savePath = getSavePath()
        if not os.path.exists(savePath):
            os.mkdir(savePath)
        filePath = os.path.join(savePath, filename)
        with open(filePath, "wb") as f:
            f.write(requests.get(url=url, headers=self.downloadVideoHeaders, stream=True, verify=False).content)
        pub.sendMessage("update", type=SEND_PROGRESS_BAR_INFO)
        return filePath

    def downloadAudio(self, audio, title=None):
        """
        下载音频
        :param audio:
        :param title:
        :return:
        """
        if not title:
            title = re.sub(r'[\/:*?"<>|]', '-', audio['title'])  # 去掉创建文件时的非法字符
        url = audio['audio_url']
        filename = title + '.mp3'
        pub.sendMessage("update", type=SEND_LOG_INFO, message=f"开始下载音频 -> {filename}")
        savePath = getSavePath()
        if not os.path.exists(savePath):
            os.mkdir(savePath)
        filePath = os.path.join(savePath, filename)
        with open(filePath, "wb") as f:
            f.write(requests.get(url=url, headers=self.downloadVideoHeaders, stream=True, verify=False).content)
        pub.sendMessage("update", type=SEND_PROGRESS_BAR_INFO)
        return filePath

    def composeVideoAudio(self, videoFile, audioFile):
        """
        合成视频和音频
        :param videoFile: 视频文件路径
        :param audioFile: 音频文件路径
        :param target:
        :return: 合成后的视频路径
        """
        pub.sendMessage("update", type=SEND_LOG_INFO, message="开始合并音、视频文件……")
        video = VideoFileClip(videoFile)
        audio_clip = AudioFileClip(audioFile)
        video = video.set_audio(audio_clip)
        target = os.path.join(getSavePath(), videoFile.replace('.flv', '.mp4'))
        video.write_videofile(target)
        pub.sendMessage("update", type=SEND_PROGRESS_BAR_INFO)
        pub.sendMessage("update", type=SEND_LOG_INFO, message=f"合成最终视频文件 -> {target}")
        os.remove(videoFile)
        os.remove(audioFile)

    def batchSpiderVideo(self):
        count = 1
        app.Frame.donwloadButton.Enable(False)
        pub.sendMessage("update", type=SEND_LOG_INFO, message="开始下载B站视频……")

        app.Frame.progressBar.SetValue(0)
        app.Frame.progressBar.SetRange(len(self.urlList) * 3)  # 每个视频下载分为3步，所以总区间设置为视频数*步数
        for ur in self.urlList:
            html = self.parseHtml(self.getHtml(ur))
            videoPath = self.downloadVideo(html, str(count))
            audioPath = self.downloadAudio(html, str(count))
            self.composeVideoAudio(videoPath, audioPath)
            pub.sendMessage("update", type=SEND_STATUS_INFO, message=(str(count) + '个视频下载完成！'))
            count += 1
        pub.sendMessage("update", type=SEND_PROGRESS_BAR_INFO, message=len(self.urlList) * 3)
        app.Frame.donwloadButton.Enable(True)

    def run(self):
        self.batchSpiderVideo()


if __name__ == "__main__":
    app = mainApp()
    app.MainLoop()
