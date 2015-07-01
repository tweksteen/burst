from burst.conf import conf

style_normal = "\033[0m"
style_great_success = "\033[36m"
style_success = "\033[32m"
style_error = "\033[31m"
style_warning = "\033[33m"
style_info = "\033[34m"
style_stealthy = "\033[37m"
style_bright_red = "\033[1;31m"

def __generic_style(c):
  def _x(s, rl=False):
    if conf.color_enabled:
      if rl:
        return '\001' + c + '\002' + s + '\001' + style_normal + '\002'
      else:
        return c + s + style_normal
    else:
      return s
  return _x

success = __generic_style(style_success)
error = __generic_style(style_error)
warning = __generic_style(style_warning)
great_success = __generic_style(style_great_success)
stealthy = __generic_style(style_stealthy)
info = __generic_style(style_info)
bright_red = __generic_style(style_bright_red)

def color_status(status, rl=False):
  if status.startswith("2"):
    return great_success(status, rl)
  elif status.startswith("3"):
    return warning(status, rl)
  elif status.startswith("4") or status.startswith("5"):
    return error(status, rl)
  return stealthy(status, rl)
