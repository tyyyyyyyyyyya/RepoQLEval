/**
 * @name CWE-119: Improper Restriction of Operations within the Bounds of a Memory Buffer
 * @description Detects potential buffer overflow vulnerabilities where operations on a memory buffer do not properly restrict access within the buffer's bounds.
 * @kind problem
 * @problem.severity warning
 * @security-severity 8.1
 * @precision medium
 * @id cpp/cwe-119
 * @tags security
 *       external/cwe/cwe-119
 */

import cpp
import semmle.code.cpp.rangeanalysis.SimpleRangeAnalysis

// Helper predicate to get the size of an array if it can be determined
int getArraySize(Variable v) {
  exists(ArrayType at | at = v.getType().getUnspecifiedType() |
    result = at.getArraySize()
  )
}

from ArrayExpr arrayAccess, Expr index, Variable arrayVar
where
  arrayAccess.getArrayBase() = arrayVar.getAnAccess() and
  arrayAccess.getArrayOffset() = index and
  exists(int arraySize | arraySize = getArraySize(arrayVar) |
    upperBound(index) >= arraySize
  ) and
  // Exclude cases where the index is clearly guarded by a condition
  not exists(IfStmt ifStmt, RelationalOperation relOp |
    ifStmt.getCondition() = relOp and
    relOp.getAnOperand() = index and
    relOp.getAnOperand().isConstant() and
    arrayAccess.getEnclosingBlock() = ifStmt.getThen()
  )
select arrayAccess,
  "Potential buffer overflow in access to array $@ at index " + index.toString() +
  ". File: " + arrayAccess.getFile().getAbsolutePath(),
  arrayVar, arrayVar.toString()
 