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

# 窗口标题
APP_TITLE = u'视频下载器'

# 多个网站直接在后面添加元素
WEB_List = ['B站']

# 视频清晰度
QUALITY = {
    "accept_description": ["高清 1080P", "高清 720P", "清晰 480P", "流畅 360P"],
    "accept_quality": [80, 64, 32, 16]
}

# 消息发送的类型
SEND_LOG_INFO = "logInfo"
SEND_STATUS_INFO = "statusInfo"
SEND_PROGRESS_BAR_INFO = "progressBarInfo"

# 通用控件样式
BTN_COLOUR = wx.Colour(0, 157, 255)


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
        icon = wx.Icon('favicon.ico', wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)

        SMALL_FONT = wx.Font(10, wx.DEFAULT, wx.NORMAL, wx.NORMAL)
        # MIDDLE_FONT = wx.Font(12, wx.DEFAULT, wx.NORMAL, wx.NORMAL)

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

        # 模式
        wx.StaticText(self, -1, u'模式：', pos=(LEFT_MARGIN + 180, HEIGHT_LINE1), style=wx.ALIGN_RIGHT)
        modeRadio1 = wx.RadioButton(self, -1, u'单视频', pos=(LEFT_MARGIN + 220, HEIGHT_LINE1), style=wx.RB_GROUP)
        modeRadio2 = wx.RadioButton(self, -1, u'视频选集', pos=(LEFT_MARGIN + 280, HEIGHT_LINE1))
        for eachRadio in [modeRadio1, modeRadio2]:
            self.Bind(wx.EVT_RADIOBUTTON, self.OnModeRadio, eachRadio)

        # 清晰度
        wx.StaticText(self, -1, u'清晰度：', pos=(LEFT_MARGIN + 390, HEIGHT_LINE1), style=wx.ALIGN_RIGHT)

        self.quanlityChoice = wx.Choice(self, -1, pos=(LEFT_MARGIN + 440, HEIGHT_LINE1), size=(70, 20),
                                        choices=QUALITY['accept_description'],
                                        style=wx.ALIGN_CENTER_VERTICAL)
        self.quanlityChoice.SetSelection(0)
        self.quanlityChoice.SetFont(SMALL_FONT)
        # 添加事件处理
        self.Bind(wx.EVT_CHOICE, self.OnQualityChoice, self.quanlityChoice)

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
        self.donwloadButton.SetBackgroundColour(BTN_COLOUR)
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
            # 视频选集解析弹窗
            self.videoListDialog = VideoListDialog(self, -1)
            self.videoListDialog.ShowModal()
        else:
            self.videoListDialog.Destroy()

    def OnQualityChoice(self, event):
        """
        视频清晰度选择事件
        :param event: 
        :return: 
        """
        updateStatusText('选择视频清晰度：' + event.GetString())
        # print(event.GetSelection())

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
                VideoSpiderThread(urlList=urlList)
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


class VideoListDialog(wx.Dialog):

    def __init__(self, parent, id):
        webNo = app.Frame.webChoice.GetSelection()
        super(VideoListDialog, self).__init__(parent, id, "视频选集解析-" + WEB_List[webNo], size=(400, 300))
        panel = wx.Panel(self)
        panel.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.webUrlTextCtrl = wx.TextCtrl(panel, -1, u'请在此输入网址', pos=(20, 10), size=(340, 20))
        self.resultListTextCtrl = wx.TextCtrl(panel, -1, pos=(20, 40), size=(340, 160), style=wx.TE_MULTILINE)
        self.parseWebUrlButton = wx.Button(panel, -1, u'解析网址', pos=(100, 210), size=(70, 30))
        self.parseWebUrlButton.SetBackgroundColour(BTN_COLOUR)
        self.autoWriteUrlListButton = wx.Button(panel, -1, u'一键填入', pos=(210, 210), size=(70, 30))
        self.autoWriteUrlListButton.SetBackgroundColour(BTN_COLOUR)
        self.Bind(wx.EVT_BUTTON, self.OnParseWebUrl, self.parseWebUrlButton)
        self.Bind(wx.EVT_BUTTON, self.OnAutoWriteUrlList, self.autoWriteUrlListButton)

    def OnParseWebUrl(self, event):
        """
        解析网址
        :param event:
        :return:
        """
        url = self.webUrlTextCtrl.GetValue().strip()
        if (not url) or not (str(url).startswith('http://') or str(url).startswith('https://')):
            wx.LogWarning("请填入正确的网址")
        else:
            self.resultListTextCtrl.SetLabelText('')
            try:
                if app.Frame.webChoice.GetSelection() == 0:  # B站
                    bSpider = BilibiliVideoSpider()
                    self.videoUrlList = bSpider.parseHtml(bSpider.getHtml(url))['video_url_list']
                    if self.videoUrlList:
                        for videoUrl in self.videoUrlList:
                            # self.resultListTextCtrl.AppendText(videoUrl['title'] + ': ' + videoUrl['url'] + '\n')
                            self.resultListTextCtrl.AppendText(videoUrl['url'] + '\n')
                else:
                    wx.MessageBox("获取其他网站视频选集")
            except Exception as e:
                self.resultListTextCtrl.SetLabelText('无法解析该网址！')

    def OnAutoWriteUrlList(self, event):
        """
        将解析后的网址填入主面板地址栏中
        :param event:
        :return:
        """
        urlList = self.resultListTextCtrl.GetValue().strip()
        if not urlList or urlList == '无法解析该网址！':
            wx.LogWarning('暂无可填入的网址')
        else:
            app.Frame.websiteUrl.SetLabelText(urlList)
            self.Close()
        # if self.videoUrlList:
        #     self.resultListTextCtrl.SetLabelText('')
        #     for videoUrl in self.videoUrlList:
        #         app.Frame.websiteUrl.AppendText(videoUrl['url'] + '\n')
        #         self.videoUrlList = ''
        #         self.Close()
        # else:
        #     wx.LogWarning('暂无可填入的网址')


class VideoSpiderThread(Thread):
    """
    多线程爬取视频，根据选择的不同网站执行不同的爬取方法
    """

    def __init__(self, urlList):
        Thread.__init__(self)
        self.urlList = urlList
        self.start()

    def run(self):
        if app.Frame.webChoice.GetSelection() == 0:  # B站
            BilibiliVideoSpider(urlList=self.urlList).batchSpiderVideo()
        else:  # 其他网站
            pass


class BilibiliVideoSpider:
    """
    B站视频爬虫
    """

    def __init__(self, urlList=None):
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
            # 根据不同的清晰度选择不同的下载网址
            selectedQuality = QUALITY['accept_quality'][app.Frame.quanlityChoice.GetSelection()]
            if selectedQuality == item['id']:
                if 'baseUrl' in item.keys():
                    video_url = item['baseUrl']

        for item in temp['data']['dash']['audio']:
            if 'baseUrl' in item.keys():
                audio_url = item['baseUrl']

        # 获取视频选集列表
        initial_pattern = r'\<script\>window\.__INITIAL_STATE__=(.*?)\;\(function\(\)'
        initial_res = re.findall(initial_pattern, html)[0]
        initial_temp = json.loads(initial_res)
        url_prefix = 'https://www.bilibili.com/video/' + initial_temp['videoData']['bvid'] + '?p='
        video_url_list = []
        for item in initial_temp['videoData']['pages']:
            video_url_list.append({'title': str(item['part']), 'url': url_prefix + str(item['page'])})

        return {
            'title': video_title,
            'video_url': video_url,
            'audio_url': audio_url,
            'video_url_list': video_url_list
        }

    def downloadVideo(self, video, titleSuffix=None):
        """
        下载视频
        :param video:
        :param title:
        :return:
        """
        title = re.sub(r'[\/:*?"<>|]', '-', video['title'])  # 去掉创建文件时的非法字符
        if titleSuffix:
            title += titleSuffix
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

    def downloadAudio(self, audio, titleSuffix=None):
        """
        下载音频
        :param audio:
        :param title:
        :return:
        """
        title = re.sub(r'[\/:*?"<>|]', '-', audio['title'])  # 去掉创建文件时的非法字符
        if titleSuffix:
            title += titleSuffix
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

    def spiderVideo(self, url, titleSuffix=None):
        """
        爬取视频
        :param url:     视频网址
        :param title:   保存的视频名称
        :return:
        """
        html = self.parseHtml(self.getHtml(url))
        videoPath = self.downloadVideo(html, titleSuffix)
        audioPath = self.downloadAudio(html, titleSuffix)
        self.composeVideoAudio(videoPath, audioPath)

    def batchSpiderVideo(self):
        """
        批量爬取视频
        :return:
        """
        count = 1
        app.Frame.donwloadButton.Enable(False)
        pub.sendMessage("update", type=SEND_LOG_INFO, message="开始下载B站视频……")

        app.Frame.progressBar.SetValue(0)
        app.Frame.progressBar.SetRange(len(self.urlList) * 3)  # 每个视频下载分为3步，所以总区间设置为视频数*步数
        for url in self.urlList:
            if len(self.urlList) == 1:
                self.spiderVideo(url)
            else:
                self.spiderVideo(url, ' - ' + str(count))
            pub.sendMessage("update", type=SEND_STATUS_INFO, message=(str(count) + '个视频下载完成！'))
            count += 1
        pub.sendMessage("update", type=SEND_PROGRESS_BAR_INFO, message=len(self.urlList) * 3)
        app.Frame.donwloadButton.Enable(True)


if __name__ == "__main__":
    app = mainApp()
    app.MainLoop()
