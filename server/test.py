string = """def func(x):
  return x + 1"""

def runFunc():
    global_func = {}
    exec(string, globals(), global_func)
    x = global_func['func'](41)
    print(x)
    return x

runFunc()