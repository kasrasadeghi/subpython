class LineReader():
  def __init__(self, content):
    self.lines = content.split('\n')
    self.index = 0

  def peek(self):
    if self.index >= len(self.lines):
      return None

    return self.lines[self.index]

  def pop(self):
    if self.index >= len(self.lines):
      return None

    line = self.lines[self.index]
    self.index += 1

    return line

  def has_next(self):
    return self.index < len(self.lines)
