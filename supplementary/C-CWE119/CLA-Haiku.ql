import cpp

class CWE190Vulnerability extends DivExpr {
  CWE190Vulnerability() {
    this.getLeftOperand() instanceof Literal and
    this.getRightOperand() instanceof Literal and
    this.getRightOperand().getValue() = "0"
  }

  string getFilePath() {
    result = this.getLocation().getFile().getAbsolutePath()
  }
}

from CWE190Vulnerability v
select v.getFilePath()
