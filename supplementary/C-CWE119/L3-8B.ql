import cpp

concept CWE119 {
  entity c = Call
  c.name == "gets"
}

query CWE119_vulnerable_files {
  allFiles() -> file
  | allCallsOn(file) -> call
  | CWE119(call)
  | select filePath = file.path
}