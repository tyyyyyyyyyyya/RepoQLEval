/**
 * @name CWE-119: Buffer Overflow
 * @description Accessing memory outside the bounds of a buffer can lead to severe security vulnerabilities.
 * @kind problem
 * @problem.severity high
 * @id cpp/cwe-119
 */

import cpp

class CWE119BufferOverflow extends FunctionCall {
  CWE119BufferOverflow() {
    this.getTarget().hasName("memcpy") or
    this.getTarget().hasName("memmove") or
    this.getTarget().hasName("strcpy") or
    this.getTarget().hasName("strncpy") or
    this.getTarget().hasName("sprintf") or
    this.getTarget().hasName("snprintf")
  }
}

from CWE119BufferOverflow vuln, File file
where file = vuln.getFile()
select vuln, "Potential CWE-119 buffer overflow in " + file.getBaseName() + " at line " + vuln.getLocation().getStartLine(), file