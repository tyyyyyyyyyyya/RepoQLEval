
import cpp

from FunctionCall fc, Variable v
where
  (
    fc.getTarget().hasName("strcpy") or
    fc.getTarget().hasName("strncpy") or
    fc.getTarget().hasName("gets") or
    fc.getTarget().hasName("scanf") or
    fc.getTarget().hasName("sprintf") or
    fc.getTarget().hasName("vsprintf") or
    fc.getTarget().hasName("memcpy") or
    fc.getTarget().hasName("memmove")
  ) and
  fc.getAnArgument().getType().getSize() < v.getType().getSize()
select fc.getFile().getAbsolutePath(), fc
