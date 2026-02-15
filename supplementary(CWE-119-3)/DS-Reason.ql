import cpp

predicate isDangerousFunction(Function f) {
  f.getName() in [
    "strcpy", "strcat", "sprintf", "vsprintf", "gets", "scanf", "sscanf", "fscanf",
    "vscanf", "vsscanf", "realpath", "getwd", "stpcpy", "strdup"
  ]
}

from FunctionCall call, string filename
where
  isDangerousFunction(call.getTarget()) and
  filename = call.getLocation().getFile().getBaseName()
select call, "Potential CWE-119 vulnerability: Dangerous function call in " + filename