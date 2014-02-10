#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pygtk
pygtk.require("2.0")
import gtk
import gobject
gobject.threads_init()

import gtk.glade
import subprocess
import requests
import ConfigParser
import webbrowser
import json
import math
import os
import threading
import thread

configfile = "config.conf"

class TwitchBrowserGTK:

    def __init__(self):
        self.gladefile = "mainwindow.glade" 
        self.glade = gtk.Builder()
        self.glade.add_from_file(self.gladefile)
        self.glade.connect_signals(self) 
        #Get UI Objects      
        self.following_init = False
        self.browse_init = False
        self.window = self.glade.get_object("MainWindow")
        self.window.set_wmclass ("Twitch Browser", "Twitch Browser")
        self.window_width = self.window.get_allocation().width
        self.featured_table = self.glade.get_object("featured_table")
        self.following_table = self.glade.get_object("following_table")  
        self.games_table = self.glade.get_object("games_table")  
        self.featuredmorebutton = self.glade.get_object("featuredmorebutton")
        self.followingmorebutton = self.glade.get_object("followingmorebutton")
        self.gamesmorebutton = self.glade.get_object("gamesmorebutton")
        global notebook      
        global channel_tab_template
        notebook = self.glade.get_object("notebook1")
        self.popupmenu = self.glade.get_object("menu1") 
        self.settingsbutton = self.glade.get_object("settingsbutton") 
        initstarttabs(self)
        self.window.show_all()

    def on_MainWindow_delete_event(self, widget, event):
        gtk.main_quit()

    def on_quitmenuitem_activate(self, widget):
        gtk.main_quit()

    def on_refreshbutton_clicked(self, widget):
        for tab in tabs:
            tab.refresh()

    def on_settingsmenuitem_activate(self, widget):
        self.settingswindow = self.glade.get_object("SettingsWindow")
        self.usernameentry = self.glade.get_object("usernameentry")
        self.qualityentry = self.glade.get_object("qualityentry")
        self.playerentry = self.glade.get_object("pcmdentry")
        cancelbutton = self.glade.get_object("cancelbutton")
        savebutton = self.glade.get_object("savebutton")

        cancelbutton.connect("clicked", lambda w: self.settingswindow.hide())
        savebutton.connect("clicked", self.save_settings, self.settingswindow)

        if (username):
            self.usernameentry.set_text(username)
        self.qualityentry.set_text(quality)
        self.playerentry.set_text(playercmd)

        self.settingswindow.show_all()

    def on_aboutmenuitem_activate(self, widget):
        about = gtk.AboutDialog()
        about.set_name("Twitch Browser")
        about.set_website("http://www.screenfreeze.net")
        about.set_copyright("(c) Andreas Wilhelm")
        about.set_version("0.5")
        about.run()
        about.destroy()

    def on_settingsbutton_clicked(self, widget):
        self.popupmenu.popup(None, None, None, 0, 0)
        self.popupmenu.show_all()

    def save_settings(self, widget, sw):
        global username
        global quality
        global playercmd
        username = self.usernameentry.get_text()
        quality = self.qualityentry.get_text()
        playercmd = self.playerentry.get_text()
        savesettings()
        self.settingswindow.hide()
        for tab in tabs:
            tab.refresh()

    def on_notebook1_switch_page(self, widget, event ,page):
        if (page == 1 and not self.following_init):
            self.following_init = True
            followingtab.reorder()
        elif (page == 2 and not self.browse_init):
            self.browse_init = True
            gamestab.reorder()

    def on_MainWindow_resize_event(self, event):
        w = self.window.get_allocation().width
        wdif = abs(w - self.window_width)
        if (wdif > 100):
            self.window_width = w
            for tab in tabs:
                tab.reorder()

username = None
quality = "high"
playercmd = "vlc"
notebook = None
channel_tab_template = None
tabs = []

def loadsettings():
    config = ConfigParser.ConfigParser()
    if os.path.isfile(configfile):
        config.read(configfile)
        global username
        global quality
        global playercmd
        username = config.get('user', 'username')
        quality = config.get('stream', 'quality')
        playercmd = config.get('stream', 'playercmd')

def savesettings():
    config = ConfigParser.ConfigParser()
    if os.path.isfile(configfile):
        config.read(configfile)
        config.set('user','username', username)
        config.set('stream','quality', quality)
        config.set('stream','playercmd', playercmd)
        cfgfile = open(configfile, 'w')
        config.write(cfgfile)
        cfgfile.close()


class TableTab():
    
    def __init__(self, table, morebtn,
                apiurl, subelement, publicatemethod):
        self.data = None
        self.table = table
        self.apiurl = apiurl
        self.subelement = subelement
        self.itemsize = 80
        self.publicatemethod = publicatemethod
        morebtn.connect("clicked", self.onloadmore)
        thread.start_new_thread(self.refresh, ())

    def onloadmore(self, widget):
        thread.start_new_thread(self.loadmore, ())

    def loadmore(self):
        itemcount = len(self.data)
        columncount = self.table.get_property('n-columns')
        row = int(math.ceil(float(itemcount) / columncount)) -1
        column = (itemcount % columncount)-1
        newdata = query_twitch(self.apiurl+"&offset="+str(itemcount), self.subelement)        
        
        #if following tab -> check if live
        if (self.subelement == "follows"):
            check_live(newdata)

        self.data += newdata
        totalcnt = len(self.data)
        self.publicatemethod(self.table, newdata, self.itemsize, column, row, totalcnt)

    def refresh(self):
        self.data = query_twitch(self.apiurl, self.subelement)
        #if following tab -> check if live
        if (self.subelement == "follows"):
            check_live(self.data)
        self.update()

    def reorder(self):
        thread.start_new_thread(self.update, ())

    def update(self):
        children = self.table.get_children()
        for c in children:
            gobject.idle_add(self.table.remove, c)
        totalcnt = len(self.data)
        self.publicatemethod(self.table, self.data, self.itemsize, 0, 0, totalcnt)


def initstarttabs(window):
    global featuredtab
    global followingtab
    global gamestab
    featuredtab = TableTab(window.featured_table,
                    window.featuredmorebutton,
                    "https://api.twitch.tv/kraken/streams/featured?limit=25",
                    "featured",
                    publicate_table)
    tabs.append(featuredtab)
    gamestab = TableTab(window.games_table,
                    window.gamesmorebutton,
                    "https://api.twitch.tv/kraken/games/top?limit=25",
                    "top",
                    publicate_table_games)
    tabs.append(gamestab)
    if (username):
            followingtab = TableTab(window.following_table,
                    window.followingmorebutton,
                    "https://api.twitch.tv/kraken/users/"+username+"/follows/channels?limit=25",
                    "follows",
                    publicate_table)
            tabs.append(followingtab)


class downloadChannelThread (threading.Thread):

    def __init__(self, gameimage, bannerimage, game, bannerurl):
        threading.Thread.__init__(self)
        self.gameimage = gameimage
        self.bannerimage = bannerimage
        self.game = game
        self.bannerurl = bannerurl

    def run(self):
        data = query_twitch("https://api.twitch.tv/kraken/search/games?q="+self.game+"&type=suggest", "games")
        if (len(data) > 0):
            logourl = data[0]['box']['medium']
            download_logo(logourl)
            logourlsplit = logourl.split("/")
            logo = logourlsplit[len(logourlsplit)-1]
            self.gameimage.set_from_file('logos/'+logo)
            download_tmp(self.bannerurl)
            logourlsplit = self.bannerurl.split("/")
            logo = logourlsplit[len(logourlsplit)-1]
            pixbuf = gtk.gdk.pixbuf_new_from_file_at_scale('tmp/'+logo, 500, 100, True)
            self.bannerimage.set_from_pixbuf(pixbuf)
            self.bannerimage.show_all()
     

def publicate_table(table, jdata, lsize, column, row, totalcnt):
    data = jdata
    i=column
    j=row

    #calc Table
    itemcount = totalcnt
    twidth = table.get_allocation().width
    columncount = int(round(twidth / 102, 0))
    rowcount = int(math.ceil(float(itemcount) / columncount))
    if (table.get_property('n-columns') != columncount):
        table.resize(columncount, rowcount)

    for k in range(0, len(data)):    
        viewers = ""      
        islive = False
        if (data[k].has_key('channel')):
            channel = data[k]['channel']
            if (channel.has_key('islive')):
                islive = channel['islive']
        else:
            channel = data[k]['stream']['channel']
            viewers = data[k]['stream']['viewers']

        logourl = channel['logo']
        if logourl:
            download_logo(logourl)
            logourlsplit = channel['logo'].split("/")
            logo = logourlsplit[len(logourlsplit)-1]
            channel['logo'] = logo
        name = channel['name']
        status = unicode(channel['status'])
        img = gtk.Image()
        button = gtk.Button()
        button.connect("clicked", new_channel_tab, channel)
        pixbuf = gtk.gdk.pixbuf_new_from_file_at_scale('logos/'+logo, lsize, lsize, True)
        img.set_from_pixbuf(pixbuf)
        label = gtk.Label(name)
        box = gtk.VBox()

        box.pack_start(img, False, False, 0)
        box.pack_end(label, False, False, 0)
        if (islive):
            livelabel = gtk.Label("LIVE")
            livelabel.modify_fg(gtk.STATE_NORMAL, gtk.gdk.Color("red"))
            box.pack_end(livelabel, False, False, 0)

        button.add(box)
        tttext = status
        if (viewers):
            tttext = tttext+"\nViewers: "+str(viewers)

        button.set_tooltip_text(tttext)
        button.set_size_request(100, 110)
        button.show_all()
        if (i > columncount-1):
            j = j+1
            i = 0
        gobject.idle_add(table.attach,button, i, i+1, j, j+1)
        i = i+1
    table.show_all()

def publicate_table_games(table, jdata, lsize, column, row, totalcnt):
    data = jdata
    i=column
    j=row

    #calc Table
    itemcount = totalcnt
    twidth = table.get_allocation().width
    columncount = int(round(twidth / 102, 0))
    rowcount = int(math.ceil(float(itemcount) / columncount))
    if (table.get_property('n-columns') != columncount):
        table.resize(columncount, rowcount)

    for k in range(0, len(data)):  
        gamedata = data[k]['game']    
        viewers = data[k]['viewers']
        boxurl = gamedata['box']['medium']
        download_logo(boxurl)
        logourlsplit = boxurl.split("/")
        logo = logourlsplit[len(logourlsplit)-1]
        name = gamedata['name']

        img = gtk.Image()
        button = gtk.Button()
        button.connect("clicked", new_game_tab, name)
        pixbuf = gtk.gdk.pixbuf_new_from_file_at_scale('logos/'+logo, 100, 140, True)
        img.set_from_pixbuf(pixbuf)
        label = gtk.Label(name)
        box = gtk.VBox()
        box.pack_start(img, False, False, 0)
        box.pack_start(label, False, False, 0)
        button.add(box)
        tttext = ""
        if (viewers):
            tttext = tttext+"Viewers: "+str(viewers)
        button.set_tooltip_text(tttext)
        button.set_size_request(100, 165)
        button.show_all()
        if (i > columncount-1):
            j = j+1
            i = 0
        gobject.idle_add(table.attach,button, i, i+1, j, j+1)
        i = i+1
    table.show_all()

def new_channel_tab(button, jdata):
    glade = gtk.Builder()
    glade.add_from_file('channel_template.glade')
    box = glade.get_object("channelbox")
    channelimage = glade.get_object("channelimage")
    namelabel = glade.get_object("channelnamelabel")
    gameimage = glade.get_object("gameimage")
    bannerimage = glade.get_object("bannerimage")
    statuslabel = glade.get_object("statuslabel")
    gamelabel = glade.get_object("gamelabel")
    viewerslabel = glade.get_object("viewerslabel")
    openwebbutton = glade.get_object("openwebbutton")
    openchatbutton = glade.get_object("openchatbutton")
    openstreambutton = glade.get_object("openstreambutton")
    openvideosbutton = glade.get_object("openvideosbutton")
    
    name = jdata['name']
    url = jdata['url']
    views = jdata['views']
    game = unicode(jdata['game'])
    status = unicode(jdata['status'])
    chat_url = "http://www.twitch.tv/chat/embed?channel="+name
    videos_url = "http://www.twitch.tv/"+name+"/profile"
    bannerurl = jdata['banner']
    logo = jdata['logo']
    dglt = downloadChannelThread(gameimage, bannerimage, game, bannerurl)
    dglt.start()
    pixbuf = gtk.gdk.pixbuf_new_from_file_at_scale('logos/'+logo, 110, 110, True)
    channelimage.set_from_pixbuf(pixbuf)
    openwebbutton.connect("clicked", open_url, url)
    openchatbutton.connect("clicked", open_url, chat_url)
    openvideosbutton.connect("clicked", open_url, videos_url)
    
    if (not jdata.has_key('islive') or (jdata.has_key('islive') and jdata['islive'])):
        openstreambutton.connect("clicked", start_stream, name)
        openstreambutton.show_all()

    namelabel.set_text(name)
    statuslabel.set_text(status)
    gamelabel.set_text(game)
    viewerslabel.set_text(str(views))
    #build Tab Label
    lhbox = gtk.HBox()
    label = gtk.Label(name)
    closeimage = gtk.Image()
    closeimage.set_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU)
    btn = gtk.Button()
    btn.set_image(closeimage)
    btn.set_relief(gtk.RELIEF_NONE)
    lhbox.pack_start(label, True, True, 0)
    lhbox.pack_end(btn, False, False, 0)
    lhbox.show_all()    
    pagenum = notebook.append_page(box, lhbox)
    btn.connect("clicked", close_tab, box)
    notebook.set_current_page(pagenum)

def new_game_tab(button, game):
    glade = gtk.Builder()
    glade.add_from_file('gametab_template.glade')
    box = glade.get_object("gamescrolledwindow")
    channelstable = glade.get_object("channelstable")
    morebutton = glade.get_object("morebutton")

    newtab = TableTab(channelstable,
                morebutton,
                "https://api.twitch.tv/kraken/streams?game="+game, 
                "streams",
                publicate_table)
    tabs.append(newtab)

    lhbox = gtk.HBox()
    label = gtk.Label("Game: "+game)
    closeimage = gtk.Image()
    closeimage.set_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU)
    btn = gtk.Button()
    btn.set_image(closeimage)
    btn.set_relief(gtk.RELIEF_NONE)
    lhbox.pack_start(label, True, True, 0)
    lhbox.pack_start(btn, False, False, 0)
    lhbox.show_all()    
    pagenum = notebook.append_page(box, lhbox)
    btn.connect("clicked", close_tab, box)
    notebook.set_current_page(pagenum)

def close_tab(widget, page):
    n = notebook.page_num(page)
    notebook.remove_page(n)

def start_stream(widget, name):
    subprocess.Popen(["livestreamer", 'twitch.tv/'+name, quality, '--player', playercmd])

def open_url(widget, url):
    webbrowser.open(url, 0 ,True)

def download_logo(lurl):
    urlsplit = lurl.split("/")
    fname = urlsplit[len(urlsplit)-1]
    logo_path = "logos/"+fname
    if not os.path.isfile(logo_path):
        logo_img = requests.get(lurl)
        with open(logo_path, "wb") as code:
            code.write(logo_img.content)

def download_tmp(lurl):
    urlsplit = lurl.split("/")
    fname = urlsplit[len(urlsplit)-1]
    logo_path = "tmp/"+fname
    if not os.path.isfile(logo_path):
        logo_img = requests.get(lurl)
        with open(logo_path, "wb") as code:
            code.write(logo_img.content)

def query_twitch(apiurl, subelement):
    r = requests.get(apiurl)
    jobj = json.loads(r.text, 'utf-8')

    if (jobj.has_key('status') and jobj['status'] == 503):
        return query_twitch(apiurl, subelement)

    return jobj[subelement]

def check_live(data):
    namequery = ""
    is_online = {}
    for stream in data:
        channel = stream['channel']
        name = channel['name']
        namequery = namequery+name+","

    onlinejobj = query_twitch("https://api.twitch.tv/kraken/streams?limit=20&channel="+namequery, "streams")
    for stream in onlinejobj:
        name = stream['channel']['name']
        is_online[name] = "on"

    for stream in data:
        channel = stream['channel']
        name = channel['name']
        if (is_online.has_key(name)):
            channel['islive'] = True
        else:
            channel['islive'] = False

if __name__ == "__main__":
    try:
        loadsettings()
        app = TwitchBrowserGTK()
        gtk.main()
    except KeyboardInterrupt:
        pass