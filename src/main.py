﻿# -*- coding: UTF-8 -*- 
import cv2
import numpy as np
# local module
from fps import FPS
from udp.myudp import MyUdp
from camshift.mycamshift import mycamshift
from camshift.analyze import *
import camshift.video as video
import time
from calibration import fish_calibration

from camshift.WebcamVideoStream import WebcamVideoStream

class App(object):
    def __init__(self, video_src):
        #树莓派ip
        self.mdp=MyUdp()
        #self.server_address='http://%s:8000/stream.mjpg' % MyUdp.get_piIP('raspberrypi')
        #self.server_address='http://192.168.43.110:8000/stream.mjpg'
        #self.server_address='rtmp://127.0.0.1/live/stream'
        #self.server_address='rtmp://127.0.0.1:1935/dji'
        #self.server_address='http://192.168.56.240:8000/stream.mjpg'
        
        #self.server_address='http://192.168.56.240:8000/?action=stream'
        #self.server_address='http://192.168.191.3:8000/stream.mjpg'

        #self.server_address='rtsp://:192.168.40.118/1'
        self.server_address=1
        #self.server_address='udp://@:8000 --demux=h264'
        self.cam = video.create_capture(self.server_address)
        #self.cam = WebcamVideoStream(self.server_address).start()
        ret, self.frame = self.cam.read()
        #self.fish_cali=fish_calibration(self.frame)
        self.drag_start = None
        self.list_camshift=[]
        #self.show_backproj = False
        self.newcamshift=None
        self.selection=None
        self.lock=False
        self.first_start=False
        self.lastime=time.time()
        self.sumtime=0

        #self.count=0
        self.light=self.get_light()

        self.swicht=False
        #self.list_camshift.append(self.get_car('red.jpg',0))
        #self.list_camshift.append(self.get_car('yellow.jpg',1))
        #H,S
        self.mask_avoid=cv2.cvtColor(cv2.imread('mask_avoid.bmp'),cv2.COLOR_BGR2GRAY)

        self.BACKGROUND_PARAM=App.calc_HS(cv2.cvtColor(self.frame,cv2.COLOR_BGR2HSV))
        
        self.miste=True

        self.fps = FPS().start()

        #wifi模块IP
        self.mdp.client_address=('192.168.56.61', 8899)  

        #新车
        #self.mdp.client_address=('192.168.56.207', 8899)  
        cv2.namedWindow('TUCanshift')
        cv2.setMouseCallback('TUCanshift', self.onmouse)

    def onmouse(self, event, x, y, flags, param):
        if self.lock:
            if event == cv2.EVENT_RBUTTONDOWN:
                self.pop_camshift()
                return
            if event == cv2.EVENT_LBUTTONDOWN:
                self.drag_start = (x, y)
                self.newcamshift=mycamshift()
            if self.drag_start:                  
                xmin = min(x, self.drag_start[0])
                ymin = min(y, self.drag_start[1])
                xmax = max(x, self.drag_start[0])
                ymax = max(y, self.drag_start[1])
                self.selection=(xmin, ymin, xmax, ymax)
            if event == cv2.EVENT_LBUTTONUP:
                self.fps.reset()
                self.drag_start = None
                if self.newcamshift is not None and self.newcamshift.getHist() is not None:
                    self.newcamshift.ID=len(self.list_camshift)
                    self.list_camshift.append(self.newcamshift)
                self.newcamshift=None
                self.selection=None

    def pop_camshift(self):
        if(len(self.list_camshift)<1):
            return True
        cv2.destroyWindow(str(len(self.list_camshift)-1))
        cv2.destroyWindow('%s%s' % ('cam',str(len(self.list_camshift)-1)))
        self.list_camshift.pop()
        return False
    
    @staticmethod
    def creat_camshift_from_img(hsv):
        camshift=mycamshift()
        mask=np.ones((hsv.shape[0],hsv.shape[1]),dtype=np.uint8)
        camshift.preProcess(hsv,mask,(0,0,hsv.shape[1],hsv.shape[0]),32)
        return camshift

    def get_light(self):
        temp=mycamshift()
        temp.prProcess_light(self.frame)
        temp.ID=99
        return temp
    
    def get_car(self,file,ID):
        img=cv2.imread(file,cv2.IMREAD_UNCHANGED)
        img=cv2.resize(img,(self.frame.shape[1],self.frame.shape[0]))       
        hsv=cv2.cvtColor(img,cv2.COLOR_BGR2HSV)
        temp=App.creat_camshift_from_img(hsv)
        cv2.imshow(str(ID),temp.getHist())
        temp.ID=ID

        return temp

    @staticmethod
    def calc_HS(hsv):
        H_hist = cv2.calcHist([hsv],[0], None,[180],[0,180])
        H = H_hist.argmax(axis=None, out=None)
        S_hist = cv2.calcHist([hsv],[1], None,[255],[0,255])
        S = S_hist.argmax(axis=None, out=None)
        return (H,S)
        
    def run(self):
        while True:  
            #if not (self.cam.renew and self.cam.grabbed): 
            #    if not self.cam.grabbed:
            #        self.mdp.send_message('lost')          
            #    continue
            
            ret, self.frame = self.cam.read()
            self.frame=cv2.resize(self.frame,(640,480))
            #self.frame=cv2.GaussianBlur(self.frame,(5,5),2)
            
            #self.frame=cv2.medianBlur(self.frame,5)
            
            #self.frame=self.fish_cali.cali(self.frame)

            imshow_vis=self.frame.copy()
                        
            hsv=cv2.cvtColor(self.frame, cv2.COLOR_BGR2HSV)

            #注掉使用背景参数的静态方法
            self.BACKGROUND_PARAM=App.calc_HS(hsv)

            mask=mycamshift.filte_background_color(hsv,self.BACKGROUND_PARAM,offset1=30.,offset2=90., iterations=3)
            if self.miste:
                cv2.imshow('fore_ground',mask)

            if self.newcamshift is not None:
                if self.newcamshift.preProcess(hsv,mask,self.selection,16):
                    cv2.imshow(str(ll),self.newcamshift.getHist())   

            self.lock=False
            ll=len(self.list_camshift) 
            if ll>0:
                light_gray=cv2.cvtColor(self.frame,cv2.COLOR_BGR2GRAY)
                #cv2.imshow('gray',light_gray)
                mean,temp = cv2.threshold(light_gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
                thresh=(255-mean)*0.8+mean
                if thresh>230:
                    thresh=230

                #_,light_gray=cv2.threshold(light_gray,thresh,255,cv2.THRESH_BINARY)
                
                _,light_gray_ths=cv2.threshold(light_gray,thresh,255,cv2.THRESH_BINARY)
                light_gray=cv2.bitwise_and(light_gray,light_gray,mask=cv2.bitwise_and(mask,light_gray_ths))
                light_gray=cv2.morphologyEx(light_gray,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3)),iterations=3, borderType=cv2.BORDER_REPLICATE)
                

                if self.miste:
                    cv2.imshow('light',light_gray)
                
                track_box=[self.light.go_once_gray(light_gray)]
                
                if track_box[0] is None:
                    self.sumtime=time.time()-self.lastime+self.sumtime
                else:
                    self.sumtime=0
                    self.first_start=True
                self.lastime=time.time()
                #print self.sumtime
                
                if self.sumtime>0.6 and self.first_start:
                    print 'lost light GUIDANCE'
                    track_box[0]=((self.frame.shape[1]/2,self.frame.shape[0]/2),)
                if self.sumtime>3600:
                    self.sumtime=36

                #mask_hsv=cv2.bitwise_and(hsv,hsv,mask=mask)
                #cv2.imshow('mask_hsv',mask_hsv)
                
                for x in self.list_camshift:
                    track_box.append(x.go_once(hsv,mask))             

                n=len(track_box)
                #if n>2:
                if n>2:
                    p3=track_box[0]
                    p1,p2=track_box[n-2:]            
                    try:
                        p1=p1[0]
                    except:
                        p1=None
                    try:
                        p2=p2[0]
                    except:
                        p2=None
                    try:
                        p3=p3[0]
                    except:
                        p3=None
                    if p1 and p2:
                        try:
                            #snap(img,p1,p2,障碍侦测范围，障碍侦测宽度，微调：避免将车头识别为障碍)
                            #theta,D,dst=snap(mask,p1,p2,7.0,0.8,2.2,2.2)
                            

                            #新车
                            theta,D,dst=snap(mask,p1,p2,8.0,0.9,2.2,2.2)
                            #theta,D,dst=snap_test(mask,self.mask_avoid,p1,p2,6.0,2.0,2.1,2.2)

                            dst=cv2.resize(dst,(400,200))
                            if self.miste:
                                cv2.imshow('snap',dst)
                            if theta is not None:
                                mes=(int(theta),int(D))
                                self.mdp.send_message('avoid',mes)
                                #print('Block ahead')
                                cv2.putText(imshow_vis, 'Block ahead:%s,%s' % mes, (10, 230),cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255,255), 1, cv2.LINE_AA)
                                #print(mes)

                            elif p3:
                                t,d=get_direction(p1,p2,p3)
                                mes=(int(t),int(d))
                                self.mdp.send_message('guidance',mes)
                                #print('guidance')
                                cv2.putText(imshow_vis, 'Guidance:%s,%s' % mes, (10, 230),cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255,255), 1, cv2.LINE_AA)
                                #print mes
                            else:
                                cv2.putText(imshow_vis, 'Taget LOST', (10, 230),cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255,255), 1, cv2.LINE_AA)
                                self.mdp.send_message('lost')
                        except:
                            cv2.putText(imshow_vis, '0/0 is error', (10, 230),cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255,255), 1, cv2.LINE_AA)
                            self.mdp.send_message('lost')
                    else:
                        cv2.putText(imshow_vis, 'Wait for START', (10, 230),cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255,255), 1, cv2.LINE_AA)
                        self.mdp.send_message('lost')

                elif n>1:
                    cv2.putText(imshow_vis, 'Wait for START', (10, 230),cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255,255), 1, cv2.LINE_AA)
                    self.mdp.send_message('lost')
                else:
                    cv2.putText(imshow_vis, 'Wait for START', (10, 230),cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255,255), 1, cv2.LINE_AA)
                    #self.mdp.send_message('lost')


                #prob=self.list_camshift[ll-1].prob
                #if self.show_backproj and prob is not None:
                #    self.frame=prob[...,np.newaxis]

                for x in track_box:
                    try:
                        cv2.ellipse(imshow_vis, x, (0, 0, 255), 2) 
                        pts = cv2.boxPoints(x)
                        pts = np.int0(pts)
                        cv2.polylines(imshow_vis, [pts], True, 255, 2)
                    except:
                        pass
                        

            else:
                cv2.putText(imshow_vis, 'Wait for START', (10, 230),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255,255), 1, cv2.LINE_AA)
                #self.mdp.send_message('lost')
            self.lock=True  
            
            if self.selection is not None:
                x0, y0, x1, y1 = self.selection
                vis_roi = self.frame[y0:y1, x0:x1]
                cv2.bitwise_not(vis_roi, vis_roi)
            
            fps = self.fps.approx_compute()
            # print("FPS: {:.3f}".format(fps))
            cv2.putText(imshow_vis, 'FPS {:.3f}'.format(fps), (10, 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 255),
                        1, cv2.LINE_AA) 

            if self.miste:
                cv2.imshow('TUCanshift',imshow_vis)

            if not self.first_start:
                print 'WAIT...'
            else:
                print 'GO'
            

            ch = cv2.waitKey(1)
            if ch == 27:
                break
            #if ch==ord('b'):
            #    self.show_backproj=not self.show_backproj
            if ch==ord('r'):
                self.BACKGROUND_PARAM=App.calc_HS(hsv)
                self.first_start=False
            if ch==ord('w'):
                self.mdp.send_message('guidance',(0,10))
            if ch==ord('s'):
                self.mdp.send_message('back_car',(0,0))
            if ch==ord('['):
                self.miste=not self.miste            
            if ch==ord('j'):
                self.first_start=False
                while True:
                    self.mdp.send_message('lost')
                    ob=cv2.waitKey(1)
                    if ob==ord('k'):
                        break


            #data, addr = self.mdp.recv_message()
            #data=MyUdp.getdata(data)
            #if data:
            #    print "received:", data, "from", addr

        cv2.destroyAllWindows()
        self.cam.release()
        self.mdp.close()


if __name__=='__main__':
    App(0).run()