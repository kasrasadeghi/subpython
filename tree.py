class Tree:
  def __init__(self, **kw):
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
        return repr(v)
    return self.type + "\n" + indented("\n".join([f"{k}: " + dump_(v) for k, v in self.__dict__.items() if k != 'type']))

  def dictdump(self):
    return {k: v.dictdump() if isinstance(v, Tree) else v for k, v in self.__dict__.items() if k != 'type'}

  def __getitem__(self, key):
    return self.__dict__[key]
