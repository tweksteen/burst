#!/usr/bin/python
#
# abrupt.color
# tw@securusglobal.com
#

try:
  from IPython.ColorANSI import InputTermColors
  
  style_normal = InputTermColors.Normal
  style_great_success = InputTermColors.LightGreen
  style_success = InputTermColors.Green
  style_error = InputTermColors.Red 
  style_warning = InputTermColors.Yellow
  style_info = InputTermColors.LightBlue
    
  def success(s):
    return style_success + s + style_normal
  
  def error(s):
    return style_error + s + style_normal

  def warning(s):
    return style_warning + s + style_normal

  def great_success(s):
    return style_great_success + s + style_normal

  def info(s):
    return style_info + s + style_normal

except ImportError:
  success = error = warning = great_success = info = lambda x: x


