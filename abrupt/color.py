try:
  from IPython.ColorANSI import InputTermColors
  
  style_normal = InputTermColors.Normal
  style_great_success = InputTermColors.LightGreen
  style_success = InputTermColors.Green
  style_error = InputTermColors.Red 
  style_warning = InputTermColors.Yellow
  style_info = InputTermColors.LightBlue
  style_stealthy = InputTermColors.Black

    
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

  def stealthy(s):
    return style_stealthy + s + style_normal

  def color_status(status):
    if status.startswith("2"):
      return great_success(status)
    elif status.startswith("3"):
      return warning(status)
    elif status.startswith("4") or status.startswith("5"):
      return error(status)
    return stealthy(status)
    

except ImportError:
  success = error = warning = stealthy = great_success = info = color_status = lambda x: x


