class Tree:
  def __init__(self, type, **kw):
    self.type = type
    for k, v in kw.items():
      setattr(self, k, v)
  
  def __repr__(self):
    return self.dump()
  
  def dump(self, indent=0):
    def indented(s):
      assert isinstance(s, str)
      lines = s.split('\n')
      return "\n".join(["  " + line for line in lines])
    def dump_(v):
      if isinstance(v, Tree):
        return v.dump(indent + 1)
      elif isinstance(v, list):
        def listindented(s):
          assert isinstance(s, str)
          lines = s.split('\n')
          return "\n".join([("- " if i == 0 else "  ") + line for i, line in enumerate(lines)])
        return "list" + "\n" + "\n".join([listindented(dump_(x)) for x in v])
      else:
        return str(v)
    return self.type + "\n" + indented("\n".join([f"{k}: " + dump_(v) for k, v in self.__dict__.items() if k != 'type']))

  def dictdump(self):
    return {k: v.dictdump() if isinstance(v, Tree) else v for k, v in self.__dict__.items() if k != 'type'}

  def __getattribute__(self, key):
    if key in ('__dict__', 'dump', 'type', '__repr__', '__getattribute__', 'dictdump'):
      return super().__getattribute__(key)
    if key not in self.__dict__:
      print(f"Warning: key '{key}' not in {self}")
    return self.__dict__[key]
