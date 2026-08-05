import python
import semmle.python.security.dataflow.SqlInjectionQuery
import DataFlow::PathGraph

from Configuration config, DataFlow::PathNode source, DataFlow::PathNode sink
where config.hasFlowPath(source, sink)
select sink.getNode().getLocation().getFile().getRelativePath(), source, sink,
"SQL injection vulnerability detected in file $@ due to user-controlled input.",
source.getNode(), "a user-provided value"
