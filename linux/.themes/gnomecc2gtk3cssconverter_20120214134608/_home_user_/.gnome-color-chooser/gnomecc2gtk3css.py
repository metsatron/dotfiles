#!/usr/bin/python
#- gnomecc2gtk3css 20120212150025 - Paulo Silva - GPL license
#- usage: python gnomecc2gtk3css.py > colourscheme.css

import os, sys

# finp_st=sys.argv[1]

finp_st="./config.xml"
fout_st="./config.css"

chbcp_st=finp_st
debug=0

fbase_st="./basewebcolour.basecolorpalette"

#- ------------------
#- functions --------
def suffixreplacer(a_st,b_st):
  lct1=a_st.rfind(".");lct2=a_st.rfind("/")
  if lct1>-1 and lct1>lct2:a_st=a_st[:lct1]
  a_st=a_st+b_st
  return a_st
def locstrinfo(a_st,b_st,c_st):
  adra=0;adrb=0;d_st=""
  while adrb<=len(a_st) and adrb<len(b_st):
    #if debug==1:print adra,adrb
    if a_st[adra]==b_st[adrb]:
      adrb=adrb+1
    adra=adra+1
  while a_st[adra]!=c_st[0]:
    d_st=d_st+a_st[adra]
    adra=adra+1
  return d_st
def hexvl(a_st):
  a_st=a_st.lower();tmpr=0;hx_st="0123456789abcdef";hx_st=hx_st.lower()
  for i in range(0,len(a_st),1):tmpr=(tmpr*16)+hx_st.find(a_st[i])
  return tmpr
def fixhxc(va):
  tm_st="000000"+hex(va).lstrip("0x");tm_st="#"+tm_st[len(tm_st)-6:]
  return tm_st.upper()
def fixhex(va,sz):
  tml_st=""
  for i in range (0,sz,1):tml_st=tml_st+"0"
  tml_st=tml_st+hex(va).lstrip("0x");tml_st=tml_st[len(tml_st)-sz:]
  return tml_st.upper()
def shade(a_st,kw_st,shd):
  a_st="000000"+a_st;a_st=a_st[len(a_st)-6:]
  a_st=a_st.lower();tmpr=0;hx_st="0123456789abcdef";hx_st=hx_st.lower()
  rv=(hx_st.find(a_st[0])*16)+hx_st.find(a_st[1])
  gv=(hx_st.find(a_st[2])*16)+hx_st.find(a_st[3])
  bv=(hx_st.find(a_st[4])*16)+hx_st.find(a_st[5])
  if kw_st.lower()=="k":
    rv=int(rv*shd);gv=int(gv*shd);bv=int(bv*shd)
  else:
    rv=int(255-((255-rv)*shd));gv=int(255-((255-gv)*shd));bv=int(255-((255-bv)*shd))
  hc_st="000000"+hex(rv*65536+gv*256+bv).lstrip("0x")
  return hc_st[len(hc_st)-6:]

#- --------------------------------
#- converter code start ----------------------
#if varghlp==0 and (txttmpl==1 and basepal==1):
#if txttmpl==1 and basepal==1:
#if basepal==1:

ifdefgamma=1

if finp_st!="":
  #- --------------------
  #- reads #define values from Base and Custom -----------------------
  # fovl_stl=[""]*2 #- dim fovl_stl(2)
  # fovl_stl[0]=fbase_st;fovl_stl[1]=chbcp_st
  # for foid in range(0,2,1):
  #  inpfile=open(fovl_stl[foid],"r")
    inpfile=open(finp_st,"r")
    lcntr=0
    while True:
      text_st=inpfile.readline();lcntr=lcntr+1
      if len(text_st)==0:break
      text_st=" "+text_st.strip()+"      # # # id \"9999\" value \"9999\" "
      cm01_st=locstrinfo(text_st," "," ")
      cm02_st=locstrinfo(text_st," # "," ")
      cm03_st=locstrinfo(text_st," #  #"," ")

      # print text_st
      
      cmb01_st=locstrinfo(text_st,"id\"","\"")
      cmb02_st=locstrinfo(text_st,"value\"","\"")

      if cmb01_st.lower()=="0":print "@define-color bg_color "+cmb02_st.lower()+"; /* element id 0 - bg[NORMAL] */ " 
      if cmb01_st.lower()=="1":print "@define-color prelight_bg_color "+cmb02_st.lower()+"; /* element id 1 - bg[PRELIGHT] */ " 
      if cmb01_st.lower()=="2":print "@define-color selected_bg_color "+cmb02_st.lower()+"; /* element id 2 - bg[SELECTED] */ " 
      if cmb01_st.lower()=="3":print "@define-color active_bg_color "+cmb02_st.lower()+"; /* element id 3 - bg[ACTIVE] */ " 
      if cmb01_st.lower()=="4":print "@define-color intensitive_bg_color "+cmb02_st.lower()+"; /* element id 4 - bg[INTENSITIVE] */ " 

      if cmb01_st.lower()=="5":print "@define-color fg_color "+cmb02_st.lower()+"; /* element id 5 - fg[NORMAL] */ "
      if cmb01_st.lower()=="6":print "@define-color prelight_fg_color "+cmb02_st.lower()+"; /* element id 6 - fg[PRELIGHT] */ "
      if cmb01_st.lower()=="7":print "@define-color selected_fg_color "+cmb02_st.lower()+"; /* element id 7 - fg[SELECTED] */ "
      if cmb01_st.lower()=="8":print "@define-color active_fg_color "+cmb02_st.lower()+"; /* element id 8 - fg[ACTIVE] */ "
      if cmb01_st.lower()=="9":print "@define-color intensitive_fg_color "+cmb02_st.lower()+"; /* element id 9 - fg[INTENSITIVE] */ "
 
      if cmb01_st.lower()=="10":print "@define-color base_color "+cmb02_st.lower()+"; /* element id 10 - base[NORMAL] */ "
      if cmb01_st.lower()=="11":print "@define-color prelight_base_color "+cmb02_st.lower()+"; /* element id 11 - base[PRELIGHT] */ "
      if cmb01_st.lower()=="12":print "@define-color selected_base_color "+cmb02_st.lower()+"; /* element id 12 - base[SELECTED] */ "
      if cmb01_st.lower()=="13":print "@define-color active_base_color "+cmb02_st.lower()+"; /* element id 13 - base[ACTIVE] */ "
      if cmb01_st.lower()=="14":print "@define-color intensitive_base_color "+cmb02_st.lower()+"; /* element id 14 - base[INTENSITIVE] */ "
 
      if cmb01_st.lower()=="15":print "@define-color text_color "+cmb02_st.lower()+"; /* element id 15 - text[NORMAL] */ "
      if cmb01_st.lower()=="16":print "@define-color prelight_text_color "+cmb02_st.lower()+"; /* element id 16 - text[PRELIGHT] */ "
      if cmb01_st.lower()=="17":print "@define-color selected_text_color "+cmb02_st.lower()+"; /* element id 17 - text[SELECTED] */ "
      if cmb01_st.lower()=="18":print "@define-color active_text_color "+cmb02_st.lower()+"; /* element id 18 - text[ACTIVE] */ "
      if cmb01_st.lower()=="19":print "@define-color intensitive_text_color "+cmb02_st.lower()+"; /* element id 19 - text[INTENSITIVE] */ "
 
      if cmb01_st.lower()=="44":print "@define-color scrollbar_bg_color "+cmb02_st.lower()+"; /* scrollbar background - element id 44 */ "
      if cmb01_st.lower()=="45":print "@define-color scrollbar_prelight_bg_color "+cmb02_st.lower()+"; /* scrollbar background - element id 45 */ "
      if cmb01_st.lower()=="46":print "@define-color scrollbar_active_bg_color "+cmb02_st.lower()+"; /* scrollbar background - element id 46 */ "
 
      if cmb01_st.lower()=="83":print "@define-color button_bg_color "+cmb02_st.lower()+"; /* button background - element id 83 */ "
      if cmb01_st.lower()=="84":print "@define-color button_prelight_bg_color "+cmb02_st.lower()+"; /* button background - element id 84 */ "
      if cmb01_st.lower()=="85":print "@define-color button_selected_bg_color "+cmb02_st.lower()+"; /* selected background - element id 85 */ "
      if cmb01_st.lower()=="86":print "@define-color button_active_bg_color "+cmb02_st.lower()+"; /* button background - element id 86 */ "
      if cmb01_st.lower()=="87":print "@define-color button_insensitive_bg_color "+cmb02_st.lower()+"; /* button background - element id 87 */ "
 
      if cmb01_st.lower()=="88":print "@define-color button_fg_color "+cmb02_st.lower()+"; /* button foreground - element id  88 */ "
      if cmb01_st.lower()=="89":print "@define-color button_prelight_fg_color "+cmb02_st.lower()+"; /* button foreground - element id  89 */ "
      if cmb01_st.lower()=="90":print "@define-color button_selected_fg_color "+cmb02_st.lower()+"; /* selected foreground - element id  90 */ "
      if cmb01_st.lower()=="91":print "@define-color button_active_fg_color "+cmb02_st.lower()+"; /* button foreground - element id  91 */ "
      if cmb01_st.lower()=="92":print "@define-color button_intensitive_fg_color "+cmb02_st.lower()+"; /* button foreground - element id  92 */ "
 
      if cmb01_st.lower()=="51":print "@define-color tooltip_bg_color "+cmb02_st.lower()+"; /* tooltip background - element id 51 */ "
      if cmb01_st.lower()=="78":print "@define-color tooltip_fg_color "+cmb02_st.lower()+"; /* tooltip foreground - element id 78 */ "
 
      if cmb01_st.lower()=="48":print "@define-color progressbar_bg_color "+cmb02_st.lower()+"; /* progressbar background - element id 48 */ "
      #if cmb01_st.lower()=="48":print "@define-color progressbar_selected_bg_color "+cmb02_st.lower()+"; /* progressbar background - 48 */ "
 
      if cmb01_st.lower()=="26":print "@define-color panel_bg_color "+cmb02_st.lower()+"; /* window background - element id 26 */ "
      if cmb01_st.lower()=="27":print "@define-color panel_prelight_bg_color "+cmb02_st.lower()+"; /* window background - element id 27 */ "
      if cmb01_st.lower()=="28":print "@define-color panel_selected_bg_color "+cmb02_st.lower()+"; /* selected background - element id 28 */ "
      if cmb01_st.lower()=="29":print "@define-color panel_active_bg_color "+cmb02_st.lower()+"; /* window background - element id 29 */ "
      if cmb01_st.lower()=="30":print "@define-color panel_intensitive_bg_color "+cmb02_st.lower()+"; /* window background - element id 30 */ "

      if cmb01_st.lower()=="31":print "@define-color panel_fg_color "+cmb02_st.lower()+"; /* window foreground - element id 31 */"
      if cmb01_st.lower()=="32":print "@define-color panel_prelight_fg_color "+cmb02_st.lower()+"; /* window foreground - element id 32 */"
      if cmb01_st.lower()=="33":print "@define-color panel_selected_fg_color "+cmb02_st.lower()+"; /* selected foreground - element id 33 */"
      if cmb01_st.lower()=="34":print "@define-color panel_active_fg_color "+cmb02_st.lower()+"; /* window foreground - element id 34 */"
      if cmb01_st.lower()=="35":print "@define-color panel_intensitive_fg_color "+cmb02_st.lower()+"; /* window foreground - element id 35 */"

      if cmb01_st.lower()=="94":print "@define-color combobox_fg_color "+cmb02_st.lower()+"; /* combobox foreground - element id 94 */"
      if cmb01_st.lower()=="95":print "@define-color combobox_prelight_fg_color "+cmb02_st.lower()+"; /* combobox foreground - element id 95 */"
      if cmb01_st.lower()=="96":print "@define-color combobox_selected_fg_color "+cmb02_st.lower()+"; /* selected foreground - element id 96 */"
      if cmb01_st.lower()=="97":print "@define-color combobox_active_fg_color "+cmb02_st.lower()+"; /* combobox foreground - element id 97 */"
      if cmb01_st.lower()=="98":print "@define-color combobox_intensitive_fg_color "+cmb02_st.lower()+"; /* combobox foreground - element id 98 */"

      if cmb01_st.lower()=="81":print "@define-color link_color "+cmb02_st.lower()+"; /* link - element id- 81 */"
      if cmb01_st.lower()=="82":print "@define-color visited_link_color "+cmb02_st.lower()+"; /* visited link - element id 82 */"

    inpfile.close()

#- that's all !!! - element id- element id- element id- element id- element id- element id- element id- element id- element id- element id- element id- element id

