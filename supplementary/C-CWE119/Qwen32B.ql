import cpp

from FunctionCall call
where
  call.getTarget().getName() = "strcpy" or
  call.getTarget().getName() = "strcat" or
  call.getTarget().getName() = "sprintf" or
  call.getTarget().getName() = "gets" or
  (
    call.getTarget().getName() = "memcpy" or
    call.getTarget().getName() = "memmove"
  ) and
  call.getArgument(1) instanceof StringLiteral
select call, "Potential CWE-119 vulnerability in function call to " + call.getTarget().getName() + " in file " + call.getFile().getAbsolutePath()