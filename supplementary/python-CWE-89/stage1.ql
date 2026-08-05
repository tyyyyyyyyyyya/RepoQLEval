import python
import semmle.python.dataflow.new.DataFlow
import semmle.python.dataflow.new.TaintTracking
import semmle.python.dataflow.new.RemoteFlowSources

/**

* A configuration for tracking user input to SQL query execution.
  */
  class SqlInjectionConfig extends TaintTracking::Configuration {
  SqlInjectionConfig() { this = "SqlInjectionConfig" }

override predicate isSource(DataFlow::Node source) {
source instanceof RemoteFlowSource
}

override predicate isSink(DataFlow::Node sink) {
exists(DataFlow::CallCfgNode call |
call.getFunction().(DataFlow::Node).toString() in ["execute", "executemany", "cursor"] and
sink in [call.getArg(*), call.getArgByName(*)]
)
}

override predicate isSanitizer(DataFlow::Node node) {
exists(DataFlow::CallCfgNode call |
call.getFunction().(DataFlow::Node).toString() in ["execute", "executemany"] and
exists(DataFlow::Node arg | arg in [call.getArg(*), call.getArgByName(*)] |
arg.toString().matches("%?") and
node = arg
)
)
}
}

from SqlInjectionConfig config, DataFlow::PathNode source, DataFlow::PathNode sink
where config.hasFlowPath(source, sink)
select sink.getNode(), source, sink,
"Potential SQL injection vulnerability: user input from $@ flows to SQL query execution.",
source.getNode(), "this source",
sink.getNode().getLocation().getFile().getRelativePath(), "file"